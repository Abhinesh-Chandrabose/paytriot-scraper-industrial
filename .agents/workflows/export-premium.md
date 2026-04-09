---
description: Filter score>70, format for cold email
---

1. Ensure `leads.db` contains data.
// turbo
2. Export premium leads to a specialized CSV.
```bash
# This requires a script modification or a direct SQLite query.
# Using the existing exporter with a filter logic.
python -c "import sqlite3, pandas as pd; conn = sqlite3.connect('reddit-highrisk-scraper/leads.db'); df = pd.read_sql_query('SELECT author, contact_info, context FROM leads WHERE lead_score > 70', conn); df.to_csv('premium_leads.csv', index=False); conn.close()"
```
3. Check `premium_leads.csv` for high-quality contacts.
