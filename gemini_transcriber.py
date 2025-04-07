import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please add it to your .env file.")

genai.configure(api_key=GEMINI_API_KEY)

def transcribe_audio_chunk(audio_chunk, model):
    """Transcribe a single chunk of audio data."""
    prompt = '''Generate a transcript of the speech with precise word-by-word timing.
Return the result as a JSON array where each entry contains a single word with its timing information.
Each entry should have the following format:
{
    "index": sequential_number_starting_from_0,
    "text": "word",
    "start": start_time_in_seconds,
    "duration": duration_in_seconds,
    "person": "label of the speaking person"
}

IMPORTANT: Make sure the JSON is valid and properly formatted. Do not include any explanatory text before or after the JSON array.
Start your response with [ and end with ], and make sure all entries are properly separated with commas.'''

    # Generate content with the audio chunk
    try:
        response = model.generate_content(
            contents=[{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "audio/mp3", "data": audio_chunk}}]}]
        )

        # Get the transcript text
        transcript = response.text.strip()
        
        # Clean up the response - remove any markdown formatting
        if transcript.startswith("```json"):
            transcript = transcript[7:]
        if transcript.endswith("```"):
            transcript = transcript[:-3]
        transcript = transcript.strip()
        
        # Try to parse the JSON
        try:
            transcript_data = json.loads(transcript)
            return transcript_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            
            # Try a more aggressive approach to extract a valid JSON array
            import re
            
            # Find anything that looks like a JSON array
            json_pattern = r'\[\s*\{.*\}\s*\]'
            match = re.search(json_pattern, transcript, re.DOTALL)
            
            if match:
                json_str = match.group(0)
                try:
                    # Try to fix common JSON issues
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    # Remove control characters that might cause parsing issues
                    json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in '\t\r\n')
                    transcript_data = json.loads(json_str)
                    return transcript_data
                except json.JSONDecodeError as e2:
                    print(f"Still couldn't parse extracted JSON: {e2}")
                    # Try one more approach - parse line by line
                    try:
                        # Last resort: try to manually construct a valid JSON array
                        print("Attempting manual JSON reconstruction...")
                        lines = transcript.split('\n')
                        valid_entries = []
                        current_entry = ""
                        in_entry = False
                        
                        for line in lines:
                            line = line.strip()
                            if line.startswith('{'):
                                in_entry = True
                                current_entry = line
                            elif line.endswith('},') or line.endswith('}') and in_entry:
                                current_entry += line
                                try:
                                    # Fix the entry if it ends with a comma
                                    if current_entry.endswith(','):
                                        current_entry = current_entry[:-1]
                                    # Make sure it's a valid JSON object
                                    entry_json = json.loads(current_entry)
                                    valid_entries.append(entry_json)
                                except json.JSONDecodeError:
                                    pass  # Skip invalid entries
                                in_entry = False
                                current_entry = ""
                            elif in_entry:
                                current_entry += line
                        
                        if valid_entries:
                            print(f"Manually reconstructed {len(valid_entries)} valid entries")
                            return valid_entries
                    except Exception as e3:
                        print(f"Manual reconstruction failed: {e3}")
                    return []
            else:
                print("Could not find a JSON array pattern in the response")
                return []
    except Exception as e:
        print(f"Error during transcription: {e}")
        return []


def merge_transcripts(chunks, overlap_seconds=0):
    """Merge transcript chunks, handling overlaps appropriately."""
    if not chunks:
        return []
    
    # Start with an empty result
    merged = []
    
    # Add all words from all chunks to a single list
    for chunk in chunks:
        if not chunk:
            continue
        merged.extend(chunk)
    
    # Sort by start time
    merged.sort(key=lambda x: x['start'])
    
    # Remove duplicates (words that are too close in time and have similar text)
    if len(merged) > 1:
        filtered = [merged[0]]
        
        for i in range(1, len(merged)):
            current = merged[i]
            previous = filtered[-1]
            
            # Calculate time difference
            time_diff = abs(current['start'] - previous['start'])
            
            # If phrases are more than overlap_seconds apart, or have different text, keep both
            if time_diff > overlap_seconds:
                filtered.append(current)
            else:
                # Check for text similarity
                from difflib import SequenceMatcher
                similarity = SequenceMatcher(None, current['text'], previous['text']).ratio()
                
                # If texts are different enough, keep both
                if similarity < 0.7:  # Threshold for similarity
                    filtered.append(current)
                # Otherwise, keep the longer one
                elif len(current['text']) > len(previous['text']):
                    filtered[-1] = current
        
        # Reindex the filtered entries
        for idx, entry in enumerate(filtered):
            entry['index'] = idx
            
        return filtered
    
    return merged


