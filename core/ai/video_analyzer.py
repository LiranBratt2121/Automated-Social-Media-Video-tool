import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from .ai_types import MicroClip, TTSScriptLine, List
from .shared import init_client

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
VIDEO_PATH = r"C:/Users\bratt\Documents/code/video-tool/core/video/output_crop.mp4"
PROMPT_PATH = "core/ai/prompt.txt"
MODEL_NAME = "gemini-2.5-flash"


client = init_client()


def get_ai_prompt() -> str:
    try:
        with open(PROMPT_PATH, "r") as f:
            return f.read().strip()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Prompt file not found at '{PROMPT_PATH}'") from e
    except Exception as e:
        raise RuntimeError(f"Error reading prompt file: {e}") from e

def _upload_video(file_path: str) -> "types.File":
    def wait_for_upload(gemini_client: genai.Client, file: "types.File"):
        from time import sleep
        print(f"Waiting for file {file.name} to be uploaded...")
        while True:
            file_status = gemini_client.files.get(name=file.name or "").state
            if file_status == "ACTIVE":
                break
            print(f"File {file.name} is still {file_status}. Waiting...")
            sleep(5)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Video file not found at '{file_path}'")
    try:
        print(f"Uploading video file: {file_path}...")
        uploaded_file = client.files.upload(file=file_path)
        print(f"File uploaded successfully: {uploaded_file.name}")
        if uploaded_file:
            wait_for_upload(client, uploaded_file)
        else:
            raise ValueError("Uploaded file is None")
        return uploaded_file
    except Exception as e:
        raise RuntimeError(f"Failed to upload video file: {e}") from e


def _configure_generation_settings() -> types.GenerateContentConfig:
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",  # pyright: ignore[reportCallIssue]
            response_schema=types.Schema(  # pyright: ignore[reportCallIssue]
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "clip_title": types.Schema(type=types.Type.STRING),
                        "start_time": types.Schema(type=types.Type.STRING),
                        "end_time": types.Schema(type=types.Type.STRING),
                        "description": types.Schema(type=types.Type.STRING),
                        "voice_style_prompt": types.Schema(type=types.Type.STRING),
                        "tts_sync_script": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "start_s": types.Schema(type=types.Type.NUMBER),
                                    "end_s": types.Schema(type=types.Type.NUMBER),
                                    "text": types.Schema(type=types.Type.STRING),
                                },
                                required=["start_s", "end_s", "text"],
                            ),
                        ),
                    },
                    required=["clip_title", "start_time", "end_time", "description", "voice_style_prompt", "tts_sync_script"],
                ),
            ),
        )
        return config
    except Exception as e:
        raise RuntimeError(f"Error configuring generation settings: {e}") from e


def _generate_content(prompt: str, video_file: types.File, config: types.GenerateContentConfig) -> "types.GenerateContentResponse":
    try:
        print("Sending prompt and video to Gemini...")
        return client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, video_file],
            config=config,
        )
    except Exception as e:
        raise RuntimeError(f"Error during content generation: {e}") from e


def _parse_json_response(response: "types.GenerateContentResponse") -> List[MicroClip]:
    if response.text is None:
        raise ValueError("No response text returned from Gemini API")
    try:
        data = json.loads(response.text)
        
        micro_clips: List[MicroClip] = [
            MicroClip (
            clip_title=clip["clip_title"],
            start_time=(clip["start_time"]),
            end_time=(clip["end_time"]),
            voice_style_prompt=clip["voice_style_prompt"],
            description=clip["description"],
            tts_sync_script=[
                TTSScriptLine(
                    start_s=float(line["start_s"]),
                    end_s=float(line["end_s"]),
                    text=line["text"]
                ) for line in clip["tts_sync_script"]
            ]        ) 
        for clip in data]
        
        return micro_clips
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}") from e


def _delete_uploaded_file(uploaded_file: "types.File | None"):
    if uploaded_file and uploaded_file.name:
        try:
            print(f"\nCleaning up. Deleting file: {uploaded_file.name}")
            client.files.delete(name=uploaded_file.name)
            print("Cleanup complete.")
        except Exception as e:
            print(f"Warning: Failed to delete uploaded file: {e}")


def HMMSS_time_to_seconds(time: str) -> float:
    """Get seconds from HMMSS_time_to_seconds."""
    h, m, s = time.split(':')
    return float(h) * 3600 + float(m) * 60 + float(s)

def generate_micro_clips(video_file_path: str):
    """
    Uploads a video file, generates the micro-clips using Gemini, 
    and prints the resulting JSON.
    """
    uploaded_file = None
    try:
        uploaded_file = _upload_video(video_file_path)
        config = _configure_generation_settings()
        response = _generate_content(get_ai_prompt(), uploaded_file, config)
        clips_data = _parse_json_response(response)
        print("\nGenerated Micro-Clips JSON Output:")
        print(clips_data)
        return clips_data
    finally:
        _delete_uploaded_file(uploaded_file)


if __name__ == "__main__":
    try:
        generate_micro_clips(VIDEO_PATH)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
