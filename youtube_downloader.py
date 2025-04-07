#!/usr/bin/env python3
"""
YouTube Audio and Transcript Downloader
This script downloads audio and transcript from YouTube videos using yt-dlp.
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, Optional
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


def extract_video_id(url: str) -> str:
    """Extract the video ID from a YouTube URL."""
    if "youtu.be" in url:
        # Handle youtu.be URLs
        return url.split("/")[-1].split("?")[0]
    elif "youtube.com" in url:
        # Handle youtube.com URLs
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
            return video_id
    
    # If we can't extract the ID, return the original URL
    # yt-dlp will handle it
    return url


def download_audio(url: str, output_dir: str = "downloads", force: bool = False) -> Optional[str]:
    """
    Download audio from a YouTube video.
    
    Args:
        url: YouTube URL
        output_dir: Directory to save the downloaded audio
        force: Force download even if file already exists
    
    Returns:
        Path to the downloaded audio file or None if download failed
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract video ID for naming the output file
    video_id = extract_video_id(url)
    
    # Check if file already exists
    output_file = os.path.join(output_dir, f"{video_id}.mp3")
    if os.path.exists(output_file) and not force:
        print(f"Audio file already exists: {output_file}")
        return output_file
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, f'{video_id}.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
    }
    
    try:
        # Download the audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get the downloaded file path
            if info:
                # The file extension will be mp3 after post-processing
                return os.path.join(output_dir, f"{video_id}.mp3")
            
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None
    
    return None


def download_transcript(url: str, output_dir: str = "downloads", force: bool = False) -> Optional[str]:
    """
    Download transcript from a YouTube video.
    
    Args:
        url: YouTube URL
        output_dir: Directory to save the downloaded transcript
        force: Force download even if files already exist
    
    Returns:
        Path to the saved transcript file or None if download failed
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract video ID
    video_id = extract_video_id(url)
    
    # Check if transcript files already exist
    json_file = os.path.join(output_dir, f"{video_id}_transcript.json")
    text_file = os.path.join(output_dir, f"{video_id}_transcript.txt")
    
    if os.path.exists(json_file) and os.path.exists(text_file) and not force:
        print(f"Transcript files already exist: {json_file} and {text_file}")
        return json_file
    
    try:
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Fix durations to ensure each segment doesn't overlap with the next one
        for i in range(len(transcript) - 1):
            current_end = transcript[i]['start'] + transcript[i]['duration']
            next_start = transcript[i + 1]['start']
            
            # If current segment ends after the next one starts, adjust the duration
            if current_end > next_start:
                # Set duration so that it ends exactly at the start of the next segment
                transcript[i]['duration'] = max(0.1, next_start - transcript[i]['start'])

        # Save transcript as JSON
        transcript_file = os.path.join(output_dir, f"{video_id}_transcript.json")
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=4)
        
        # Also save as plain text for easy reading
        text_file = os.path.join(output_dir, f"{video_id}_transcript.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            for entry in transcript:
                f.write(f"[{entry['start']:.2f}s - {entry['start'] + entry['duration']:.2f}s] {entry['text']}\n")
        
        return transcript_file
        
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"No transcript available: {e}")
        return None
    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return None


def main():
    """Main function to parse arguments and download content."""
    parser = argparse.ArgumentParser(description="Download YouTube audio and transcript")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-o", "--output-dir", default="downloads", 
                        help="Output directory for downloaded files (default: downloads)")
    parser.add_argument("--audio-only", action="store_true", 
                        help="Download only audio")
    parser.add_argument("--transcript-only", action="store_true", 
                        help="Download only transcript")
    parser.add_argument("--force", action="store_true",
                        help="Force download even if files already exist")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Download based on options
    if args.transcript_only:
        print(f"Downloading transcript for: {args.url}")
        transcript_file = download_transcript(args.url, args.output_dir, args.force)
        if transcript_file:
            print(f"Transcript saved to: {transcript_file}")
    elif args.audio_only:
        print(f"Downloading audio for: {args.url}")
        audio_file = download_audio(args.url, args.output_dir, args.force)
        if audio_file:
            print(f"Audio saved to: {audio_file}")
    else:
        # Download both by default
        print(f"Downloading audio and transcript for: {args.url}")
        
        audio_file = download_audio(args.url, args.output_dir, args.force)
        if audio_file:
            print(f"Audio saved to: {audio_file}")
        
        transcript_file = download_transcript(args.url, args.output_dir, args.force)
        if transcript_file:
            print(f"Transcript saved to: {transcript_file}")
    

if __name__ == "__main__":
    main()
