import ffmpeg
import io
import tempfile
import os
from pathlib import Path
from typing import Tuple


def adjust_audio_to_duration(
    audio_buffer: io.BytesIO,
    target_duration_s: float
) -> Tuple[io.BytesIO, float]:
    """
    Adjust audio speed to exactly match target duration.
    
    Args:
        audio_buffer: Input audio as BytesIO buffer (WAV format)
        target_duration_s: Exact desired duration in seconds
    
    Returns:
        New BytesIO buffer with adjusted audio
    """
    # Create temp files
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_input:
        temp_input_path = temp_input.name
        audio_buffer.seek(0)
        temp_input.write(audio_buffer.read())
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
        temp_output_path = temp_output.name
    
    try:
        # Get actual duration
        probe = ffmpeg.probe(temp_input_path)
        actual_duration_s = float(probe['streams'][0]['duration'])
        
        print(f"  Adjusting: {actual_duration_s:.3f}s → {target_duration_s:.3f}s")
        
        # Calculate exact speed factor
        speed_factor = actual_duration_s / target_duration_s
        print(f"  Speed factor: {speed_factor:.4f}x")
        
        # Build atempo filter chain for values outside 0.5-2.0 range
        atempo_filters = []
        remaining_speed = speed_factor
        
        while remaining_speed > 2.0:
            atempo_filters.append("atempo=2.0")
            remaining_speed /= 2.0
        
        while remaining_speed < 0.5:
            atempo_filters.append("atempo=0.5")
            remaining_speed /= 0.5
        
        atempo_filters.append(f"atempo={remaining_speed:.6f}")
        
        # Run ffmpeg - chain the atempo filters properly
        stream = ffmpeg.input(temp_input_path)
        audio = stream.audio
        
        # Apply each atempo filter in the chain
        for atempo in atempo_filters:
            audio = audio.filter('atempo', atempo.split('=')[1])
        
        stream = ffmpeg.output(audio, temp_output_path)
        
        try:
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        except ffmpeg.Error as e:
            print(f"  FFmpeg error stdout: {e.stdout.decode('utf8')}")
            print(f"  FFmpeg error stderr: {e.stderr.decode('utf8')}")
            raise
        
        # Read output into BytesIO
        output_buffer = io.BytesIO()
        with open(temp_output_path, 'rb') as f:
            output_buffer.write(f.read())
        output_buffer.seek(0)
        
        # Verify final duration
        probe = ffmpeg.probe(temp_output_path)
        final_duration_s = float(probe['streams'][0]['duration'])
        print(f"  ✓ Final duration: {final_duration_s:.3f}s")
        
        return output_buffer, speed_factor
        
    finally:
        # Cleanup temp files
        if os.path.exists(temp_input_path):
            os.unlink(temp_input_path)
        if os.path.exists(temp_output_path):
            os.unlink(temp_output_path)


def merge_audio_files(input_files: list[io.BytesIO]) -> io.BytesIO:
    """
    Merge multiple WAV files from in-memory buffers into one WAV file.
    Returns:
        BytesIO buffer with merged audio.
    """
    print(f"🔗 Merging {len(input_files)} audio files...")

    concat_list_path = None
    temp_files = []

    try:
        # Save all BytesIO inputs to temporary .wav files
        for i, audio_buf in enumerate(input_files):
            temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp.write(audio_buf.getvalue())
            temp.flush()
            temp_files.append(temp.name)
            temp.close()

        # Create concat list for ffmpeg
        concat_list = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        for path in temp_files:
            concat_list.write(f"file '{os.path.abspath(path)}'\n")
        concat_list_path = concat_list.name
        concat_list.close()

        # Temporary output file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
            temp_output_path = temp_output.name

        # Merge using ffmpeg concat demuxer
        (
            ffmpeg
            .input(concat_list_path, format='concat', safe=0)
            .output(temp_output_path, c='copy')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        # Load merged output into BytesIO
        output_buffer = io.BytesIO()
        with open(temp_output_path, 'rb') as f:
            output_buffer.write(f.read())
        output_buffer.seek(0)

        print("✅ Merged audio successfully")
        return output_buffer

    finally:
        if concat_list_path and os.path.exists(concat_list_path):
            os.remove(concat_list_path)
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)


