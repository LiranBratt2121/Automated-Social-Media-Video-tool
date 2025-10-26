import io
import ffmpeg
import tempfile
import os
from contextlib import contextmanager
from typing import List, Generator, Tuple


@contextmanager
def _managed_temp_files(
    input_buffers: List[io.BytesIO], create_concat_list: bool = False
) -> Generator[Tuple[List[str], str, str | None], None, None]:
    """
    A context manager to elegantly handle all temporary file operations for ffmpeg.

    This single helper function creates temporary files from in-memory data,
    yields their paths for ffmpeg to use, and then GUARANTEES they are all
    cleaned up afterwards, even if an error occurs. This keeps the main
    functions clean and focused on their specific ffmpeg tasks.
    """
    temp_input_paths = []
    temp_output_path = ""
    concat_list_path = ""
    
    try:
        # Create temporary input files from each memory buffer
        for buf in input_buffers:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_in:
                buf.seek(0)
                temp_in.write(buf.read())
                temp_input_paths.append(temp_in.name)

        # Create a temporary output file path
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_out:
            temp_output_path = temp_out.name

        # If needed for combining, create a list file for the concat demuxer
        if create_concat_list:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as concat_list:
                for path in temp_input_paths:
                    concat_list.write(f"file '{os.path.abspath(path)}'\n")
                concat_list_path = concat_list.name

        # Yield the necessary paths to the calling function
        yield temp_input_paths, temp_output_path, concat_list_path

    finally:
        # This block runs no matter what, ensuring all temp files are deleted
        all_paths = temp_input_paths + [temp_output_path, concat_list_path]
        for path in all_paths:
            if path and os.path.exists(path):
                os.remove(path)


def cut_video(input_bytes: io.BytesIO, start: float, end: float) -> io.BytesIO:
    """
    Cuts a video to a precise start and end time by re-encoding.
    """
    duration = end - start
    
    with _managed_temp_files([input_bytes]) as (input_paths, output_path, _):
        input_path = input_paths[0]
        try:
            (
                ffmpeg.input(input_path, ss=start, t=duration)
                .output(output_path, vcodec='libx264', acodec='aac', strict='experimental')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            print(f"Successfully cut video between {start=} and {end=} (duration: {duration})")
        except ffmpeg.Error as e:
            print(f"❌ FFmpeg error during cut_video:\n{e.stderr.decode('utf-8')}")
            raise

        with open(output_path, "rb") as f:
            return io.BytesIO(f.read())


def combine_videos(mp4_clips: List[io.BytesIO]) -> io.BytesIO:
    """
    Combines multiple MP4 clips using the ffmpeg concat demuxer.
    """
    with _managed_temp_files(mp4_clips, create_concat_list=True) as (_, output_path, concat_path):
        try:
            (
                ffmpeg.input(concat_path, format='concat', safe=0)
                .output(output_path, c='copy')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            print(f"Successfully combined {len(mp4_clips)} videos")
        except ffmpeg.Error as e:
            print(f"❌ FFmpeg error during combine_videos:\n{e.stderr.decode('utf-8')}")
            raise

        with open(output_path, 'rb') as f:
            return io.BytesIO(f.read())


def save_video_to_file(video_bytes: io.BytesIO, output_path: str):
    """Saves a video from an in-memory buffer to a file on disk."""
    with open(output_path, 'wb') as f:
        f.write(video_bytes.getvalue())
    print(f"Video saved to {output_path}")