def transcribe_audio_file(file_path, chunk_size_mb=10, overlap_mb=1):
    """Transcribe an audio file by processing it in chunks with overlap."""
    # Create a model instance
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Calculate chunk sizes in bytes
    chunk_size = chunk_size_mb * 1024 * 1024  # Convert MB to bytes
    overlap_size = overlap_mb * 1024 * 1024   # Convert MB to bytes
    
    # Get file size
    file_size = os.path.getsize(file_path)
    print(f"Audio file size: {file_size / (1024 * 1024):.2f} MB")
    
    # Read the audio file
    with open(file_path, 'rb') as f:
        audio_data = f.read()
    
    # If file is smaller than chunk size, process it all at once
    if file_size <= chunk_size:
        print("File is smaller than chunk size, processing entire file at once")
        transcript = transcribe_audio_chunk(audio_data, model)
        # Ensure each entry has an index if not already provided
        for idx, entry in enumerate(transcript):
            if 'index' not in entry:
                entry['index'] = idx
        return transcript
    
    # Process in chunks
    chunks = []
    chunk_transcripts = []
    overlap_seconds = 5  # Estimated overlap in seconds
    
    # Calculate number of chunks
    num_chunks = (file_size - overlap_size) // (chunk_size - overlap_size)
    if (file_size - overlap_size) % (chunk_size - overlap_size) > 0:
        num_chunks += 1
    
    print(f"Processing audio in {num_chunks} chunks of {chunk_size_mb}MB with {overlap_mb}MB overlap")
    
    # Estimate total duration for timestamp adjustments
    total_duration = estimated_total_duration(file_path)
    print(f"Estimated total duration: {total_duration:.2f} seconds")
    
    for i in range(num_chunks):
        # Calculate chunk start and end positions
        start_pos = i * (chunk_size - overlap_size)
        end_pos = min(start_pos + chunk_size, file_size)
        
        # Extract chunk
        chunk = audio_data[start_pos:end_pos]
        chunks.append(chunk)
        
        print(f"Processing chunk {i+1}/{num_chunks} ({len(chunk) / (1024 * 1024):.2f} MB)")
        
        # Transcribe chunk
        transcript = transcribe_audio_chunk(chunk, model)
        
        if transcript:
            # Ensure each entry has an index if not already provided
            for idx, entry in enumerate(transcript):
                if 'index' not in entry:
                    entry['index'] = idx
                    
            # If this is not the first chunk, adjust timing for the current chunk
            if i > 0:
                # Calculate time offset based on the chunk's position relative to file size
                # and the estimated total duration
                time_offset = (start_pos / file_size) * total_duration
                print(f"Applying time offset of {time_offset:.2f} seconds to chunk {i+1}")
                
                # Adjust all timestamps in this chunk
                for phrase in transcript:
                    phrase['start'] += time_offset
                    # Ensure we have all required fields
                    if 'duration' not in phrase:
                        phrase['duration'] = 1.0  # Default duration if missing
                    if 'person' not in phrase:
                        phrase['person'] = "unknown"  # Default speaker if missing
            
            chunk_transcripts.append(transcript)
            print(f"Chunk {i+1} transcription complete: {len(transcript)} words")
        else:
            print(f"Chunk {i+1} transcription failed or returned empty result")
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)
    
    # Merge all chunk transcripts
    merged_transcript = merge_transcripts(chunk_transcripts, overlap_seconds)
    
    # Sort the transcript by start time and reindex
    merged_transcript.sort(key=lambda x: x['start'])
    for idx, entry in enumerate(merged_transcript):
        entry['index'] = idx
    
    return merged_transcript

def estimated_total_duration(file_path):
    """Estimate the total duration of an audio file in seconds.
    This is a very rough estimate based on file size and assumes MP3 format.
    For more accurate results, consider using a library like pydub or ffmpeg.
    """
    # Rough estimate: ~1MB per minute for medium quality MP3
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    estimated_minutes = file_size_mb
    return estimated_minutes * 60  # Convert to seconds

# Main execution
if __name__ == "__main__":
    # File path for the audio
    audio_file_path = 'downloads/4zjvQd8dslY.mp3'
    
    # Transcribe the audio file
    transcript_data = transcribe_audio_file(audio_file_path)
    
    # Create the output file paths
    file_name = os.path.basename(audio_file_path)
    file_base = os.path.splitext(file_name)[0]
    output_file_path = f"downloads/{file_base}_transcript.json"
    
    # Save the transcript as a JSON array
    with open(output_file_path, 'w') as f:
        json.dump(transcript_data, f, indent=2)
    
    print(f"Transcript saved to {output_file_path}")
    print(f"Found {len(transcript_data)} words in the transcript")
    
    # Also save as plain text for easier reading
    text_output_path = f"downloads/{file_base}_transcript.txt"
    with open(text_output_path, 'w') as f:
        for phrase in transcript_data:
            f.write(f"{phrase['index']}: {phrase['start']:.2f} - {phrase['start'] + phrase['duration']:.2f}: {phrase['text']}\n")
    
    print(f"Plain text transcript saved to {text_output_path}")
    
    # Print a sample of the transcript
    print("First 5 phrases:")
    for i, phrase in enumerate(transcript_data[:5]):
        print(f"{phrase['index']}: {phrase['text']} ({phrase['start']:.2f}s, {phrase['duration']:.2f}s)")
