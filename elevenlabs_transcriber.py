#!/usr/bin/env python3
"""
ElevenLabs Transcriber
This script transcribes audio files using the ElevenLabs Speech-to-Text API.
"""

import os
import json
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()

# Configure the ElevenLabs API
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in environment variables. Please add it to your .env file.")

# API endpoint for ElevenLabs Speech-to-Text
ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

def transcribe_audio_file(file_path: str, model_id: str = "scribe_v1") -> List[Dict[str, Any]]:
    """
    Transcribe an audio file using ElevenLabs Speech-to-Text API.
    
    Args:
        file_path: Path to the audio file
        model_id: ElevenLabs model ID to use for transcription
    
    Returns:
        List of word-level transcription entries with timing information
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    
    print(f"Transcribing audio file: {file_path}")
    
    # Prepare headers with API key
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    # Prepare the file for upload
    with open(file_path, 'rb') as audio_file:
        files = {
            'file': (os.path.basename(file_path), audio_file, 'audio/mpeg')
        }
        
        # Prepare form data
        data = {
            'model_id': model_id
        }
        
        # Make the API request
        try:
            print("Sending request to ElevenLabs API...")
            response = requests.post(
                ELEVENLABS_STT_URL,
                headers=headers,
                files=files,
                data=data
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Process the response into our expected format
            return process_elevenlabs_response(result)
            
        except requests.exceptions.RequestException as e:
            print(f"Error during API request: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status code: {e.response.status_code}")
                print(f"Response content: {e.response.text}")
            return []
        except Exception as e:
            print(f"Error during transcription: {e}")
            return []

def process_elevenlabs_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process the ElevenLabs API response into our expected word-level transcript format.
    
    Args:
        response: The JSON response from the ElevenLabs API
    
    Returns:
        List of word-level transcription entries with timing information
    """
    # Initialize the result list
    result = []

    # print(response)
    
    try:
        # Check if we have the expected fields in the response
        if 'words' in response:
            index = 0
            # Process each word in the response
            for word_data in response['words']:
                # Create an entry for each word with the required fields
                if word_data.get('type') != 'word':
                    continue
                duration = word_data.get('end', 0) - word_data.get('start', 0)
                duration = round(duration, 3)
                index += 1
                entry = {
                    'index': index,
                    'text': word_data.get('text', ''),
                    'start': word_data.get('start', 0),
                    'duration': duration,
                    # 'person': word_data.get('speaker_id', 'unknown')
                }
                result.append(entry)
        elif 'text' in response:
            # If we only have full text without word-level timing, create a single entry
            print("Warning: No word-level timing information available in the response.")
            entry = {
                'index': 0,
                'text': response['text'],
                'start': 0,
                'duration': 0,
                # 'person': 'unknown'
            }
            result.append(entry)
        else:
            print("Error: Unexpected response format from ElevenLabs API")
            print(f"Response: {json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"Error processing ElevenLabs response: {e}")
    
    return result

def estimated_total_duration(file_path: str) -> float:
    """
    Estimate the total duration of an audio file in seconds.
    This is a very rough estimate based on file size and assumes MP3 format.
    For more accurate results, consider using a library like pydub or ffmpeg.
    
    Args:
        file_path: Path to the audio file
    
    Returns:
        Estimated duration in seconds
    """
    # Get file size in bytes
    file_size = os.path.getsize(file_path)
    
    # Rough estimate: Assuming 128 kbps MP3 (16 KB/s)
    # Duration = file_size / (bitrate / 8)
    estimated_duration = file_size / (128 * 1024 / 8)
    
    return estimated_duration

def save_transcript(transcript: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save the transcript to a JSON file.
    
    Args:
        transcript: The transcript data
        output_path: Path to save the transcript
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    
    print(f"Transcript saved to: {output_path}")
    
    # Also save as plain text for easy reading
    text_file = output_path.replace('.json', '.txt')
    with open(text_file, 'w', encoding='utf-8') as f:
        for entry in transcript:
            f.write(f"[{entry['start']:.2f}s - {entry['start'] + entry['duration']:.2f}s] {entry['text']}\n")
    
    print(f"Plain text transcript saved to: {text_file}")

# Main execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Transcribe audio files using ElevenLabs API")
    parser.add_argument("file_path", help="Path to the audio file to transcribe")
    parser.add_argument("--model", default="scribe_v1", 
                        help="ElevenLabs model ID to use (default: scribe_v1)")
    parser.add_argument("--output", help="Output file path (default: input_file_transcript.json)")
    parser.add_argument("--force", action="store_true", 
                        help="Force transcription even if output file already exists")
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    if not args.output:
        base_name = os.path.splitext(args.file_path)[0]
        args.output = f"{base_name}_elevenlabs_transcript.json"
    
    # Check if transcript file already exists
    if os.path.exists(args.output) and not args.force:
        print(f"Transcript file already exists: {args.output}")
        print("Loading existing transcript instead of transcribing again.")
        
        # Load the existing transcript
        with open(args.output, 'r', encoding='utf-8') as f:
            transcript = json.load(f)
        
        print(f"Loaded existing transcript with {len(transcript)} entries")
    else:
        # Transcribe the audio file
        transcript = transcribe_audio_file(args.file_path, args.model)
        
        if transcript:
            # Save the transcript
            save_transcript(transcript, args.output)
            print(f"Transcription completed with {len(transcript)} entries")
        else:
            print("Transcription failed or returned no results")
