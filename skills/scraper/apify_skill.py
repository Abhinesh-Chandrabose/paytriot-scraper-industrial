import os
import asyncio
from apify_client import ApifyClientAsync
from typing import List, Dict, Any, Optional

class ApifySkill:
    """
    Skill for specialized scraping tasks using Apify Actors.
    Used as Fallback for general scraping and Primary for LinkedIn/Email.
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("APIFY_API_TOKEN")
        if not self.token:
            self.enabled = False
            self.client = None
        else:
            self.enabled = True
            self.client = ApifyClientAsync(token=self.token)

    async def scrape_google(self, queries: List[str], max_pages: int = 1) -> Dict[str, Any]:
        """
        Scrapes Google Search via Apify.
        """
        if not self.enabled:
            return {"success": False, "error": "APIFY_API_TOKEN missing", "provider": "apify"}
        run_input = {
            "queries": "\n".join(queries),
            "maxPagesPerQuery": max_pages,
            "resultsPerPage": 10
        }
        actor = self.client.actor("apify/google-search-scraper")
        run = await actor.call(run_input=run_input)
        
        items = []
        async for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
        
        return {"success": True, "results": items, "provider": "apify"}

    async def scrape_linkedin(self, company_urls: List[str], max_results: int = 50) -> Dict[str, Any]:
        """
        Industrial LinkedIn employee scraping.
        """
        if not self.enabled:
            return {"success": False, "error": "APIFY_API_TOKEN missing", "provider": "apify"}
        run_input = {
            "companyUrls": company_urls,
            "maxResultsPerCompany": max_results
        }
        actor = self.client.actor("caprolok/linkedin-employees-scraper")
        run = await actor.call(run_input=run_input)
        
        items = []
        async for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
            
        return {"success": True, "employees": items, "provider": "apify"}

    async def find_emails(self, domain: str) -> Dict[str, Any]:
        """
        Finds and verifies emails for a domain.
        """
        if not self.enabled:
            return {"success": False, "error": "APIFY_API_TOKEN missing", "provider": "apify"}
        actor = self.client.actor("apify/contact-details-scraper")
        run = await actor.call(run_input={"startUrls": [{"url": f"https://{domain}"}]})
        
        items = []
        async for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
            
        return {"success": True, "contacts": items, "provider": "apify"}

    async def scrape_website(self, url: str) -> Dict[str, Any]:
        """
        Deep website scraping using Apify Website Content Crawler.
        This is a robust fallback for Firecrawl.
        """
        if not self.enabled:
            return {"success": False, "error": "APIFY_API_TOKEN missing", "provider": "apify-crawler"}
        run_input = {
            "startUrls": [{"url": url}],
            "maxRequestsPerCrawl": 5,  # Keep it focused
            "onlyMainContent": True,
        }
        actor = self.client.actor("apify/website-content-crawler")
        run = await actor.call(run_input=run_input)
        
        items = []
        async for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
            
        if not items:
            return {"success": False, "error": "No content found", "provider": "apify-crawler"}
            
        return {
            "success": True, 
            "data": items[0],  # Return the main page result
            "provider": "apify-crawler"
        }
