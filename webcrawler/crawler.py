"""
Crawler that:
- reads baseurl.txt (one URL per line)
- respects robots.txt
- fetches page, extracts visible text
- POSTs to model server /predict (port configured by MODEL_SERVER_URL env or default http://127.0.0.1:8100)
- stores pages classified as spam (above threshold) into SQLite DB fraud.db

Usage:
    python crawler.py
"""
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import urllib.robotparser
import sqlite3
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()  # load .env file

# --------------------------
# Config from .env
# --------------------------
USER_AGENT = os.getenv("USER_AGENT", "GoaCyberCrawler/1.0 (+https://example.com/contact)")
MODEL_SERVER = os.getenv("MODEL_SERVER_URL", "http://127.0.0.1:8100")
BASEFILE = os.getenv("BASEURL_FILE", "baseurl.txt")
DBFILE = os.getenv("DB_FILE", "fraud.db")
THRESHOLD = float(os.getenv("CRAWLER_THRESHOLD", "0.6"))
DELAY = float(os.getenv("CRAWLER_DELAY", "2.0"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "20000"))
MAX_SNIPPET = int(os.getenv("MAX_SNIPPET_LENGTH", "2000"))

# --------------------------
# Helper functions
# --------------------------
def can_fetch(url, user_agent=USER_AGENT):
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True  # allow by default on error

def extract_visible_text(html):
    soup = BeautifulSoup(html, "lxml")
    for s in soup(['script','style','noscript','header','footer','nav','svg','form','iframe']):
        s.decompose()
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)

def ensure_db(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suspicious_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        label TEXT,
        score REAL,
        text_snippet TEXT,
        scraped_at TEXT
    )
    """)
    conn.commit()

def save_suspicious(conn, url, label, score, text, max_snippet=MAX_SNIPPET):
    cur = conn.cursor()
    snippet = text[:max_snippet]
    cur.execute(
        "INSERT INTO suspicious_pages (url,label,score,text_snippet,scraped_at) VALUES (?,?,?,?,?)",
        (url, label, float(score), snippet, datetime.utcnow().isoformat() + "Z")
    )
    conn.commit()

def predict_text(model_server, text, url=None, timeout=10):
    payload = {"text": text}
    if url:
        payload["url"] = url
    try:
        r = requests.post(model_server.rstrip("/") + "/predict", json=payload, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        else:
            return {"error": f"Status {r.status_code}", "raw": r.text}
    except Exception as e:
        return {"error": str(e)}

# --------------------------
# Main crawler logic
# --------------------------
def main():
    with open(BASEFILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    conn = sqlite3.connect(DBFILE)
    ensure_db(conn)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for url in tqdm(urls, desc="URLs"):
        try:
            if not can_fetch(url):
                print(f"Skipping due to robots.txt: {url}")
                continue
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"Skipping {url}, status {resp.status_code}")
                continue
            text = extract_visible_text(resp.text)
            if not text.strip():
                print(f"No text extracted from {url}")
                continue
            payload_text = text[:MAX_TEXT_LENGTH]
            res = predict_text(MODEL_SERVER, payload_text, url=url)
            if res.get("error"):
                print("Model server error for", url, res.get("error"))
                continue
            label = res.get("label")
            score = float(res.get("score", 0.0))
            print(f"URL={url} label={label} score={score:.3f}")
            if label == "spam" or score >= THRESHOLD:
                save_suspicious(conn, url, label, score, text)
                print("Saved suspicious page:", url)
        except Exception as e:
            print("Error with", url, e)
        time.sleep(DELAY)  # polite crawling

    conn.close()

if __name__ == "__main__":
    main()
