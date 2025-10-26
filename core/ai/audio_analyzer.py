import io
from typing import List
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from .ai_types import WordTimestamp

def get_word_timestamps_from_audio(
    audio_buffer: io.BytesIO,
    original_text: str
) -> List[WordTimestamp]:
    """
    Analyzes an audio buffer using Pydub's `detect_nonsilent` to create
    highly accurate, word-level timestamps that respect silent gaps.
    """
    audio_buffer.seek(0)
    audio = AudioSegment.from_file(audio_buffer, format="wav")

    print("  🤫 Analyzing audio with Pydub's `detect_nonsilent` for precise timing...")

    nonsilent_ranges = detect_nonsilent(
        audio,
        min_silence_len=200,    # A pause of 200ms is considered a gap
        silence_thresh=-40,     # Quieter than -40dBFS is silence
    )

    if not nonsilent_ranges:
        print("  ⚠️ Pydub found no non-silent audio. Cannot generate timestamps.")
        return []

    words = original_text.split()
    total_words = len(words)
    
    total_sound_duration_ms = sum(end - start for start, end in nonsilent_ranges)

    word_timings: List[WordTimestamp] = []
    word_index = 0

    for start_ms, end_ms in nonsilent_ranges:
        chunk_duration_ms = end_ms - start_ms
        
        words_in_chunk_count = round(
            (chunk_duration_ms / total_sound_duration_ms) * total_words
        ) if total_sound_duration_ms > 0 else 0
        
        words_in_chunk_count = min(words_in_chunk_count, total_words - word_index)
        
        is_last_chunk = (nonsilent_ranges[-1] == [start_ms, end_ms])
        if is_last_chunk:
            words_in_chunk_count = total_words - word_index

        chunk_words = words[word_index : word_index + words_in_chunk_count]
        if not chunk_words:
            continue

        time_per_word_ms = chunk_duration_ms / len(chunk_words)
        
        chunk_current_time_ms = start_ms
        for word in chunk_words:
            start_s = chunk_current_time_ms / 1000.0
            end_s = (chunk_current_time_ms + time_per_word_ms) / 1000.0
            
            word_timings.append(WordTimestamp(
                word=word,
                start_s=start_s,
                end_s=end_s
            ))
            chunk_current_time_ms += time_per_word_ms
        
        word_index += len(chunk_words)

    print(f"  ✅ Mapped {len(word_timings)} words to precise audio events.")
    return word_timings
