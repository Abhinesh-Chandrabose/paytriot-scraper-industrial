# GOscraper - Business Intelligence Scraper

## Problem Statement
User provided an HTML file for GOscraper (a business intelligence scraper) and asked to convert it into a full-stack web app with Apify API integration for Google Search Scraper and LinkedIn Company Employees Scraper.

## Architecture
- **Frontend**: React + Tailwind CSS + Phosphor Icons
- **Backend**: FastAPI + Motor (MongoDB async) + Apify Client + Emergent LLM
- **Database**: MongoDB
- **External APIs**: Apify (Google Search Scraper, LinkedIn Employees Scraper), Anthropic Claude (via Emergent LLM key)

## User Personas
- **Lead Gen Specialist**: Uses Google Search + LinkedIn scraping to find business contacts
- **Sales Team**: Exports CSV data for outreach campaigns
- **Business Analyst**: Uses AI assistant for market intelligence queries

## Core Requirements
- [x] Google Search Scraper via Apify (`apify/google-search-scraper`)
- [x] LinkedIn Employee Scraper via Apify (`caprolok/linkedin-employees-scraper`)
- [x] AI Chat Assistant (Claude via Emergent LLM key)
- [x] CSV Export
- [x] Search History (MongoDB)
- [x] Business Records CRUD (MongoDB)
- [x] Chat History (MongoDB)
- [x] Dark Control Room UI theme

## What's Been Implemented (2026-03-31)
1. Full backend with Apify integration (sync + async endpoints with polling)
2. AI chat using Emergent LLM key with Claude Sonnet 4.5
3. Three-tab UI: Google Search, LinkedIn, AI Assistant
4. Business records stored in MongoDB with CSV export
5. Search history tracking
6. Chat history persistence

## API Endpoints
- `POST /api/search/google` - Sync Google search
- `POST /api/search/google/async` - Async Google search
- `POST /api/search/linkedin` - Sync LinkedIn scrape
- `POST /api/search/linkedin/async` - Async LinkedIn scrape
- `GET /api/task/{task_id}/status` - Poll task status
- `POST /api/chat` - AI chat
- `GET /api/chat/history/{session_id}` - Chat history
- `POST /api/businesses` - Save business
- `POST /api/businesses/bulk` - Bulk save
- `GET /api/businesses` - List businesses
- `DELETE /api/businesses` - Clear all
- `GET /api/businesses/export/csv` - CSV export
- `GET /api/search/history` - Search history

## Prioritized Backlog
### P0 (Critical) - DONE
- [x] Apify Google Search integration
- [x] Apify LinkedIn Employee integration  
- [x] AI Chat Assistant
- [x] CSV Export

### P1 (Important)
- [ ] Async polling UI (progress bar with real-time status updates)
- [ ] Search result enrichment (parse emails/phones from descriptions)
- [ ] Pagination for large result sets

### P2 (Nice to have)
- [ ] User authentication
- [ ] Saved search templates
- [ ] Batch scraping (multiple companies at once)
- [ ] Data deduplication
- [ ] Webhook notifications for completed scrapes
