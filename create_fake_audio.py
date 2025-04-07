#!/usr/bin/env python3
"""
Fake Audio Creator
This script takes a JSON file with selected segments and the original audio file,
then uses FFmpeg to extract those segments and combine them into a new audio file.
"""

import os
import json
import argparse
import subprocess
import tempfile
from typing import List, Dict, Any

def load_segments(json_file_path: str) -> List[Dict[str, Any]]:
    """
    Load segments from a JSON file.
    
    Args:
        json_file_path: Path to the JSON segments file
        
    Returns:
        List of segments
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            segments_data = json.load(f)
        return segments_data
    except Exception as e:
        print(f"Error loading segments: {e}")
        return []

def merge_close_segments(segments: List[Dict[str, Any]], threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Merge consecutive segments that are very close together into a single segment.
    
    Args:
        segments: List of segments to process
        threshold: Maximum time gap (in seconds) between segments to be merged
        
    Returns:
        List of merged segments
    """
    if not segments or len(segments) < 2:
        return segments
    
    merged_segments = []
    current_segment = segments[0].copy()
    
    for next_segment in segments[1:]:
        # Calculate the gap between the end of current segment and start of next segment
        current_end = current_segment["start"] + current_segment["duration"]
        gap = next_segment["start"] - current_end
        
        if 0 <= gap <= threshold:
            # Merge segments
            new_duration = (next_segment["start"] + next_segment["duration"]) - current_segment["start"]
            current_segment["duration"] = new_duration
            current_segment["text"] = f"{current_segment['text']} {next_segment['text']}"
            # If there are other properties like "person", you might want to handle them here
        else:
            # Add the current segment to results and start a new one
            merged_segments.append(current_segment)
            current_segment = next_segment.copy()
    
    # Add the last segment
    merged_segments.append(current_segment)
    
    print(f"Merged {len(segments)} segments into {len(merged_segments)} segments")
    return merged_segments

def create_fake_audio(audio_file: str, segments: List[Dict[str, Any]], output_file: str, merge_threshold: float = 0.5) -> bool:
    """
    Create a fake audio file by extracting and combining segments from the original audio.
    
    Args:
        audio_file: Path to the original audio file
        segments: List of segments to extract and combine
        output_file: Path to save the resulting audio file
        merge_threshold: Maximum time gap (in seconds) between segments to be merged
        
    Returns:
        True if successful, False otherwise
    """
    if not segments:
        print("No segments provided.")
        return False
    
    # Merge segments that are close together
    # print(segments)
    merged_segments = merge_close_segments(segments, merge_threshold)    
    # print(merged_segments)

    # Create a temporary directory to store segment files
    with tempfile.TemporaryDirectory() as temp_dir:
        segment_files = []
        
        # Extract each segment to a separate file
        for i, segment in enumerate(merged_segments):
            start_time = segment["start"]
            duration = round(segment["duration"], 3)
            segment_file = os.path.join(temp_dir, f"segment_{i:03d}.mp3")
            
            # Use FFmpeg to extract the segment
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files without asking
                "-i", audio_file,  # Input file
                "-ss", str(start_time),  # Start time
                "-t", str(duration),  # Duration
                "-c:a", "copy",  # Copy audio codec (no re-encoding)
                segment_file  # Output file
            ]
            
            try:
                print(f"Extracting segment {i+1}/{len(merged_segments)}: {segment['text']} [{start_time} : {duration}]")
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                segment_files.append(segment_file)
            except subprocess.CalledProcessError as e:
                print(f"Error extracting segment {i+1}: {e}")
                print(f"FFmpeg stderr: {e.stderr.decode('utf-8')}")
                return False
        
        # Create a file list for FFmpeg to concatenate
        concat_file = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_file, "w") as f:
            for segment_file in segment_files:
                f.write(f"file '{segment_file}'\n")
        
        # Concatenate all segments
        concat_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files without asking
            "-f", "concat",  # Use concat demuxer
            "-safe", "0",  # Don't require safe filenames
            "-i", concat_file,  # Input file list
            "-c", "copy",  # Copy codecs (no re-encoding)
            output_file  # Output file
        ]
        
        try:
            print(f"Combining segments into {output_file}...")
            subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Fake audio created successfully: {output_file}")
            
            # Print the fake narrative
            print("\nFake narrative:")
            narrative = " ".join([segment["text"] for segment in merged_segments])
            print(f'"{narrative}"')
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error combining segments: {e}")
            print(f"FFmpeg stderr: {e.stderr.decode('utf-8')}")
            return False

def main():
    """Main function to parse arguments and create fake audio."""
    parser = argparse.ArgumentParser(description="Create fake audio by combining segments")
    parser.add_argument("json_file", help="Path to the JSON file with segments")
    parser.add_argument("audio_file", help="Path to the original audio file")
    parser.add_argument("-o", "--output", 
                        help="Output audio file (default: <json_file_base>_fake.mp3)")
    parser.add_argument("-t", "--threshold", type=float, default=0.5,
                        help="Maximum time gap (in seconds) between segments to be merged (default: 0.5)")
    
    args = parser.parse_args()
    
    # Set default output file if not specified
    if not args.output:
        base_name = os.path.splitext(args.json_file)[0]
        args.output = f"{base_name}_fake.mp3"
    
    # Load segments
    segments = load_segments(args.json_file)
    if not segments:
        print("No segments found in the JSON file. Exiting.")
        return
    
    # Create fake audio
    create_fake_audio(args.audio_file, segments, args.output, args.threshold)

if __name__ == "__main__":
    main()
