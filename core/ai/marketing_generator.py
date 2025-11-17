import json
from typing import List
from .shared import init_client
from .ai_types import MarketingPackage, SocialMediaCaption, PinnedComment, MicroClip

client = init_client()
MODEL_NAME = "gemini-2.0-flash-lite"
PROMPT_PATH = "core/ai/marketing_prompt.txt"

def get_marketing_prompt() -> str:
    """Reads the marketing asset generation prompt from the file."""
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("Error: marketing_prompt.txt not found.")
        return ""

def generate_marketing_assets(raw_text_content: str) -> MarketingPackage:
    """
    Uses the AI to generate a structured MarketingPackage object.

    Args:
        raw_text_content: The string content of all the AI-generated video ideas.

    Returns:
        A MarketingPackage dataclass instance containing the generated assets.
    """
    print("  ✍️ Generating complete marketing package with AI...")
    
    full_prompt = get_marketing_prompt() + "\n\n--- INPUT DATA ---\n" + raw_text_content

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[full_prompt],
            config={"response_mime_type": "application/json"} 
        )
        
        if not response.text:
            raise ValueError("AI response is empty")
        
        data = json.loads(response.text)
        
        caption_data = data.get("social_media_caption", {})
        comment_data = data.get("pinned_comment", {})

        caption = SocialMediaCaption(
            hook=caption_data.get("hook", ""),
            value=caption_data.get("value", ""),
            cta=caption_data.get("cta", ""),
            hashtags=caption_data.get("hashtags", "")
        )
        
        comment = PinnedComment(
            text=comment_data.get("text", "")
        )
        
        print("  ✅ Marketing package generated successfully.")
        return MarketingPackage(social_media_caption=caption, pinned_comment=comment)

    except (json.JSONDecodeError, Exception) as e:
        print(f"  ❌ Error generating or parsing marketing assets: {e}")
        return MarketingPackage()
    

def generate_and_save_content_package(
    micro_clips: List[MicroClip],
    output_filename: str,
):
    """
    Generates all marketing text assets and saves them to a single text file,
    using a structured MarketingPackage object.
    """
    raw_ideas_content = "--- 💡 AI Generated Video Ideas ---\n\n"
    for i, clip in enumerate(micro_clips):
        raw_ideas_content += f"Clip {i+1}: {clip.clip_title}\n"
        raw_ideas_content += f"Description: {clip.description}\n"
        raw_ideas_content += f"Script: {' '.join([line.text for line in clip.tts_sync_script])}\n\n"

    marketing_package = generate_marketing_assets(raw_ideas_content)
    
    final_text_content = raw_ideas_content
    final_text_content += "\n" + "="*50 + "\n\n"
    final_text_content += "--- 📱 READY-TO-POST SOCIAL MEDIA CONTENT ---\n\n"
    
    final_text_content += "COPY-PASTE THIS CAPTION:\n"
    final_text_content += "-"*25 + "\n"
    final_text_content += f"{marketing_package.social_media_caption.hook}\n\n"
    final_text_content += f"{marketing_package.social_media_caption.value}\n\n"
    final_text_content += f"{marketing_package.social_media_caption.cta}\n\n"
    final_text_content += f"{marketing_package.social_media_caption.hashtags}\n"
    final_text_content += "-"*25 + "\n\n"

    final_text_content += "COPY-PASTE THIS AS YOUR FIRST COMMENT (AND PIN IT):\n"
    final_text_content += "-"*50 + "\n"
    final_text_content += f"{marketing_package.pinned_comment.text}\n"
    final_text_content += "-"*50 + "\n"

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(final_text_content)
    print(f"  ✅ Content package saved to {output_filename}")