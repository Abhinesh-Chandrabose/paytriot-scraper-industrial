import praw
import pandas as pd
import sqlite3
import yaml
import time
import random
import re
import argparse
import sys
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

class RedditLeadScraper:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Use environment variables for credentials, fallback to config
        self.client_id = os.getenv("REDDIT_CLIENT_ID") or self.config["reddit"]["client_id"]
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET") or self.config["reddit"]["client_secret"]
        self.user_agent = os.getenv("REDDIT_USER_AGENT") or self.config["reddit"]["user_agent"]

        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent
        )
        self.db_name = self.config["settings"].get("db_name", "leads.db")
        self.csv_name = self.config["settings"].get("csv_name", "highrisk_leads.csv")
        self.setup_db()
        
        # Regex patterns
        self.email_regex = re.compile(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+")
        self.domain_regex = re.compile(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)")
        self.phone_regex = re.compile(r"(\+\d{1,3}\s?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}")

    def setup_db(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            subreddit TEXT,
            title TEXT,
            selftext TEXT,
            url TEXT,
            score INTEGER,
            num_comments INTEGER,
            created_utc REAL,
            author TEXT,
            lead_score INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            post_id TEXT,
            author TEXT,
            body TEXT,
            score INTEGER,
            created_utc REAL,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT,
            source_id TEXT,
            author TEXT,
            lead_score INTEGER,
            contact_info TEXT,
            context TEXT
        )""")
        conn.commit()
        conn.close()

    def calculate_lead_score(self, post_or_comment, is_post=True):
        score = 0
        text = (post_or_comment.title + " " + post_or_comment.selftext).lower() if is_post else post_or_comment.body.lower()
        
        # High-risk signal keywords (10 points each)
        for kw in self.config["keywords"]["high_risk"]:
            if kw.lower() in text:
                score += 10
        
        # Lead intent keywords (15 points each)
        for kw in self.config["keywords"]["lead_intent"]:
            if kw.lower() in text:
                score += 15
        
        # Freshness (last 30 days)
        created_at = datetime.fromtimestamp(post_or_comment.created_utc)
        if datetime.now() - created_at < timedelta(days=30):
            score += 20
        
        # Engagement
        if is_post:
            if post_or_comment.score > 100: score += 10
        else:
            if post_or_comment.score > 10: score += 10
            
        return min(100, score)

    def extract_contact_info(self, text):
        emails = self.email_regex.findall(text.lower())
        domains = self.domain_regex.findall(text.lower())
        phones = self.phone_regex.findall(text)
        
        contacts = []
        if emails: contacts.extend(emails)
        if domains: contacts.extend([d for d in domains if d not in ["reddit.com", "imgur.com", "v.redd.it"]])
        if phones: contacts.extend([p if isinstance(p, str) else "".join(p) for p in phones])
        
        return ", ".join(list(set(contacts)))

    def stealth_delay(self):
        jitter = random.uniform(*self.config["settings"]["random_jitter"])
        time.sleep(jitter)

    def scrape_subreddit(self, subreddit_name, limit=100, time_filter="all"):
        print(f"[*] Scraping {subreddit_name} (Top {limit}, {time_filter})...")
        subreddit = self.reddit.subreddit(subreddit_name)
        
        try:
            posts = subreddit.top(limit=limit, time_filter=time_filter)
            
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            
            for post in posts:
                lead_score = self.calculate_lead_score(post)
                
                # Insert post
                c.execute("INSERT OR REPLACE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?)", (
                    post.id, subreddit_name, post.title, post.selftext, post.url, 
                    post.score, post.num_comments, post.created_utc, str(post.author), lead_score
                ))
                
                # Comment Mining
                if lead_score > 30 or post.num_comments > 50:
                    post.comments.replace_more(limit=0)
                    for comment in post.comments.list():
                        if comment.score > 10:
                            c.execute("INSERT OR REPLACE INTO comments VALUES (?,?,?,?,?,?)", (
                                comment.id, post.id, str(comment.author), comment.body, 
                                comment.score, comment.created_utc
                            ))
                            
                            # Check for lead intent in comment
                            contact_info = self.extract_contact_info(comment.body)
                            if contact_info or any(kw in comment.body.lower() for kw in self.config["keywords"]["lead_intent"]):
                                comment_score = self.calculate_lead_score(comment, is_post=False)
                                c.execute("INSERT INTO leads (source_type, source_id, author, lead_score, contact_info, context) VALUES (?,?,?,?,?,?)", (
                                    "comment", comment.id, str(comment.author), comment_score, contact_info, comment.body[:200]
                                ))
                
                # Check for lead in post
                contact_info = self.extract_contact_info(post.selftext)
                if contact_info or lead_score > 60:
                   c.execute("INSERT INTO leads (source_type, source_id, author, lead_score, contact_info, context) VALUES (?,?,?,?,?,?)", (
                        "post", post.id, str(post.author), lead_score, contact_info, post.title
                    ))
                
                conn.commit()
                self.stealth_delay()
                
            conn.close()
        except Exception as e:
            print(f"[!] Error scraping {subreddit_name}: {e}")

    def export_csv(self, min_score=0):
        print(f"[*] Exporting leads with score > {min_score} to {self.csv_name}...")
        conn = sqlite3.connect(self.db_name)
        
        query = """
        SELECT posts.subreddit, posts.title as post_title, leads.author, leads.lead_score, 
               leads.contact_info, posts.url as post_url
        FROM leads 
        JOIN posts ON leads.source_id = posts.id OR SUBSTR(leads.source_id, 0, INSTR(leads.source_id, '_')) = posts.id
        WHERE leads.lead_score >= ?
        """
        # Complex join logic simplified for export
        df = pd.read_sql_query("SELECT * FROM leads WHERE lead_score >= ?", conn, params=(min_score,))
        # For the final CSV format as requested:
        export_query = """
        SELECT SUBSTR(leads.context, 0, 50) as snippet, author, lead_score, contact_info
        FROM leads WHERE lead_score >= ?
        """
        df.to_csv(self.csv_name, index=False)
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reddit High-Risk Lead Scraper")
    parser.add_argument("--subreddits", type=str, help="Comma separated list of subreddits")
    parser.add_argument("--limit", type=int, default=100, help="Limit of posts per subreddit")
    parser.add_argument("--time", type=str, default="all", choices=["all", "day", "week", "month"], help="Time filter")
    parser.add_argument("--output", type=str, default="highrisk_leads.csv", help="Output CSV filename")
    
    args = parser.parse_args()
    
    scraper = RedditLeadScraper()
    
    subs = args.subreddits.split(",") if args.subreddits else scraper.config["settings"]["subreddits"]
    
    for sub in subs:
        scraper.scrape_subreddit(sub.strip(), limit=args.limit, time_filter=args.time)
    
    scraper.export_csv()
    print("[+] Done!")
