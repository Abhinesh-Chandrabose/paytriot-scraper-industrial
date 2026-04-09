"""
Module 1: skills/monitor/reddit_skill.py
Streams Reddit posts via RSS (no API credentials required),
scores matches with Gemini, extracts contact info, and writes high-intent leads to Supabase.

API keys required:
  SUPABASE_URL / SUPABASE_KEY — Supabase project settings → API
  GEMINI_API_KEY or OPENROUTER_API_KEY — for AI scoring
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import feedparser
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))

from supabase import create_client, Client
from skills.ai.gemini_scorer import GeminiScorer

logger = logging.getLogger(__name__)

# Payment/processor focused subreddits
PAYMENT_SUBREDDITS = [
    "stripe", "payments", "smallbusiness", "entrepreneur",
    "ecommerce", "shopify", "startups", "cryptocurrency",
]

# High-risk investment focused subreddits
HIGH_RISK_SUBREDDITS = [
    "highriskinvestments",
    "pennystock",
    "wallstreetbets",
    "options",
    "bitcoinmarkets",
]

# Payment processor keywords
PAYMENT_KEYWORDS = [
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

# High-risk investment / startup keywords
HIGH_RISK_KEYWORDS = [
    "startup",
    "funding",
    "VC",
    "investment",
    "crypto",
    "penny stock",
    "high risk",
    "moonshot",
]

# Lead intent keywords
LEAD_INTENT_KEYWORDS = [
    "DM me",
    "email",
    "invest",
    "partner",
    "business",
    "contact",
]

POLL_INTERVAL = 60  # seconds between RSS polls
SEEN_IDS_MAX = 1000  # max post IDs to keep in memory


class RedditSkill:
    """
    Polls Reddit RSS feeds (no API credentials required),
    keyword-matches posts, scores with Gemini, extracts contact info,
    and saves high-intent leads to Supabase.
    """

    def __init__(self):
        self.scorer = GeminiScorer()
        self.db: Client | None = self._init_db()
        self.seen_ids: set = set()

        # Regex patterns for contact extraction
        self.email_regex = re.compile(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+")
        self.domain_regex = re.compile(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)")
        self.phone_regex = re.compile(r"(\+\d{1,3}\s?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}")

    def _init_db(self) -> Client | None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
        logger.warning("SUPABASE_URL/KEY missing — Reddit leads will NOT be saved")
        return None

    def _matches(self, text: str) -> bool:
        lower = text.lower()
        return any(kw in lower for kw in PAYMENT_KEYWORDS) or \
               any(kw in lower for kw in HIGH_RISK_KEYWORDS)

    def _extract_contact_info(self, text: str) -> str:
        """Extract emails, domains, and phone numbers from text."""
        emails = self.email_regex.findall(text.lower())
        domains = self.domain_regex.findall(text.lower())
        phones = self.phone_regex.findall(text)

        contacts = []
        if emails:
            contacts.extend(emails)
        if domains:
            contacts.extend([d for d in domains if d not in ["reddit.com", "imgur.com", "v.redd.it"]])
        if phones:
            contacts.extend([p if isinstance(p, str) else "".join(p) for p in phones])

        return ", ".join(list(set(contacts)))

    def _calculate_lead_score(self, text: str, score: int = 0) -> int:
        """Calculate lead score based on keywords."""
        text_lower = text.lower()

        # High-risk signal keywords (10 points each)
        for kw in HIGH_RISK_KEYWORDS:
            if kw.lower() in text_lower:
                score += 10

        # Lead intent keywords (15 points each)
        for kw in LEAD_INTENT_KEYWORDS:
            if kw.lower() in text_lower:
                score += 15

        return min(100, score)

    def _save_lead(self, post: Dict[str, Any], result: dict, contact_info: str = ""):
        if not self.db:
            return

        text = post.get("title", "") + " " + post.get("summary", "")
        lead_score = self._calculate_lead_score(text)

        record = {
            "source": "reddit",
            "channel": post.get("subreddit", "unknown"),
            "score": result["score"],
            "lead_score": lead_score,
            "urgency": result["urgency"],
            "pain_point": result["pain_point"],
            "contact_info": contact_info,
            "snippet": text[:400],
            "url": post.get("link", ""),
            "author": post.get("author", "unknown"),
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
                    "lead_score": record["lead_score"],
                    "url": record["url"],
                })
            )
        except Exception as exc:
            logger.error(f"Supabase insert failed: {exc}")

    def _fetch_subreddit_posts(self, subreddit: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch posts from a subreddit via RSS feed."""
        # Reddit RSS feed URL (no auth required)
        rss_url = f"https://www.reddit.com/r/{subreddit}/new.rss?limit={limit}"

        try:
            feed = feedparser.parse(rss_url)
            posts = []

            for entry in feed.entries:
                # Extract post ID from link
                post_id = entry.link.split("/")[4] if "/comments/" in entry.link else entry.link

                # Skip already seen posts
                if post_id in self.seen_ids:
                    continue

                post = {
                    "id": post_id,
                    "title": entry.title,
                    "summary": entry.get("summary", ""),
                    "link": entry.link,
                    "author": entry.get("author", "unknown"),
                    "published": entry.get("published", ""),
                    "subreddit": subreddit,
                }
                posts.append(post)
                self.seen_ids.add(post_id)

                # Trim seen_ids if too large
                if len(self.seen_ids) > SEEN_IDS_MAX:
                    self.seen_ids = set(list(self.seen_ids)[-SEEN_IDS_MAX//2:])

            return posts

        except Exception as e:
            logger.error(f"Error fetching RSS for r/{subreddit}: {e}")
            return []

    def _process_posts(self, posts: List[Dict[str, Any]]):
        """Process a list of posts, checking for leads."""
        for post in posts:
            text = f"{post['title']} {post['summary']}"

            if not self._matches(text):
                continue

            logger.info(
                json.dumps({
                    "event": "keyword_match",
                    "source": "reddit",
                    "channel": post["subreddit"],
                    "url": post["link"],
                })
            )

            result = self.scorer.score(text)
            contact_info = self._extract_contact_info(text)

            # Save if high AI score, high keyword score, or has contact info
            if result["score"] >= 7 or self._calculate_lead_score(text) >= 50 or contact_info:
                self._save_lead(post, result, contact_info)

    def run(self):
        """Polling loop for RSS feeds."""
        all_subreddits = PAYMENT_SUBREDDITS + HIGH_RISK_SUBREDDITS
        logger.info(f"Reddit RSS monitor starting — polling r/{'+r/'.join(all_subreddits)} every {POLL_INTERVAL}s")

        while True:
            try:
                for subreddit in all_subreddits:
                    posts = self._fetch_subreddit_posts(subreddit)
                    if posts:
                        self._process_posts(posts)

                time.sleep(POLL_INTERVAL)

            except Exception as exc:
                logger.error(f"Reddit RSS monitor error: {exc!r}. Retrying in {POLL_INTERVAL}s...")
                time.sleep(POLL_INTERVAL)


async def run_reddit_monitor():
    """Async entry-point: runs the blocking monitor in a thread pool."""
    skill = RedditSkill()
    await asyncio.to_thread(skill.run)


# --- Standalone test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_reddit_monitor())
