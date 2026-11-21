"""ai_engine.py - calls the Gemini API while keeping the key on the server."""
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

MODEL = os.getenv("AI_MODEL", "gemini-3.5-flash-lite")
SYSTEM_PROMPT = (
    "You are HETA AI, a friendly and intelligent assistant. Tagline: 'Your Intelligence. "
    "Your Assistant. Your HETA AI.' Answer clearly and accurately. Reply in the same language "
    "the user writes in (English or Tamil). When you write code, put it in fenced code blocks "
    "with the language name. Explain things simply for beginners when asked."
)


class AIError(Exception):
    """A friendly error message that is safe to show the user."""


def get_ai_response(history):
    """Send the last 20 chat turns to Gemini and return its text response."""
    # ANTHROPIC_API_KEY is accepted as a fallback for users who pasted their
    # Google key into the old README's variable before upgrading this project.
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key == "your-api-key-here":
        raise AIError("API key missing. Add your Google AI Studio key as GEMINI_API_KEY in the root .env file, then restart the server.")

    contents = [
        {
            "role": "model" if item["role"] == "assistant" else "user",
            "parts": [{"text": item["content"]}],
        }
        for item in history[-20:]
    ]
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 2000},
    }
    for attempt in range(3):
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as error:
            try:
                details = json.loads(error.read().decode("utf-8"))
                message = details.get("error", {}).get("message", "")
            except (ValueError, AttributeError):
                message = ""
            if error.code == 503 and attempt < 2:
                time.sleep(attempt + 1)
                continue
            if error.code in (400, 401, 403):
                raise AIError("Gemini rejected the API key or request. Check that GEMINI_API_KEY is a valid Google AI Studio key and that AI_MODEL is available.") from None
            if error.code == 429:
                raise AIError("Gemini rate limit reached. Wait a moment and try again.") from None
            raise AIError(f"Gemini API error ({error.code}): {message or 'request failed'}") from None
        except (URLError, TimeoutError):
            raise AIError("Could not reach Gemini. Check your internet connection and try again.") from None

    try:
        return "".join(part.get("text", "") for part in result["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError, TypeError):
        raise AIError("Gemini returned an empty response. Please try again.") from None
