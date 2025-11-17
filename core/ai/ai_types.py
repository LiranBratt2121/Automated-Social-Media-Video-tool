from dataclasses import dataclass, field
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

@dataclass
class SocialMediaCaption:
    hook: str = "Caption generation failed. Please check logs."
    value: str = ""
    cta: str = ""
    hashtags: str = ""

@dataclass
class PinnedComment:
    text: str = "Comment generation failed."

@dataclass
class MarketingPackage:
    social_media_caption: SocialMediaCaption = field(default_factory=SocialMediaCaption)
    pinned_comment: PinnedComment = field(default_factory=PinnedComment)
