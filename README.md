# Fake Conversations Generator

A cybersecurity demonstration tool that shows how audio can be manipulated to create misleading content by selectively extracting and recombining segments from original recordings.

Created on [Sundai](https://www.sundai.club/projects/bff7fb12-04b4-4350-b0c1-86b0e7db07d6), April 6, 2025.

## ⚠️ Educational Purpose Only

This tool is designed **strictly for educational and cybersecurity awareness purposes**. It demonstrates how easily media can be manipulated to create false narratives, highlighting the importance of media literacy and verification in the digital age.

## Overview

The Fake Conversations Generator automates the process of:
1. Downloading audio from YouTube videos
2. Transcribing the audio with word-level timing information
3. Analyzing the transcript to identify segments that could be recombined to create misleading content
4. Extracting and combining those segments to create a fake audio clip

## Features

- **YouTube Integration**: Download audio and transcripts directly from YouTube videos
- **High-Quality Transcription**: Uses ElevenLabs Speech-to-Text API for accurate word-level transcription with timing
- **AI-Powered Analysis**: Leverages Google's Gemini AI to identify segments that could be repurposed
- **Audio Manipulation**: Extracts and combines audio segments using FFmpeg

## Requirements

- Python 3.8+
- FFmpeg
- API keys:
  - ElevenLabs API key
  - Google Gemini API key

## Installation

1. Clone this repository
2. Install required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Install FFmpeg (if not already installed):
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

4. Create a `.env` file in the project root with your API keys:
   ```
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

## Usage

Run the main script with a YouTube video ID:

```bash
./do.sh <youtube_video_id>
```

For example:
```bash
./do.sh dQw4w9WgXcQ
```

### Step-by-Step Process

1. **Download**: The script downloads the audio from the specified YouTube video
2. **Transcribe**: The audio is transcribed using ElevenLabs API with word-level timing
3. **Analyze**: Gemini AI analyzes the transcript to identify segments that could be recombined
4. **Create**: The identified segments are extracted and combined to create a fake audio clip

### Individual Components

You can also run each component separately:

#### YouTube Downloader
```bash
python youtube_downloader.py "https://www.youtube.com/watch?v=<video_id>"
```

#### ElevenLabs Transcriber
```bash
python elevenlabs_transcriber.py "downloads/<video_id>.mp3"
```

#### Gemini Analyzer
```bash
python gemini_analyzer.py "downloads/<video_id>_elevenlabs_transcript.json"
```

#### Fake Audio Creator
```bash
python create_fake_audio.py "downloads/<video_id>_elevenlabs_transcript_compromising_with_timing.json" "downloads/<video_id>.mp3"
```

## Output Files

The process generates several files in the `downloads` directory:
- `<video_id>.mp3`: Original audio from YouTube
- `<video_id>_transcript.json` & `<video_id>_transcript.txt`: YouTube's transcript (if available)
- `<video_id>_elevenlabs_transcript.json` & `<video_id>_elevenlabs_transcript.txt`: ElevenLabs transcript with word-level timing
- `<video_id>_elevenlabs_transcript_compromising.json`: Segments identified by Gemini as potentially misleading
- `<video_id>_elevenlabs_transcript_compromising_with_timing.json`: Same as above but with timing information
- `<video_id>_elevenlabs_transcript_compromising_fake.mp3`: The generated fake audio clip

## Ethical Considerations

This tool demonstrates how easily audio can be manipulated to create misleading content. It is intended to:
- Raise awareness about the ease of creating fake content
- Encourage critical thinking when consuming media
- Promote the development of detection technologies

**Do not use this tool to create misleading content for malicious purposes.**

## License

This project is provided for educational purposes only.
