#!/bin/bash
# Fake Conversations Generator Script
# This script processes a YouTube video to create a fake audio clip that
# misrepresents what was said in the original video.

# Check if a YouTube video ID was provided
if [ $# -eq 0 ]; then
    echo "Error: No YouTube video ID provided"
    echo "Usage: $0 <youtube_video_id>"
    exit 1
fi

# Get the YouTube video ID from the command line argument
VIDEO_ID="$1"

# Create downloads directory if it doesn't exist
mkdir -p downloads

# Construct YouTube URL from the video ID
YOUTUBE_URL="https://www.youtube.com/watch?v=${VIDEO_ID}"

echo "Step 1: Downloading YouTube video and transcript..."
python youtube_downloader.py "$YOUTUBE_URL"

echo "Step 2: Transcribing audio with ElevenLabs..."
python elevenlabs_transcriber.py "downloads/${VIDEO_ID}.mp3"

echo "Step 3: Analyzing transcript to find potentially compromising segments..."
python gemini_analyzer.py "downloads/${VIDEO_ID}_elevenlabs_transcript.json"

echo "Step 4: Creating fake audio by combining segments..."
python create_fake_audio.py "downloads/${VIDEO_ID}_elevenlabs_transcript_compromising_with_timing.json" "downloads/${VIDEO_ID}.mp3"

echo "Process complete! The fake audio has been created."
echo "Original audio: downloads/${VIDEO_ID}.mp3"
echo "ElevenLabs transcript: downloads/${VIDEO_ID}_elevenlabs_transcript.json"
echo "Fake audio: downloads/${VIDEO_ID}_elevenlabs_transcript_compromising_fake.mp3"
