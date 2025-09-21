"""
Crawler that:
- reads baseurl.txt (one URL per line)
- respects robots.txt
- fetches page, extracts visible text
- POSTs to model server /predict (port configured by MODEL_SERVER_URL env or default http://127.0.0.1:8100)
- stores pages classified as spam (above threshold) into SQLite DB fraud.db

Usage:
    python crawler.py --base baseurl.txt --db fraud.db --threshold 0.6
"""
import argparse
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import urllib.robotparser
import sqlite3
from datetime import datetime
from tqdm import tqdm

USER_AGENT = "GoaCyberCrawler/1.0 (+https://example.com/contact)"

def can_fetch(url, user_agent=USER_AGENT):
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        # On error, be conservative and allow (or you could disallow). We'll allow but with a delay.
        return True

def extract_visible_text(html):
    soup = BeautifulSoup(html, "lxml")
    # remove scripts/styles
    for s in soup(['script','style','noscript','header','footer','nav','svg','form','iframe']):
        s.decompose()
    text = soup.get_text(separator="\n")
    # Collapse whitespace and heuristics
    lines = [line.strip() for line in text.splitlines()]
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

def save_suspicious(conn, url, label, score, text, max_snippet=2000):
    cur = conn.cursor()
    snippet = text[:max_snippet]
    cur.execute("INSERT INTO suspicious_pages (url,label,score,text_snippet,scraped_at) VALUES (?,?,?,?,?)",
                (url, label, float(score), snippet, datetime.utcnow().isoformat() + "Z"))
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

def main(args):
    basefile = args.base
    dbfile = args.db
    threshold = float(args.threshold)
    delay = float(args.delay)
    model_server = args.model_server

    with open(basefile, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    conn = sqlite3.connect(dbfile)
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
            # Optionally truncate long pages (to limit payload)
            payload_text = text[:20000]
            res = predict_text(model_server, payload_text, url=url)
            if res.get("error"):
                print("Model server error for", url, res.get("error"))
                continue
            label = res.get("label")
            score = float(res.get("score", 0.0))
            print(f"URL={url} label={label} score={score:.3f}")
            if label == "spam" or score >= threshold:
                save_suspicious(conn, url, label, score, text)
                print("Saved suspicious page:", url)
        except Exception as e:
            print("Error with", url, e)
        time.sleep(delay)  # polite crawling
    conn.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--base', default='baseurl.txt', help='file with base URLs, one per line')
    p.add_argument('--db', default='fraud.db', help='sqlite db file to store suspicious pages')
    p.add_argument('--threshold', default=0.6, help='probability threshold to mark as suspicious')
    p.add_argument('--delay', default=2.0, help='delay between requests (seconds)')
    p.add_argument('--model-server', default='http://127.0.0.1:8100', help='model server URL (must include /predict endpoint)')
    args = p.parse_args()
    main(args)
