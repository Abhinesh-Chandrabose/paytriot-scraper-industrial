import os
import asyncio
from firecrawl import FirecrawlApp
from typing import Dict, Any, Optional

class FirecrawlSkill:
    """
    Skill for high-performance web scraping and crawling using Firecrawl.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            self.enabled = False
            self.app = None
        else:
            self.enabled = True
            self.app = FirecrawlApp(api_key=self.api_key)

    async def scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrapes a single URL and returns structured markdown/json.
        """
        if not self.enabled:
            return {
                "success": False, 
                "error": "FIRECRAWL_API_KEY missing. Please add it to your .env file.", 
                "provider": "firecrawl"
            }
        try:
            # Note: Firecrawl library is synchronous in some versions, 
            # using run_in_executor if needed, but modern versions support async
            response = await asyncio.to_thread(self.app.scrape_url, url, {
                'formats': ['markdown', 'html'],
                'onlyMainContent': True
            })
            return {
                "success": True,
                "data": response,
                "provider": "firecrawl"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "firecrawl"
            }

    async def extract(self, url: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Uses Firecrawl's LLM-based extraction to get structured data from a URL.
        """
        if not self.enabled:
            return {"success": False, "error": "FIRECRAWL_API_KEY missing"}
        
        try:
            response = await asyncio.to_thread(self.app.scrape_url, url, {
                'formats': ['extract'],
                'extract': {
                    'schema': schema
                }
            })
            return {
                "success": True,
                "data": response.get("extract", {}),
                "provider": "firecrawl"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def crawl(self, url: str, limit: int = 10) -> Dict[str, Any]:
        """
        Crawls a domain starting from a URL.
        """
        if not self.enabled:
            return {
                "success": False, 
                "error": "FIRECRAWL_API_KEY missing. Please add it to your .env file.", 
                "provider": "firecrawl"
            }
        try:
            crawl_result = await asyncio.to_thread(self.app.crawl_url, url, {
                'limit': limit,
                'scrapeOptions': {'formats': ['markdown']}
            })
            return {
                "success": True,
                "job_id": crawl_result.get("job_id"),
                "provider": "firecrawl"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "firecrawl"
            }
