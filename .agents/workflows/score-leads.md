---
description: Re-run scoring on existing DB
---

1. Open `reddit-highrisk-scraper/scraper.py`.
2. This workflow assumes the scoring logic in `scraper.py` has been updated and you want to refresh the `leads` table.
// turbo
3. Run the scoring initialization (Implementation Note: This would typically be a script that iterates over `posts` and updates `leads`).
```bash
# This is a placeholder for a future optimization. 
# For now, running the scraper again handles updates.
python reddit-highrisk-scraper/scraper.py --limit 1
```
