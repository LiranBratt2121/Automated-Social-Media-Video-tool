import io
import ffmpeg
import os
from typing import Optional


TARGET_MB = 7
OUTPUT_RESOLUTION = (1080, 1920)
AUDIO_BITRATE = "128k"
VIDEO_PRESET = "slow"


def get_video_info(path: str) -> dict:
    """Return video metadata using ffmpeg.probe (no subprocess)."""
    return ffmpeg.probe(path)


def get_duration_seconds(info: dict) -> float:
    """Extract duration in seconds from ffmpeg.probe info."""
    return float(info["format"]["duration"])


def calculate_video_bitrate(duration: float, target_mb: float = TARGET_MB) -> int:
    """Return video bitrate (kbps) to stay under target file size."""
    audio_bitrate_kbps = int(AUDIO_BITRATE.rstrip("k"))
    total_bitrate_kbps = int((target_mb * 8 * 1024) / duration)
    video_bitrate_kbps = total_bitrate_kbps - audio_bitrate_kbps

    if video_bitrate_kbps <= 0:
        raise ValueError("Target size too small for given duration and audio bitrate.")

    return video_bitrate_kbps


def _build_common_output(video_stream, audio_stream, output_path: str, bitrate_kbps: int):
    """Apply shared compression, encoding, and output configuration."""
    return (
        ffmpeg.output(
            video_stream,
            audio_stream,
            output_path,
            vcodec="libx264",
            video_bitrate=f"{bitrate_kbps}k",
            maxrate=f"{bitrate_kbps}k",
            bufsize=f"{bitrate_kbps*2}k",
            preset=VIDEO_PRESET,
            acodec="aac",
            audio_bitrate=AUDIO_BITRATE,
            movflags="+faststart",
            loglevel="info",
        )
        .overwrite_output()
    )


def compress_with_blur(input_path: str, output_path: Optional[str] = None):
    """Convert video to portrait (9:16) with blurred background and ≤7MB output."""
    output_path = output_path or "output_blur.mp4"
    info = get_video_info(input_path)
    duration = get_duration_seconds(info)
    bitrate = calculate_video_bitrate(duration)

    w, h = OUTPUT_RESOLUTION
    inp = ffmpeg.input(input_path)

    # Ensure even width/height using trunc(.../2)*2 trick
    main = (
        inp.video
        .filter(
            "scale",
            # CORRECTED: Use double backslash \\, to escape for Python AND ffmpeg
            rf"trunc(iw*min({h}/ih,{w}/iw)/2)*2",
            rf"trunc(ih*min({h}/ih,{w}/iw)/2)*2",
        )
        .filter("format", "yuv420p")
    )

    background = (
        inp.video
        .filter(
            "scale",
            # CORRECTED: Use double backslash \\,
            rf"trunc(iw*max({h}/ih,{w}/iw)/2)*2",
            rf"trunc(ih*max({h}/ih,{w}/iw)/2)*2",
        )
        .filter("gblur", sigma=25)
        .filter("crop", w, h)
        .filter("format", "yuv420p")
    )

    composed = (
        ffmpeg.overlay(background, main, x="(W-w)/2", y="(H-h)/2")
        .filter("format", "yuv420p")
    )

    audio = inp.audio
    stream = _build_common_output(composed, audio, output_path, bitrate)

    # Run with logs visible
    print("🚀 Starting FFmpeg process...")
    ffmpeg.run(stream, overwrite_output=True, capture_stdout=False, capture_stderr=False)

    size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Blurred output created: {output_path} ({size:.2f} MB)")
    
    video_bytesIO = io.BytesIO()
    with open(output_path, "rb") as f:
        video_bytesIO.write(f.read())
    video_bytesIO.seek(0)
    
    return video_bytesIO
    
    
def compress_with_crop(input_path: str, output_path: Optional[str] = None):
    """Convert video to cropped 9:16 and ≤7MB output."""
    output_path = output_path or "output_crop.mp4"
    info = get_video_info(input_path)
    duration = get_duration_seconds(info)
    bitrate = calculate_video_bitrate(duration)

    inp = ffmpeg.input(input_path)
    cropped = (
        inp.video.filter("crop", "ih*9/16", "ih")
        .filter("scale", *OUTPUT_RESOLUTION)
        .filter("format", "yuv420p")
    )

    audio = inp.audio
    stream = _build_common_output(cropped, audio, output_path, bitrate)

    ffmpeg.run(stream, overwrite_output=True, capture_stdout=False, capture_stderr=False)
    
    bytesIO_video = io.BytesIO()
    with open(output_path, "rb") as f:
        bytesIO_video.write(f.read())
    bytesIO_video.seek(0)

    size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Cropped output created: {output_path} ({size:.2f} MB)")
    return bytesIO_video

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage:")
        print("  python compress_tiktok_video.py blur <input.mp4> [output.mp4]")
        print("  python compress_tiktok_video.py crop <input.mp4> [output.mp4]")
        sys.exit(1)

    mode = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    if mode == "blur":
        compress_with_blur(input_file, output_file)
    elif mode == "crop":
        compress_with_crop(input_file, output_file)
    else:
        print("❌ Invalid mode. Use 'blur' or 'crop'.")
