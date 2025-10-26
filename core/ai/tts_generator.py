import struct
import io
from google.genai import types
from .shared import init_client

MODEL_NAME = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE_NAME = "Kore" 

client = init_client()

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
            
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """
    Generates a WAV file header for the given raw signed PCM 16-bit audio data 
    and parameters, returning the complete WAV file as bytes.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    
    num_channels = 1
    data_size = len(audio_data)
    
    if bits_per_sample is None or sample_rate is None:
        raise ValueError("Invalid MIME type: unable to parse bits per sample or rate.")
    
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    # WAV header format: http://soundfile.sapp.org/doc/WaveFormat/
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data


def _configure_tts_settings() -> types.GenerateContentConfig:
    """
    Creates the necessary configuration object for TTS generation,
    using the style_prompt as the system instruction.
    """
    try:
        # system_instruction_content = types.Content(
        #     role="system",
        #     parts=[types.Part.from_text(text=style_prompt)]
        # )

        config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            
            # system_instruction=system_instruction_content,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=DEFAULT_VOICE_NAME,
                    )
                )
            ),
        )
        return config
    except Exception as e:
        raise RuntimeError(f"Error configuring TTS settings: {e}") from e


def _stream_content(
    content: str,
    style_prompt: str,
    config: types.GenerateContentConfig,
    max_retries: int = 3,
    delay: float = 2.0
) -> tuple[bytes, str]:
    """
    Calls the streaming API to accumulate raw audio data and the mime type.
    Retries automatically if no audio data is returned.
    
    Returns a tuple of (full_audio_data, mime_type).
    """
    import time

    full_text = f"[Style: {style_prompt}, and Aim for 12 cps]\n\n{content}"

    for attempt in range(1, max_retries + 1):
        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=full_text)],
                ),
            ]

            full_audio_data: bytes = b""
            mime_type: str = ""

            stream = client.models.generate_content_stream(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )

            for chunk in stream:
                if not chunk.candidates:
                    continue

                candidate = chunk.candidates[0]
                if (candidate.content and candidate.content.parts and
                    candidate.content.parts[0].inline_data and
                    candidate.content.parts[0].inline_data.data is not None):

                    inline_data = candidate.content.parts[0].inline_data
                    
                    if inline_data.data is not None:
                        full_audio_data += inline_data.data
                        
                    if not mime_type:
                        mime_type = inline_data.mime_type or ""

            if full_audio_data and mime_type:
                return full_audio_data, mime_type

            raise ValueError("No audio data received from API.")

        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    # Final return after all attempts exhausted
    print("❌ All retries failed. Returning empty result.")
    return b"", ""



def generate_tts_audio(content: str, style_prompt: str) -> io.BytesIO:
    """
    Generates TTS audio for the given content and style prompt, returning a complete WAV file 
    as an io.BytesIO object.

    Args:
        content: The text content to be synthesized (e.g., 'Then, give them a satisfying spin for instant stress relief!').
        style_prompt: A detailed prompt describing the desired voice style and tone
                      (e.g., 'Speak with an energetic, slightly amazed, and fast-paced tone...').

    Returns:
        An io.BytesIO object containing the complete WAV audio file, or None on failure.
    """
    
    print(f"Synthesizing content with base voice '{DEFAULT_VOICE_NAME}' and style prompt: '{style_prompt[:40]}...'")
    
    try:
        config = _configure_tts_settings()
        audio_result = _stream_content(content, style_prompt, config)

        print(f"Generated tts for {content =}")
        full_audio_data, mime_type = audio_result

        wav_bytes = convert_to_wav(full_audio_data, mime_type)
        print(f"Successfully generated WAV data ({len(wav_bytes)} bytes).")
        
        audio_buffer = io.BytesIO(wav_bytes)
        audio_buffer.seek(0)
        return audio_buffer

    except RuntimeError as e:
        print(f"TTS Generation failed: {e}")
        raise RuntimeError(f"Unexpected error: {e}") from e
    except Exception as e:
        print(f"An unexpected error occurred during TTS generation: {e}")
        raise RuntimeError(f"Unexpected error: {e}") from e


if __name__ == "__main__":
    try:
        example_text = "Then, give them a satisfying spin for instant stress relief!"
        example_style = "Speak with an energetic, slightly amazed, and fast-paced tone, like discovering a cool new gadget."
        
        print("-" * 50)
        print("Running example with detailed style prompt.")
        
        audio_io = generate_tts_audio(
            content=example_text,
            style_prompt=example_style
        )

        if audio_io:
            output_filename = "output_tts_styled.wav"

            with open(output_filename, "wb") as f:
                f.write(audio_io.read())
            print(f"Audio saved successfully to {output_filename}")
        else:
            print("Audio generation failed.")
            
    except RuntimeError as e:
        print(f"\nExecution terminated: {e}")
