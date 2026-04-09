---
description: Scrape last 24h posts only
---

1. Ensure the environment is active and credentials are set in `config.yaml`.
// turbo
2. Run the scraper with the daily time filter.
```bash
python reddit-highrisk-scraper/scraper.py --time day --limit 50
```
3. Open `reddit-highrisk-scraper/leads_dashboard.html` to view the new leads.
