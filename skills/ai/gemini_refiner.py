import os
import json
import logging
from google import genai
from openai import OpenAI
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class GeminiRefiner:
    """
    Skill for refining and cleaning scraped business data using Gemini Pro,
    with OpenRouter as a fallback.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        # Init Gemini
        if not self.api_key:
            self.enabled = False
            self.client = None
            logger.warning("GOOGLE_API_KEY missing - Gemini disabled")
        else:
            self.enabled = True
            self.client = genai.Client(api_key=self.api_key)

        # Init OpenRouter
        if self.openrouter_key:
            self.openrouter = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key,
            )
        else:
            self.openrouter = None
            logger.warning("OPENROUTER_API_KEY missing - OpenRouter fallback disabled")

    async def refine_leads(self, raw_data: str) -> Dict[str, Any]:
        """
        Refines raw text into a clean JSON list of business leads.
        """
        prompt = f"""
Analyze the following scraped data and extract a clean list of business leads.
For each lead, provide: Name, Website, Email, Phone, and LinkedIn URL.
If a website is missing but a LinkedIn URL is present, try to infer the most likely company domain.
Ignore any non-business data or noise.

Data:
{raw_data}

Return the results as a JSON list.
"""
        # Try Gemini
        if self.enabled and self.client:
            try:
                response = await self.client.aio.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt
                )
                return {"success": True, "refined_data": response.text, "provider": "gemini"}
            except Exception as e:
                logger.error(f"Gemini refinement error: {e}")

        # Fallback to OpenRouter
        if self.openrouter:
            try:
                # OpenRouter completions are synchronous in this SDK version unless using AsyncOpenAI,
                # but we'll use the sync one for simplicity or wrap in run_in_executor
                import asyncio
                response = await asyncio.to_thread(
                    self.openrouter.chat.completions.create,
                    model="google/gemini-2.0-flash-001",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"} if "JSON" in prompt else None
                )
                return {
                    "success": True, 
                    "refined_data": response.choices[0].message.content, 
                    "provider": "openrouter"
                }
            except Exception as e:
                logger.error(f"OpenRouter refinement fallback error: {e}")
                return {"success": False, "error": f"Both Gemini and OpenRouter failed. Last error: {str(e)}"}

        return {"success": False, "error": "No AI providers available (check API keys)"}

    async def chat(self, message: str) -> Dict[str, Any]:
        """
        General-purpose chat method using Gemini 1.5 Pro / Flash.
        """
        # Try Gemini
        if self.enabled and self.client:
            try:
                response = await self.client.aio.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=message
                )
                return {"success": True, "response": response.text, "provider": "gemini"}
            except Exception as e:
                logger.error(f"Gemini chat error: {e}")

        # Fallback to OpenRouter
        if self.openrouter:
            try:
                import asyncio
                response = await asyncio.to_thread(
                    self.openrouter.chat.completions.create,
                    model="google/gemini-2.0-flash-001",
                    messages=[{"role": "user", "content": message}]
                )
                return {
                    "success": True, 
                    "response": response.choices[0].message.content, 
                    "provider": "openrouter"
                }
            except Exception as e:
                logger.error(f"OpenRouter chat fallback error: {e}")
                return {"success": False, "error": f"Chat failed on both providers. Last error: {str(e)}"}

        return {"success": False, "error": "AI providers unavailable"}
