"""
GOscraper Industrial API v3.0
Modules 4 + 6: FastAPI backend with lead-monitor background tasks,
/leads + /stats endpoints, and structured JSON logging.
"""

# ── Standard library ────────────────────────────────────────────────────────
import asyncio
import csv
import io
import json
import logging
import logging.handlers
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── FastAPI / Pydantic ──────────────────────────────────────────────────────
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from starlette.middleware.cors import CORSMiddleware

# ── Database ────────────────────────────────────────────────────────────────
from supabase import create_client, Client

# ── Path resolution (must happen before local imports) ──────────────────────
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))

# ── Local skills ─────────────────────────────────────────────────────────────
from services.security import SecurityGuard
from skills.scraper.firecrawl_skill import FirecrawlSkill
from skills.scraper.apify_skill import ApifySkill
from skills.ai.gemini_refiner import GeminiRefiner
from skills.ai.claude_finalizer import ClaudeFinalizer
from skills.monitor.reddit_skill import run_reddit_monitor
from skills.monitor.telegram_skill import run_telegram_monitor

# ── Load env (Bun/dotenv auto-loads; this covers plain Python runs) ──────────
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

# ═══════════════════════════════════════════════════════════════════════════
# Module 6 — Structured JSON Logging
# ═══════════════════════════════════════════════════════════════════════════

class _JSONFormatter(logging.Formatter):
    """Emit every log record as a compact JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _setup_logging() -> logging.Logger:
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.handlers.clear()

    fmt = _JSONFormatter()

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    log.addHandler(ch)

    # Rotating file handler — leads.log (5 MB × 3 backups)
    log_path = ROOT_DIR / "leads.log"
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    log.addHandler(fh)

    return logging.getLogger(__name__)


logger = _setup_logging()

# ═══════════════════════════════════════════════════════════════════════════
# Supabase client
# ═══════════════════════════════════════════════════════════════════════════

_supabase_url = os.getenv("SUPABASE_URL")
_supabase_key = os.getenv("SUPABASE_KEY")

if not _supabase_url or not _supabase_key:
    logger.warning("SUPABASE_URL or SUPABASE_KEY missing — database features disabled")
    db: Optional[Client] = None
else:
    db: Client = create_client(_supabase_url, _supabase_key)

# ═══════════════════════════════════════════════════════════════════════════
# Background task lifecycle
# ═══════════════════════════════════════════════════════════════════════════

_bg_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Reddit + Telegram monitors on startup; cancel on shutdown."""
    logger.info("Starting lead-monitor background tasks")

    _bg_tasks.append(asyncio.create_task(run_reddit_monitor(), name="reddit_monitor"))
    _bg_tasks.append(asyncio.create_task(run_telegram_monitor(), name="telegram_monitor"))

    yield  # app is running

    logger.info("Shutting down lead-monitor background tasks")
    for task in _bg_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _bg_tasks.clear()


# ═══════════════════════════════════════════════════════════════════════════
# FastAPI app
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(title="GOscraper Industrial API", version="3.0", lifespan=lifespan)

# Add CORS middleware early
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")


# ── Dependency factories ─────────────────────────────────────────────────────
def get_firecrawl():  return FirecrawlSkill()
def get_apify():      return ApifySkill()
def get_gemini():     return GeminiRefiner()
def get_claude():     return ClaudeFinalizer()


# ═══════════════════════════════════════════════════════════════════════════
# Pydantic models
# ═══════════════════════════════════════════════════════════════════════════

class ScrapeRequest(BaseModel):
    url: str
    use_fallback: bool = True


class LeadRefineRequest(BaseModel):
    raw_text: str
    session_id: str


class BusinessRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    website: Optional[str] = None
    emails: List[str] = []
    phones: List[str] = []
    linkedin: Optional[str] = None
    source: str = "manual"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class LeadStatusPatch(BaseModel):
    status: str  # new | contacted | closed


# ═══════════════════════════════════════════════════════════════════════════
# Existing routes (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

@api_router.post("/scrape")
async def industrial_scrape(
    req: ScrapeRequest,
    firecrawl: FirecrawlSkill = Depends(get_firecrawl),
    apify: ApifySkill = Depends(get_apify),
):
    logger.info(f"Starting scrape for {req.url}")
    result = await firecrawl.scrape(req.url)
    if not result["success"] and req.use_fallback:
        logger.warning(f"Firecrawl failed, falling back to Apify for {req.url}")
        result = await apify.scrape_google([req.url])
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "All scrapers failed"))
    return result


