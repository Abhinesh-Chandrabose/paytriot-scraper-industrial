import os
import json
import logging
import sys
from pathlib import Path

# Add project roots to path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))

from google import genai
from openai import OpenAI
from services.security import SecurityGuard

logger = logging.getLogger(__name__)

SCORING_PROMPT = (
    "You are a lead scoring assistant for a payment gateway business.\n"
    "Score the following post for purchase intent from 1 to 10.\n"
    "Return ONLY valid JSON in this exact format, no other text:\n"
    '{"score": <int>, "urgency": "<string>", "pain_point": "<string>"}'
)

class GeminiScorer:
    def __init__(self):
        self.security = SecurityGuard()
        self._init_gemini()
        self._init_openrouter()

    def _init_gemini(self):
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if key:
            # Modern SDK uses the Client object
            self.client = genai.Client(api_key=key)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY not set — Gemini scorer disabled")

    def _init_openrouter(self):
        key = os.getenv("OPENROUTER_API_KEY")
        if key:
            self.openrouter = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=key,
            )
        else:
            self.openrouter = None
            logger.warning("OPENROUTER_API_KEY not set — OpenRouter fallback disabled")

    def score(self, raw_text: str) -> dict:
        clean_text = self.security.sanitize_scraped_text(raw_text)
        safe_prompt = self.security.create_safe_prompt(SCORING_PROMPT, clean_text[:2000])

        if self.client:
            try:
                # Using the synchronous generation method
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=safe_prompt
                )
                result = self._parse_json(response.text)
                if result:
                    return result
            except Exception as exc:
                logger.error(f"Gemini error: {exc}")

        # Fallback to OpenRouter if Gemini fails or is not configured
        if self.openrouter:
            try:
                response = self.openrouter.chat.completions.create(
                    model="google/gemini-2.0-flash-001",
                    messages=[
                        {"role": "system", "content": SCORING_PROMPT},
                        {"role": "user", "content": clean_text[:2000]}
                    ],
                    response_format={"type": "json_object"}
                )
                result = self._parse_json(response.choices[0].message.content)
                if result:
                    return result
            except Exception as exc:
                logger.error(f"OpenRouter error: {exc}")

        return {"score": 0, "urgency": "low", "pain_point": "error"}

    def _parse_json(self, text: str) -> dict | None:
        try:
            return json.loads(text.strip())
        except:
            return None
