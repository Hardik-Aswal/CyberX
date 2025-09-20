#!/usr/bin/env python3
# telethon_scraper/dump_channel.py
# Minimal Telethon scraper that saves messages to JSONL and downloads media.
import asyncio, json, os, re, time
from pathlib import Path
from telethon import TelegramClient, errors
from telethon.tl.types import Message
from dotenv import load_dotenv


# --- CONFIG ---
API_ID = 1234567           # replace
API_HASH = "your_api_hash" # replace
SESSION_NAME = "session"
CHANNEL = "t.me/somechannel"  # username or t.me link or channel id
OUT_JSONL = "../data/messages.jsonl"
MEDIA_FOLDER = "media"
BATCH_SIZE = 100

def safe_filename(s: str, max_len=200):
    s = re.sub(r'[\\/:"*?<>|]+', '_', s)
    return s[:max_len]

def message_to_dict(msg: Message):
    return {
        "id": msg.id,
        "date": msg.date.isoformat() if msg.date else None,
        "text": msg.message,
        "from_id": getattr(msg.from_id, 'user_id', None) if getattr(msg, 'from_id', None) else None,
        "reply_to_msg_id": msg.reply_to_msg_id,
        "media": bool(msg.media),
        "views": getattr(msg, 'views', None)
    }

async def main():
    Path(MEDIA_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(os.path.dirname(OUT_JSONL)).mkdir(parents=True, exist_ok=True)
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("Logged in as:", await client.get_me())
    try:
        entity = await client.get_entity(CHANNEL)
    except Exception as e:
        print("Failed to resolve channel:", e)
        return

    last_saved_id = None
    if os.path.exists(OUT_JSONL):
        try:
            with open(OUT_JSONL, 'rb') as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell() - 1
                while pos > 0:
                    f.seek(pos)
                    if f.read(1) == b'\\n':
                        break
                    pos -= 1
                if pos > 0:
                    f.seek(pos+1)
                else:
                    f.seek(0)
                last_line = f.readline().decode().strip()
                if last_line:
                    last_saved_id = json.loads(last_line).get('id')
                    print("Resuming after id:", last_saved_id)
        except Exception:
            last_saved_id = None

    with open(OUT_JSONL, 'a', encoding='utf8') as out_f:
        total = 0
        try:
            async for msg in client.iter_messages(entity, reverse=True):
                if last_saved_id and msg.id <= last_saved_id:
                    continue
                d = message_to_dict(msg)
                if msg.media:
                    try:
                        safe_name = f"{entity.id}_{msg.id}_{safe_filename((msg.message or '')[:40])}"
                        file_path = await client.download_media(msg, file=os.path.join(MEDIA_FOLDER, safe_name))
                        d['media_path'] = str(file_path)
                    except Exception as me:
                        print("Media error:", me)
                out_f.write(json.dumps(d, ensure_ascii=False) + "\\n")
                out_f.flush()
                total += 1
                if total % 100 == 0:
                    print("Saved", total, "messages; last id", msg.id)
            print("Finished. New messages saved:", total)
        except errors.FloodWaitError as fwe:
            print("Rate limited. Wait seconds:", fwe.seconds)
            time.sleep(fwe.seconds + 1)
        except Exception as e:
            print("Error:", e)
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
