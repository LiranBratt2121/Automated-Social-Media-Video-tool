from dataclasses import dataclass
from typing import List

@dataclass
class WordTimestamp:
    word: str
    start_s: float
    end_s: float
    
@dataclass
class TTSScriptLine:
    start_s: float
    end_s: float
    text: str

@dataclass
class MicroClip:
    clip_title: str
    start_time: str
    end_time: str
    description: str
    voice_style_prompt: str
    tts_sync_script: List[TTSScriptLine]
