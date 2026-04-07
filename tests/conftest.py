"""
Test configuration: patches all external services so tests run without real API keys.
"""
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Path setup (mirrors what main.py does at runtime) ─────────────────────────
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))

# ── Inject fake env vars BEFORE any app module is imported ────────────────────
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock_supabase_key")
os.environ.setdefault("FIRECRAWL_API_KEY", "mock_firecrawl_key")
os.environ.setdefault("APIFY_API_TOKEN", "mock_apify_token")
os.environ.setdefault("GOOGLE_API_KEY", "mock_google_key")
os.environ.setdefault("CLAUDE_API_KEY", "mock_claude_key")
os.environ.setdefault("REDDIT_CLIENT_ID", "mock_reddit_id")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "mock_reddit_secret")
os.environ.setdefault("REDDIT_USER_AGENT", "test-agent/1.0")
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "mock_telegram_hash")
os.environ.setdefault("GEMINI_API_KEY", "mock_gemini_key")

# ── Stub out packages that are NOT installed in the test venv ─────────────────
# praw and telethon are only used by monitor skills which we replace with no-ops.
# We must inject them into sys.modules BEFORE importing apps.api.main, because
# main.py imports the monitor skill modules which in turn import praw/telethon.

def _stub_module(name: str):
    """Register a MagicMock under `name` and all sub-names in sys.modules."""
    if name not in sys.modules:
        sys.modules[name] = MagicMock()


for _mod in [
    "praw", "praw.models",
    "telethon", "telethon.events",
    "openai",  # used in gemini_scorer fallback, not installed in test venv
]:
    _stub_module(_mod)


# ─────────────────────────────────────────────────────────────────────────────

def _make_mock_db():
    """Build a MagicMock that handles Supabase's fluent query API."""
    db = MagicMock()
    tbl = db.table.return_value

    # SELECT chain: .select().order().limit().execute()
    sel = tbl.select.return_value
    sel.order.return_value.limit.return_value.execute.return_value.data = []
    sel.limit.return_value.execute.return_value.data = []
    sel.execute.return_value.data = []

    # SELECT with filters (.eq / .gte chained after .order().limit())
    sel.eq.return_value.execute.return_value.data = []
    sel.gte.return_value.execute.return_value.data = []
    sel.order.return_value.limit.return_value.eq.return_value.execute.return_value.data = []
    sel.order.return_value.limit.return_value.gte.return_value.execute.return_value.data = []

    # INSERT chain
    tbl.insert.return_value.execute.return_value.data = [{"id": "mock-id-123"}]

    # UPDATE chain
    tbl.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "mock-id-123", "status": "contacted"}
    ]

    return db


def _make_mock_firecrawl_skill():
    skill = AsyncMock()
    skill.scrape.return_value = {
        "success": True,
        "data": {"markdown": "# Test Page\nSome content."},
        "provider": "firecrawl",
    }
    skill.crawl.return_value = {
        "success": True,
        "job_id": "crawl-job-abc",
        "provider": "firecrawl",
    }
    return skill


def _make_mock_apify_skill():
    skill = AsyncMock()
    skill.scrape_google.return_value = {
        "success": True,
        "results": [{"title": "Test Result", "url": "https://example.com"}],
        "provider": "apify",
    }
    skill.scrape_linkedin.return_value = {
        "success": True,
        "employees": [{"name": "Jane Doe", "title": "CEO"}],
        "provider": "apify",
    }
    skill.find_emails.return_value = {
        "success": True,
        "contacts": [{"email": "contact@example.com"}],
        "provider": "apify",
    }
    return skill


def _make_mock_gemini_skill():
    skill = AsyncMock()
    skill.refine_leads.return_value = {
        "success": True,
        "refined_data": '[{"name": "Acme Corp", "website": "https://acme.com"}]',
        "provider": "gemini",
    }
    return skill


def _make_mock_claude_skill():
    skill = AsyncMock()
    skill.finalize_list.return_value = {
        "success": True,
        "final_data": "Polished lead list.",
        "provider": "claude",
    }
    return skill


@pytest.fixture(scope="session")
def client():
    """
    Session-scoped TestClient with all external services mocked.

    Patches applied (in dependency order):
      - supabase.create_client       → returns mock db
      - FirecrawlApp                 → mock (prevents real HTTP)
      - ApifyClientAsync             → mock (prevents real HTTP)
      - google.generativeai          → mock (prevents real HTTP)
      - anthropic.AsyncAnthropic     → mock (prevents real HTTP)
    praw and telethon are already stubbed in sys.modules above.
    FastAPI dependency overrides replace the actual Skill objects injected
    into route handlers.
    """
    mock_db = _make_mock_db()

    async def noop_reddit():
        """No-op replacement for run_reddit_monitor."""
        return

    async def noop_telegram():
        """No-op replacement for run_telegram_monitor."""
        return

    with (
        patch("supabase.create_client", return_value=mock_db),
        patch("skills.scraper.firecrawl_skill.FirecrawlApp"),
        patch("skills.scraper.apify_skill.ApifyClientAsync"),
        patch("google.generativeai.configure"),
        patch("google.generativeai.GenerativeModel"),
        patch("anthropic.AsyncAnthropic"),
    ):
        # Import after patches so module-level code (db = create_client(...))
        # uses the mock.
        import apps.api.main as main_module

        # Replace the background-task entry-points so the lifespan doesn't
        # try to open real Reddit/Telegram connections.
        main_module.run_reddit_monitor = noop_reddit
        main_module.run_telegram_monitor = noop_telegram

        from apps.api.main import app, get_apify, get_claude, get_firecrawl, get_gemini

        # Wire mock skills into FastAPI's dependency injection
        app.dependency_overrides[get_firecrawl] = lambda: _make_mock_firecrawl_skill()
        app.dependency_overrides[get_apify] = lambda: _make_mock_apify_skill()
        app.dependency_overrides[get_gemini] = lambda: _make_mock_gemini_skill()
        app.dependency_overrides[get_claude] = lambda: _make_mock_claude_skill()

        from fastapi.testclient import TestClient

        with TestClient(app) as test_client:
            yield test_client

        app.dependency_overrides.clear()
