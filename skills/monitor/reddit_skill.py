"""
Module 1: skills/monitor/reddit_skill.py
Streams Reddit posts across payment-related subreddits, scores matches,
and writes high-intent leads (score >= 7) to Supabase.

API keys required:
  REDDIT_CLIENT_ID     — reddit.com/prefs/apps → create app (script type)
  REDDIT_CLIENT_SECRET — same app panel
  REDDIT_USER_AGENT    — any string, e.g. "lead-monitor/1.0 by u/youruser"
  SUPABASE_URL / SUPABASE_KEY — Supabase project settings → API
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))

import praw
from supabase import create_client, Client

from skills.ai.gemini_scorer import GeminiScorer

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "stripe", "payments", "smallbusiness", "entrepreneur",
    "ecommerce", "shopify", "startups", "cryptocurrency",
]

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

RECONNECT_DELAY = 30  # seconds


class RedditSkill:
    """
    Streams Reddit submissions, keyword-matches them, scores with Gemini,
    and saves leads scoring >= 7 to Supabase.
    """

    def __init__(self):
        self.scorer = GeminiScorer()
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "lead-monitor/1.0"),
        )
        self.db: Client | None = self._init_db()

    def _init_db(self) -> Client | None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
        logger.warning("SUPABASE_URL/KEY missing — Reddit leads will NOT be saved")
        return None

    def _matches(self, text: str) -> bool:
        lower = text.lower()
        return any(kw in lower for kw in KEYWORDS)

    def _save_lead(self, submission: praw.models.Submission, result: dict):
        if not self.db:
            return
        record = {
            "source": "reddit",
            "channel": submission.subreddit.display_name,
            "score": result["score"],
            "urgency": result["urgency"],
            "pain_point": result["pain_point"],
            "snippet": (submission.title + " " + (submission.selftext or ""))[:400],
            "url": f"https://reddit.com{submission.permalink}",
            "status": "new",
        }
        try:
            self.db.table("leads").insert(record).execute()
            logger.info(
                json.dumps({
                    "event": "lead_saved",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "reddit",
                    "channel": record["channel"],
                    "score": record["score"],
                    "url": record["url"],
                })
            )
        except Exception as exc:
            logger.error(f"Supabase insert failed: {exc}")

    def run(self):
        """Blocking stream loop. Reconnects every {RECONNECT_DELAY}s on error."""
        target = "+".join(SUBREDDITS)
        while True:
            try:
                logger.info(f"Reddit stream starting — r/{target}")
                sub = self.reddit.subreddit(target)
                for submission in sub.stream.submissions(skip_existing=True):
                    text = f"{submission.title} {submission.selftext or ''}"
                    if not self._matches(text):
                        continue

                    logger.info(
                        json.dumps({
                            "event": "keyword_match",
                            "source": "reddit",
                            "channel": submission.subreddit.display_name,
                            "url": f"https://reddit.com{submission.permalink}",
                        })
                    )

                    result = self.scorer.score(text)
                    if result["score"] >= 7:
                        self._save_lead(submission, result)

            except Exception as exc:
                logger.error(
                    f"Reddit stream error: {exc!r}. Reconnecting in {RECONNECT_DELAY}s…"
                )
                time.sleep(RECONNECT_DELAY)


async def run_reddit_monitor():
    """Async entry-point: runs the blocking stream in a thread pool."""
    skill = RedditSkill()
    await asyncio.to_thread(skill.run)


# --- Standalone test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_reddit_monitor())
