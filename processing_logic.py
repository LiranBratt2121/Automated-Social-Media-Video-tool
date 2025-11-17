import io
import re
import os
import sys
import subprocess
from typing import Callable

from core.ai.marketing_generator import generate_and_save_content_package
from core.ai.video_analyzer import HMMSS_time_to_seconds, generate_micro_clips
from core.editor.subtitles_editor import burn_tts_subtitles
from core.editor.video_editor import combine_videos, cut_video, save_video_to_file
from core.video.compress_videos import compress_with_crop
from core.ai.tts_generator import generate_tts_audio
from core.video.process_audio import (
    adjust_audio_to_duration,
    get_video_duration_from_bytes,
    merge_audio_with_mp4,
)
from core.ai.audio_analyzer import get_word_timestamps_from_audio
from amazon_product_video_fetcher.core.extract_links import get_m3u8_links
from amazon_product_video_fetcher.core.download_video import download_video

def show_file_in_explorer(filepath: str):
    """
    Opens the file explorer and highlights the specified file.
    Works on Windows, macOS, and Linux.
    """
    if not os.path.exists(filepath):
        print(f"Cannot open file location: {filepath} not found.")
        return

    filepath = os.path.abspath(filepath)
    
    print(f"Opening file location: {filepath}")

    if sys.platform == "win32":
        subprocess.run(['explorer', '/select,', filepath])
    elif sys.platform == "darwin":
        subprocess.run(['open', '-R', filepath])
    else:
        subprocess.run(['xdg-open', os.path.dirname(filepath)])
        
def sanitize_filename(filename: str) -> str:
    """Removes illegal characters from a string to make it a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def process_video_from_url(amazon_url: str, progress_callback: Callable):
    """
    The main video processing pipeline, refactored to accept a URL and report progress.
    """
    try:
        # --- Step 1: Downloading ---
        progress_callback(0, 100, "Fetching download link from Amazon...")
        download_link = get_m3u8_links(amazon_url)[0]
        if not download_link:
            progress_callback(0, 100, "Error: Could not find video link.")
            return

        progress_callback(5, 100, f"Got link! Downloading video...")
        download_video(download_link, "input.mp4")
        progress_callback(15, 100, "Download complete!")

        # --- Step 2: Compression & AI Analysis ---
        progress_callback(15, 100, "Compressing video for analysis...")
        compressed_video_bytes = compress_with_crop("input.mp4", "output_crop.mp4")
        
        progress_callback(25, 100, "Analyzing video with AI...")
        micro_clips = generate_micro_clips("output_crop.mp4")
        if not micro_clips:
            progress_callback(0, 100, "Error: AI analysis failed.")
            return

        # --- Step 3: Clip Processing Loop ---
        total_clips = len(micro_clips)
        video_byte_clips = []
        progress_step = 60 / total_clips  # Processing takes 60% of the progress bar

        for idx, clip in enumerate(micro_clips):
            base_progress = 35 + (idx * progress_step)
            progress_callback(base_progress, 100, f"Processing Clip {idx+1}/{total_clips}: '{clip.clip_title}'")
            
            # (The internal logic for processing a single clip remains the same)
            clip_start = HMMSS_time_to_seconds(clip.start_time)
            clip_end = HMMSS_time_to_seconds(clip.end_time)
            compressed_video_bytes.seek(0)
            cloned_bytes = io.BytesIO(compressed_video_bytes.getvalue())
            clip_cut = cut_video(cloned_bytes, clip_start, clip_end)

            all_clip_text = " ".join([p.text for p in clip.tts_sync_script])
            clip_audio = generate_tts_audio(content=all_clip_text, style_prompt=clip.voice_style_prompt)

            video_duration = get_video_duration_from_bytes(clip_cut)
            final_clip_audio, _ = adjust_audio_to_duration(clip_audio, video_duration)

            word_timings = get_word_timestamps_from_audio(final_clip_audio, all_clip_text)
            
            word_phrases = []
            word_counter = 0
            for line in clip.tts_sync_script:
                num_words_in_line = len(line.text.split())
                phrase = word_timings[word_counter : word_counter + num_words_in_line]
                if phrase:
                    word_phrases.append(phrase)
                word_counter += num_words_in_line
            
            if not word_phrases:
                clip_with_audio = merge_audio_with_mp4(final_clip_audio, clip_cut)
                video_byte_clips.append(clip_with_audio)
                continue

            clip_with_audio = merge_audio_with_mp4(final_clip_audio, clip_cut)
            clip_with_subtitles = burn_tts_subtitles(clip_with_audio, word_phrases)
            video_byte_clips.append(clip_with_subtitles)

        # --- Step 4: Final Assembly & Saving ---
        if not video_byte_clips:
            progress_callback(0, 100, "Error: No clips were processed successfully.")
            return

        progress_callback(95, 100, "Assembling final video...")
        full_video = combine_videos(video_byte_clips)

        # Use AI-generated title for the filename
        final_filename_base = sanitize_filename(micro_clips[0].clip_title)
        video_filename = f"{final_filename_base}.mp4"
        text_filename = f"{final_filename_base}_descriptions.txt"

        save_video_to_file(full_video, video_filename)

        progress_callback(97, 100, "Generating social media copy...")
        generate_and_save_content_package(micro_clips=micro_clips, output_filename=text_filename)

        show_file_in_explorer(video_filename)
        progress_callback(100, 100, f"Complete! Saved as {video_filename}")

    except Exception as e:
        error_message = f"An error occurred: {e}"
        print(error_message)
        progress_callback(0, 100, error_message)