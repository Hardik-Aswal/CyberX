#!/usr/bin/env python3
"""
discover_and_check.py

Find channels by keywords, join them, sample messages, classify with a model API,
and store only suspicious channel records in SQLite.

Config via .env:
 - TG_API_ID
 - TG_API_HASH
 - TG_PHONE
 - CLASSIFIER_API (e.g. http://127.0.0.1:8000/predict)
 - SAMPLE_SIZE (default 200)
 - MSG_LIMIT_PER_CHANNEL (default 200)
 - CHANNEL_THRESHOLD (default 0.6)
 - JOIN_IF_NEEDED (true/false)
"""

import os
import time
import json
import sqlite3
import argparse
from statistics import mean, median
from datetime import datetime
from dotenv import load_dotenv
import requests
from telethon import TelegramClient, errors
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel, Chat, User

load_dotenv()

API_ID = int(os.getenv("TG_API_ID") or 0)
API_HASH = os.getenv("TG_API_HASH")
PHONE = os.getenv("TG_PHONE")
CLASSIFIER_API = os.getenv("CLASSIFIER_API", "http://127.0.0.1:8000/predict")
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", "200"))
CHANNEL_THRESHOLD = float(os.getenv("CHANNEL_THRESHOLD", "0.6"))
JOIN_IF_NEEDED = os.getenv("JOIN_IF_NEEDED", "true").lower() in ("1","true","yes")
MSG_LIMIT_PER_CHANNEL = int(os.getenv("MSG_LIMIT_PER_CHANNEL", SAMPLE_SIZE))

DB_PATH = os.getenv("CHANNEL_DB", "suspicious_channels.db")
RATE_LIMIT_SECONDS = float(os.getenv("RATE_LIMIT_SECONDS", "1.0"))  # pause between API calls or joins

if not API_ID or not API_HASH:
    raise SystemExit("Please set TG_API_ID and TG_API_HASH in .env")

# ---------- DB helpers ----------
def init_db(conn):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS suspicious_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT,
            channel_id INTEGER,
            channel_title TEXT,
            first_seen TEXT,
            sample_size INTEGER,
            avg_prob REAL,
            median_prob REAL,
            pct90_prob REAL,
            reason TEXT,
            raw_metadata TEXT
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS checked_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE,
            last_checked TEXT,
            last_score REAL,
            checked_count INTEGER DEFAULT 0
        );
        """)

# ---------- Telethon helpers ----------
async def search_channels(client, query, limit=30):
    """
    SearchTelegram for query using contacts.SearchRequest.
    Returns list of (username, title, entity)
    """
    try:
        result = await client(SearchRequest(q=query, limit=limit))
        found = []
        # result.users and result.chats and result.chats might contain channels
        # Telethon returns chats in result.chats
        for chat in result.chats:
            # Only consider channels/chats that have a username (public)
            uname = getattr(chat, 'username', None)
            title = getattr(chat, 'title', None)
            if uname and (getattr(chat, 'megagroup', False) is False):
                found.append((uname, title, chat))
        return found
    except Exception as e:
        print("search_channels error:", e)
        return []

async def join_channel(client, username):
    try:
        # Telethon expects channel username or invite link name
        await client(JoinChannelRequest(username))
        print(f"Joined {username}")
        time.sleep(RATE_LIMIT_SECONDS)
        return True
    except errors.UserAlreadyParticipantError:
        return True
    except Exception as e:
        print("join_channel failed:", e)
        return False

# ---------- classification ----------
def classify_text_batch(texts):
    """
    Call your classifier API (FastAPI) for each text and return list of float probabilities for fraud.
    The API endpoint must accept {"text": "..."} and return {"prob_fraud": float, ...}
    This implementation sends requests serially to keep it simple and safe.
    """
    probs = []
    for t in texts:
        payload = {"text": t}
        try:
            r = requests.post(CLASSIFIER_API, json=payload, timeout=10)
            if r.status_code == 200:
                j = r.json()
                # support both keys
                p = j.get("prob_fraud") if isinstance(j.get("prob_fraud"), (int,float)) else (j.get("prob", {}).get("fraud") if j.get("prob") else None)
                if p is None:
                    # try alternate key
                    p = float(j.get("probability", 0.0)) if j.get("probability") else 0.0
                probs.append(float(p))
            else:
                print("Classifier API returned", r.status_code, r.text)
                probs.append(0.0)
        except Exception as e:
            print("Classifier request failed:", e)
            probs.append(0.0)
        time.sleep(0.1)  # tiny pause to avoid spamming local API
    return probs

# ---------- main pipeline ----------
async def evaluate_channel(client, conn, username, title=None):
    # Resolve entity
    try:
        entity = await client.get_entity(username)
    except Exception as e:
        print("Failed to resolve", username, e)
        return None

    # Optionally join
    if JOIN_IF_NEEDED:
        try:
            await join_channel(client, username)
        except Exception:
            pass

    # Sample latest messages (skip empty / service messages)
    texts = []
    async for msg in client.iter_messages(entity, limit=MSG_LIMIT_PER_CHANNEL):
        if not msg:
            continue
        text = msg.message
        if not text or not isinstance(text, str):
            continue
        texts.append(text)
        if len(texts) >= SAMPLE_SIZE:
            break

    if not texts:
        print("No textual messages for", username)
        return None

    print(f"Classifying {len(texts)} messages from {username} ...")
    probs = classify_text_batch(texts)

    avg_p = mean(probs) if probs else 0.0
    median_p = median(probs) if probs else 0.0
    pct90 = sorted(probs)[int(len(probs)*0.9)-1] if probs else 0.0

    # Decide channel suspiciousness
    reason = None
    suspicious = False
    # Example rule: avg or 90th percentile above threshold
    if avg_p >= CHANNEL_THRESHOLD or pct90 >= CHANNEL_THRESHOLD:
        suspicious = True
        reason = f"avg:{avg_p:.3f} pct90:{pct90:.3f}"

    now = datetime.utcnow().isoformat()

    # update checked_channels
    with conn:
        cur = conn.execute("SELECT * FROM checked_channels WHERE channel_username = ?", (username,))
        row = cur.fetchone()
        if row:
            conn.execute("UPDATE checked_channels SET last_checked=?, last_score=?, checked_count=checked_count+1 WHERE channel_username=?",
                         (now, avg_p, username))
        else:
            conn.execute("INSERT INTO checked_channels(channel_username,last_checked,last_score,checked_count) VALUES (?,?,?,1)",
                         (username, now, avg_p))

    if suspicious:
        metadata = {"sample_count": len(texts), "avg_prob": avg_p, "median_prob": median_p, "pct90_prob": pct90, "title": title}
        with conn:
            conn.execute("""
            INSERT INTO suspicious_channels(channel_username, channel_id, channel_title, first_seen, sample_size, avg_prob, median_prob, pct90_prob, reason, raw_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, getattr(entity, 'id', None), title or getattr(entity, 'title', None), now, len(texts), avg_p, median_p, pct90, reason, json.dumps(metadata)))
        print("Stored suspicious channel:", username, "score", avg_p)
    else:
        print("Channel appears clean:", username, "avg_prob", avg_p)

    return {"username": username, "avg_prob": avg_p, "pct90": pct90, "suspicious": suspicious}

