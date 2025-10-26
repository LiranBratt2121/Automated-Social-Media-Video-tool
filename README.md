## Automated Social Media Video tool
An automated video processing pipeline that transforms standard Amazon product videos urls into multiple, engaging, short-form social media clips, perfect for platforms like TikTok, YouTube Shorts, and Instagram Reels.
With a single click, it fetches a video, uses AI to analyze and script new content, generates dynamic voiceovers, and produces professionally subtitled videos ready for publishing.
(Suggestion: Replace this link with a screenshot of your actual GUI in action)
------
## ✨ Core Features
Amazon Video Fetcher: Directly downloads product videos from an Amazon URL.
AI-Powered Content Creation:
Intelligently analyzes the video to identify the best segments for short-form content.
Writes catchy titles, engaging descriptions, and complete voiceover scripts from scratch.
Generates prompts for the desired vocal style
Automated TTS Voiceover: Synthesizes high-quality, natural-sounding audio for the AI-generated scripts.
Dynamic, Phrase-Based Subtitles:
Generates perfectly timed, word-by-word highlighting that syncs with the voiceover.
Displays only the current spoken phrase to keep the screen clean and readable.
Intelligently persists text during natural pauses to prevent flickering.
End-to-End Automated Editing: Handles all video cutting, audio synchronization, subtitle burning, and final video assembly without any manual intervention.
Simple GUI: An easy-to-use interface to run the entire process, with real-time progress and log feedback.
------
## 🚀 How It Works
The application follows a sophisticated, fully automated pipeline:
Fetch: You provide an Amazon product video URL. The tool finds and downloads video stream.
Analyze: The downloaded video is sent to a multimodal AI which "watches" the video and generates three distinct micro-clip ideas, complete with timings, titles, descriptions, and voiceover scripts.

![Amazon Product video url](https://storage.googleapis.com/randommedia/amazon_product_url.png)
![Program running](https://storage.googleapis.com/randommedia/gui_app.png)
![Example result](https://storage.googleapis.com/randommedia/result_image.png)

Process Clips: For each AI-generated idea:
a. The original video is precisely cut to the specified timeframe.
b. An AI Text-to-Speech engine generates the voiceover audio.
c. The audio is automatically sped up or slowed down to perfectly match the video's duration.
d. Pydub analyzes the final audio to detect silent gaps, creating a perfect timing map.
e. The audio is merged with the video clip.
f. Dynamic subtitles are burned onto the video using the precise timing map.
Assemble & Save: All the processed micro-clips are combined into a single, final video.
Deliver: The final video and a text file containing the AI's titles and descriptions are saved, and the application automatically opens your file explorer to the output location.
------
## 🛠️ Getting Started
Follow these steps to get the project running on your local machine.

## Prerequisites
* Python 3.8+
* FFmpeg: This is essential for all video and audio processing.
[Download](https://www.ffmpeg.org/) FFmpeg here.
>> You must add the FFmpeg bin directory to your system's PATH environment variable so it can be called from the command line.

## Installation
Create and activate a virtual environment:

```Bash
# For Windows
python -m venv .venv
.\.venv\Scripts\activate

# For macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

Download project's requirements.txt file in your project root:
```bash
pip install -r requirements.txt
```
Set up your API Key:

Create a file named .env in the root of the project.
Get your API key from Google AI Studio.
Add the following line to your .env file:
```bash
GEMINI_API_KEY="YOUR_API_KEY_HERE"
```

Usage
Make sure your virtual environment is activated.
Run the GUI application from your terminal:
```bash
python gui_app.py
```
Paste an Amazon product video URL into the input box.

Click the "Generate Video" button.
Watch the progress bar and logs for real-time updates.
When the process is complete, your file explorer will open to show you the generated .mp4 video and .txt description file.

## 💻 Technology Stack
* Backend: Python
* AI / LLM: Google Gemini API
* Video/Audio Processing: FFmpeg, ffmpeg-python
* Audio Analysis: Pydub
* GUI: Tkinter