@api_router.post("/refine")
async def refine_leads(
    req: LeadRefineRequest,
    gemini: GeminiRefiner = Depends(get_gemini),
    security: SecurityGuard = Depends(SecurityGuard),
):
    clean_text = security.sanitize_scraped_text(req.raw_text)
    if security.detect_injection(clean_text):
        raise HTTPException(status_code=400, detail="Potential prompt injection detected.")
    result = await gemini.refine_leads(clean_text)
    if db:
        try:
            db.table("refinement_history").insert({
                "session_id": req.session_id,
                "raw_length": len(req.raw_text),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as exc:
            logger.error(f"Failed to log history to Supabase: {exc}")
    return result


@api_router.get("/businesses")
async def get_businesses():
    if not db:
        return {"businesses": [], "error": "Database not configured"}
    response = db.table("businesses").select("*").order("created_at", desc=True).limit(500).execute()
    return {"businesses": response.data}


@api_router.post("/businesses/bulk")
async def bulk_save(records: List[BusinessRecord]):
    if not db:
        return {"success": False, "error": "Database not configured"}
    docs = [r.model_dump() for r in records]
    if docs:
        db.table("businesses").insert(docs).execute()
    return {"success": True, "count": len(docs)}


@api_router.get("/export/csv")
async def export_csv():
    if not db:
        return {"error": "Database not configured"}
    response = db.table("businesses").select("*").limit(1000).execute()
    businesses = response.data
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Website", "Emails", "Phones", "LinkedIn", "Source"])
    for b in businesses:
        writer.writerow([
            b.get("name", ""),
            b.get("website", ""),
            "; ".join(b.get("emails", [])),
            "; ".join(b.get("phones", [])),
            b.get("linkedin", ""),
            b.get("source", ""),
        ])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=goscraper_leads.csv"},
    )


# ── Legacy aliases ────────────────────────────────────────────────────────────

@api_router.post("/chat")
async def legacy_chat(req: Dict[str, Any], gemini: GeminiRefiner = Depends(get_gemini)):
    # Switch to Gemini for the chat assistant
    msg = req.get("message", "")
    result = await gemini.chat(msg)
    
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}
        
    return {"success": True, "response": result.get("response", "")}


@api_router.post("/search/google")
async def legacy_search_google(req: Dict[str, Any], apify: ApifySkill = Depends(get_apify)):
    return await apify.scrape_google(req.get("queries", []), req.get("max_pages", 1))


@api_router.post("/search/linkedin")
async def legacy_search_linkedin(req: Dict[str, Any], apify: ApifySkill = Depends(get_apify)):
    return await apify.scrape_linkedin(req.get("company_urls", []), req.get("max_results", 50))


@api_router.get("/health")
async def health():
    return {"status": "ok", "version": "3.0", "industrial": True}


# ═══════════════════════════════════════════════════════════════════════════
# Module 4 — New Leads Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@api_router.get("/leads")
async def get_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[int] = None,
):
    """
    Return all leads.
    Optional query params: ?status=new&source=reddit&min_score=7
    """
    if not db:
        return {"leads": [], "error": "Database not configured"}

    query = db.table("leads").select("*").order("created_at", desc=True).limit(500)

    if status:
        query = query.eq("status", status)
    if source:
        query = query.eq("source", source)
    if min_score is not None:
        query = query.gte("score", min_score)

    response = query.execute()
    return {"leads": response.data, "count": len(response.data)}


@api_router.patch("/leads/{lead_id}")
async def update_lead_status(lead_id: str, patch: LeadStatusPatch):
    """Update the status field of a single lead (new | contacted | closed)."""
    allowed = {"new", "contacted", "closed"}
    if patch.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(allowed))}",
        )
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    response = (
        db.table("leads")
        .update({"status": patch.status})
        .eq("id", lead_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    return {"success": True, "lead": response.data[0]}


@api_router.get("/stats")
async def get_stats():
    """
    Aggregate lead statistics.
    Returns: total_leads, by_source, by_score_band, leads_today
    """
    if not db:
        return {
            "total_leads": 0,
            "by_source": {"reddit": 0, "telegram": 0},
            "by_score_band": {"high": 0, "medium": 0, "low": 0},
            "leads_today": 0,
            "error": "Database not configured",
        }

    all_leads = db.table("leads").select("source,score,created_at").execute().data

    today_str = date.today().isoformat()

    by_source: Dict[str, int] = {"reddit": 0, "telegram": 0}
    by_score_band: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    leads_today = 0

    for lead in all_leads:
        src = lead.get("source", "")
        if src in by_source:
            by_source[src] += 1

        score = lead.get("score", 0) or 0
        if score >= 8:
            by_score_band["high"] += 1
        elif score >= 5:
            by_score_band["medium"] += 1
        else:
            by_score_band["low"] += 1

        created = lead.get("created_at", "")
        if created and created[:10] == today_str:
            leads_today += 1

    return {
        "total_leads": len(all_leads),
        "by_source": by_source,
        "by_score_band": by_score_band,
        "leads_today": leads_today,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Router + middleware
# ═══════════════════════════════════════════════════════════════════════════

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
