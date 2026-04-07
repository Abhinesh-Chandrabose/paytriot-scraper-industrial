"""
Module 2: skills/monitor/telegram_skill.py
Listens to public Telegram channels for payment-problem posts, scores them,
and writes high-intent leads (score >= 7) to Supabase.

API keys required:
  TELEGRAM_API_ID    — my.telegram.org → "API development tools" → App api_id
  TELEGRAM_API_HASH  — same page → App api_hash
  TELEGRAM_CHANNELS  — comma-separated channel usernames, e.g. "@paymentstech,@stripehelp"
  SUPABASE_URL / SUPABASE_KEY — Supabase project settings → API

Session file: telegram_session.session (in project root, git-ignored)
First run will prompt for your phone number to authorise the session.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))

from telethon import TelegramClient, events
from supabase import create_client, Client

from skills.ai.gemini_scorer import GeminiScorer

logger = logging.getLogger(__name__)

SESSION_FILE = str(ROOT_DIR / "telegram_session")

KEYWORDS = [
    "stripe banned",
    "stripe account closed",
    "stripe terminated",
    "payment processor dropped",
    "frozen funds",
    "need payment gateway",
    "high risk merchant",
    "payment processing alternative",
    "fiat onramp",
    "crypto payment",
    "offshore merchant account",
    "processor shut down",
    "payment account suspended",
]


class TelegramSkill:
    """
    Monitors public Telegram channels for payment-related distress signals.
    """

    def __init__(self):
        self.scorer = GeminiScorer()
        api_id_raw = os.getenv("TELEGRAM_API_ID", "0")
        api_hash = os.getenv("TELEGRAM_API_HASH", "")
        channels_raw = os.getenv("TELEGRAM_CHANNELS", "")
        self.channels = [c.strip() for c in channels_raw.split(",") if c.strip()]

        if not api_id_raw.isdigit() or not api_hash:
            logger.warning("TELEGRAM_API_ID/HASH not set — Telegram monitor will be a no-op")

        self.client = TelegramClient(SESSION_FILE, int(api_id_raw or 0), api_hash)
        self.db: Client | None = self._init_db()

    def _init_db(self) -> Client | None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
        logger.warning("SUPABASE_URL/KEY missing — Telegram leads will NOT be saved")
        return None

    def _matches(self, text: str) -> bool:
        lower = text.lower()
        return any(kw in lower for kw in KEYWORDS)

    async def _save_lead(self, text: str, channel_name: str, result: dict, url: str):
        if not self.db:
            return
        record = {
            "source": "telegram",
            "channel": channel_name,
            "score": result["score"],
            "urgency": result["urgency"],
            "pain_point": result["pain_point"],
            "snippet": text[:400],
            "url": url,
            "status": "new",
        }
        try:
            self.db.table("leads").insert(record).execute()
            logger.info(
                json.dumps({
                    "event": "lead_saved",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "telegram",
                    "channel": channel_name,
                    "score": result["score"],
                    "url": url,
                })
            )
        except Exception as exc:
            logger.error(f"Supabase insert failed: {exc}")

    async def run(self):
        """Async main loop: connects, resolves channels, listens for messages."""
        if not self.channels:
            logger.error("TELEGRAM_CHANNELS is empty — Telegram monitor disabled")
            return

        await self.client.start()

        # Resolve channels — skip those that fail
        resolved = []
        for ch in self.channels:
            try:
                entity = await self.client.get_entity(ch)
                resolved.append(entity)
                logger.info(f"Resolved Telegram channel: {ch}")
            except Exception as exc:
                logger.warning(f"Cannot resolve Telegram channel '{ch}': {exc}")

        if not resolved:
            logger.error("No Telegram channels resolved — monitor disabled")
            await self.client.disconnect()
            return

        @self.client.on(events.NewMessage(chats=resolved))
        async def handler(event):
            text = event.message.text or ""
            if not text or not self._matches(text):
                return

            chat = event.chat
            channel_name = getattr(chat, "username", None) or str(event.chat_id)
            msg_id = event.message.id
            url = (
                f"https://t.me/{channel_name}/{msg_id}"
                if channel_name
                else f"https://t.me/c/{abs(event.chat_id)}/{msg_id}"
            )

            logger.info(
                json.dumps({
                    "event": "keyword_match",
                    "source": "telegram",
                    "channel": channel_name,
                    "url": url,
                })
            )

            # Run blocking scorer in thread to avoid stalling the event loop
            result = await asyncio.to_thread(self.scorer.score, text)

            if result["score"] >= 7:
                await self._save_lead(text, channel_name, result, url)

        logger.info(f"Telegram monitor active on {len(resolved)} channel(s)")
        await self.client.run_until_disconnected()


async def run_telegram_monitor():
    """Async entry-point for FastAPI background task."""
    skill = TelegramSkill()
    await skill.run()


# --- Standalone test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_telegram_monitor())