def merge_audio_with_mp4(audio_bytes_io: io.BytesIO, video_bytes_io: io.BytesIO) -> io.BytesIO:
    """
    Merge audio from BytesIO into video from BytesIO (MP4) using temp files
    for a stable 2-input operation.
    
    Returns:
        BytesIO buffer with merged video
    """
    
    # Create temp files for video, audio, and output
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
        temp_video_path = temp_video.name
        video_bytes_io.seek(0)
        temp_video.write(video_bytes_io.read())
    
    # Assuming audio is WAV, but suffix doesn't strictly matter
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
        temp_audio_path = temp_audio.name
        audio_bytes_io.seek(0)
        temp_audio.write(audio_bytes_io.read())
        
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
        temp_output_path = temp_output.name

    try:
        video_input = ffmpeg.input(temp_video_path)
        audio_input = ffmpeg.input(temp_audio_path)

        stream = ffmpeg.output(
            video_input.video,
            audio_input.audio,
            temp_output_path,
            vcodec='copy',  # Copy video without re-encoding
            acodec='aac',   # Re-encode audio to AAC
            strict='experimental',
            map_metadata='0' # Keep metadata from the video file
        )
        
        print("🚀 Starting FFmpeg audio/video merge...")
        # Run the single command
        stream.overwrite_output().run(capture_stdout=True, capture_stderr=True)
        
        # Read the final merged file into BytesIO
        output_buffer = io.BytesIO()
        with open(temp_output_path, 'rb') as f:
            output_buffer.write(f.read())
        output_buffer.seek(0)
        
        print(f"✅ Merged audio into video successfully")
        return output_buffer
        
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg merge error stdout: {e.stdout.decode('utf8')}")
        print(f"❌ FFmpeg merge error stderr: {e.stderr.decode('utf8')}")
        raise
        
    finally:
        # Clean up all temporary files
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            


def get_video_duration_from_bytes(video_bytes: io.BytesIO) -> float:
    """
    Returns video duration in seconds from a BytesIO object using ffmpeg.probe.
    Reliable even for short or in-memory videos.
    """
    video_bytes.seek(0)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        temp_file.write(video_bytes.read())
        temp_file.flush()
        temp_path = temp_file.name

    try:
        metadata = ffmpeg.probe(temp_path)
        duration_str = metadata.get("format", {}).get("duration")

        if not duration_str:
            raise ValueError("No duration found in FFmpeg metadata.")

        duration = float(duration_str)
        return duration

    except Exception as e:
        print(f"⚠️ FFmpeg probe failed for {temp_path}: {e}")
        return 0.0

    finally:
        # Delete the temp file safely
        try:
            os.remove(temp_path)
        except OSError:
            pass


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Test adjust_audio_to_duration:")
        print("    python process_clips.py adjust <input.wav> <target_duration_s> [output.wav]")
        print("  Test merge_audio_files:")
        print("    python process_clips.py merge <output.wav> <input1.wav> <input2.wav> ...")
        print("\nExamples:")
        print("  python process_clips.py adjust audio.wav 3.5 output.wav")
        print("  python process_clips.py merge merged.wav clip1.wav clip2.wav clip3.wav")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "adjust":
        if len(sys.argv) < 4:
            print("Error: adjust requires <input.wav> <target_duration_s> [output.wav]")
            sys.exit(1)
        
        input_file = sys.argv[2]
        target_duration = float(sys.argv[3])
        output_file = sys.argv[4] if len(sys.argv) > 4 else f"adjusted_{target_duration}s.wav"
        
        print(f"Loading {input_file}...")
        with open(input_file, 'rb') as f:
            audio_buffer = io.BytesIO(f.read())
        
        print(f"Adjusting to {target_duration}s...")
        adjusted = adjust_audio_to_duration(audio_buffer, target_duration)
        
        print(f"Saving to {output_file}...")
        with open(output_file, 'wb') as f:
            f.write(adjusted[0].read())
        
        print(f"✅ Done! Saved to {output_file}")
    
    elif command == "merge":
        if len(sys.argv) < 4:
            print("Error: merge requires <output.wav> <input1.wav> <input2.wav> ...")
            sys.exit(1)
        
        output_file = sys.argv[2]
        input_files = [Path(f) for f in sys.argv[3:]]
        
        input_fils_bytesIO = [io.BytesIO(open(f, 'rb').read()) for f in input_files]
        
        print(f"Merging {len(input_files)} files...")
        for f in input_files:
            if not f.exists():
                print(f"  ERROR: File not found: {f}")
                sys.exit(1)
            print(f"  - {f}")
        
        merged = merge_audio_files(input_fils_bytesIO)
        
        print(f"Saving to {output_file}...")
        with open(output_file, 'wb') as f:
            f.write(merged.read())
        
        print(f"✅ Done! Saved to {output_file}")
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'adjust' or 'merge'")
        sys.exit(1)