async def run_discovery(keywords, limit_per_keyword=20):
    db_conn = sqlite3.connect(DB_PATH)
    init_db(db_conn)

    client = TelegramClient("discover_session", API_ID, API_HASH)
    await client.start(phone=PHONE)
    print("Logged in as", await client.get_me())

    for kw in keywords:
        print("Searching for:", kw)
        found = await search_channels(client, kw, limit=limit_per_keyword)
        print(f"Found {len(found)} candidate channels for '{kw}'")
        for uname, title, _chat in found:
            # Skip if already processed recently
            cur = db_conn.execute("SELECT last_checked FROM checked_channels WHERE channel_username = ?", (uname,))
            r = cur.fetchone()
            if r:
                # if last checked within 1 day, skip
                try:
                    last = datetime.fromisoformat(r[0])
                    if (datetime.utcnow() - last).total_seconds() < 24*3600:
                        print("Skipping recently checked", uname)
                        continue
                except Exception:
                    pass

            try:
                res = await evaluate_channel(client, db_conn, uname, title)
            except Exception as e:
                print("Error evaluating", uname, e)
            time.sleep(RATE_LIMIT_SECONDS)

    await client.disconnect()
    db_conn.close()

# ---------- CLI ----------
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", nargs="+", required=False,
                        help="Keywords to search for (space separated). Example: 'goa escort gambling job offer'")
    parser.add_argument("--keywords-file", type=str, help="File with keywords, one per line")
    parser.add_argument("--limit", type=int, default=20, help="How many channels to try per keyword")
    return parser.parse_args()

if __name__ == "__main__":
    import asyncio
    args = parse_args()
    kws = []
    if args.keywords:
        kws.extend(args.keywords)
    if args.keywords_file:
        with open(args.keywords_file, "r", encoding="utf8") as f:
            for line in f:
                s=line.strip()
                if s:
                    kws.append(s)
    if not kws:
        # default seeds
        kws = ["goa", "escorts", "gambling", "loan offer", "work from home", "job offer", "dating"]
    asyncio.run(run_discovery(kws, limit_per_keyword=args.limit))
