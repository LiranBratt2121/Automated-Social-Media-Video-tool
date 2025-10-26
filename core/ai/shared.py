import os
from google import genai
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

def init_client() -> genai.Client:
    if not API_KEY:
        raise RuntimeError(
            "Error initializing Gemini client. Make sure the GEMINI_API_KEY environment variable is set."
        )
    try:
        print("Initializing Gemini client...")
        return genai.Client(api_key=API_KEY)
    except Exception as e:
        raise RuntimeError(f"Error initializing Gemini client: {e}") from e

