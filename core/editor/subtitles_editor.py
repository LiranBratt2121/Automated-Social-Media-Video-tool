import io
import os
import tempfile
import ffmpeg
from typing import List

from ..ai.ai_types import WordTimestamp

def burn_tts_subtitles(
    video_bytes: io.BytesIO, 
    phrases: List[List[WordTimestamp]]
) -> io.BytesIO:
    """
    Burns TikTok-style subtitles with a professional, phrase-based approach.
    - Only the current phrase is displayed on screen.
    - The full phrase text persists (in white) during word highlighting.
    - The last word's highlight persists through silent gaps until the next phrase.
    """
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file, \
         tempfile.NamedTemporaryFile(suffix='.ass', delete=False, mode='w', encoding='utf-8') as ass_file, \
         tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as out_file:

        video_file_path, ass_file_path, out_file_path = video_file.name, ass_file.name, out_file.name

        video_bytes.seek(0)
        video_file.write(video_bytes.read())
        
        ass_file.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
        ass_file.write("[V4+ Styles]\n")
        style_line = "Style: White,Arial Black,90,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,6,2,5,50,50,200,1\n"
        ass_file.write(style_line)
        ass_file.write("[Events]\n")
        ass_file.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

        # Create the full, non-highlighted subtitles for each phrase.
        for phrase_index, phrase in enumerate(phrases):
            if not phrase:
                continue
            
            phrase_text = " ".join([wt.word for wt in phrase]).upper()
            start_time_s = phrase[0].start_s
            
            # Determine the end time for the whole phrase
            end_time_s = phrase[-1].end_s
            is_not_last_phrase = phrase_index < len(phrases) - 1
            if is_not_last_phrase and phrases[phrase_index + 1]:
                # Make the text persist until the next phrase begins
                end_time_s = phrases[phrase_index + 1][0].start_s

            start_str = format_ass_time(start_time_s)
            end_str = format_ass_time(end_time_s)
            ass_file.write(f"Dialogue: 0,{start_str},{end_str},White,,0,0,0,,{phrase_text}\n")


        # 2. Second, create the word-by-word yellow highlight effect on a higher layer.
        #    This layer will draw ON TOP of the white text we just created.
        for phrase in phrases:
            if not phrase:
                continue

            for word_info in phrase:
                start_str = format_ass_time(word_info.start_s)
                end_str = format_ass_time(word_info.end_s)
                
                # The "text" for this layer is just the single highlighted word
                highlighted_word = f"{{\\c&H00FFFF&}}{word_info.word.upper()}{{\\c&HFFFFFF&}}"
                
                # We use a trick with alignment tags to place the highlighted word
                # exactly where it belongs in the sentence. \pos(x,y) might be needed for perfection,
                # but for centered text, creating the full line is more robust.
                
                # Rebuild the full sentence to find the position of the current word
                full_phrase_text = " ".join([wt.word for wt in phrase]).upper()
                words_in_phrase = full_phrase_text.split()
                current_word_index = -1
                for i, w in enumerate(words_in_phrase):
                     if w == word_info.word.upper():
                         # A simple check, might need refinement if words repeat
                         current_word_index = i
                         break

                highlighted_line_parts = []
                for i, w in enumerate(words_in_phrase):
                    if i == current_word_index:
                        highlighted_line_parts.append(highlighted_word)
                    else:
                        # Make other words transparent for this layer
                        highlighted_line_parts.append(f"{{\\alpha&HFF}}{w}")

                final_line = " ".join(highlighted_line_parts)

                # The previous method of rewriting the whole line is simpler and more reliable
                final_line_parts = []
                all_words = [w.word.upper() for w in phrase]
                for i, w in enumerate(all_words):
                    if w == word_info.word.upper(): # Simple check
                         final_line_parts.append(f"{{\\c&H00FFFF&}}{w}{{\\c&HFFFFFF&}}")
                    else:
                         final_line_parts.append(w)
                final_line = " ".join(final_line_parts)


                ass_file.write(f"Dialogue: 1,{start_str},{end_str},White,,0,0,0,,{final_line}\n")


    try:
        ass_path_escaped = ass_file_path.replace('\\', '/').replace(':', r'\:')
        (
            ffmpeg.input(video_file_path)
            .output(out_file_path, vf=f"ass='{ass_path_escaped}'", vcodec='libx264', preset='fast', acodec='copy')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        with open(out_file_path, 'rb') as f:
            return io.BytesIO(f.read())

    except ffmpeg.Error as e:
        print(f"❌ FFmpeg error during burn_tts_subtitles:\n{e.stderr.decode('utf-8')}")
        raise
    finally:
        for path in [video_file_path, ass_file_path, out_file_path]:
            if os.path.exists(path):
                os.unlink(path)


def format_ass_time(seconds: float) -> str:
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"