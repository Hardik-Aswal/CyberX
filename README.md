# Fraud Telegram Classifier — Complete Repo

## Overview
This repository contains a complete, ready-to-run project to:
1. Scrape Telegram channel messages using Telethon.
2. Train a baseline ML classifier (TF-IDF + Logistic Regression).
3. Provide a Transformer fine-tuning script (Hugging Face).
4. Serve the model via FastAPI for online inference.
5. Example data, labeling guidelines, and Dockerfile for deployment.

**Important**: Only scrape and classify messages you have legal permission to process.

---

## Repo structure
```
fraud-telegram-classifier/
├─ telethon_scraper/
│  └─ dump_channel.py            # Telethon-based scraper (saves JSONL + media)
├─ models/
│  ├─ baseline_train.py          # TF-IDF + Logistic Regression training & save
│  └─ finetune_transformer.py    # Hugging Face fine-tuning starter script
├─ api/
│  └─ app.py                     # FastAPI inference server (baseline & transformer)
├─ utils/
│  └─ text_clean.py              # text cleaning helpers
├─ labeling/
│  └─ labeling_guidelines.md
├─ data/
│  └─ sample_labeled.jsonl       # small synthetic labeled dataset
├─ requirements.txt
├─ Dockerfile
├─ README.md
└─ LICENSE
```

---

## Quick start (local)
1. Create Python venv:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure Telegram API credentials for scraper:
- Go to https://my.telegram.org → API development tools → Create new app.
- Fill *App title*, *Short name*, etc. Copy `api_id` and `api_hash`.
- Edit `telethon_scraper/dump_channel.py` and set `API_ID`, `API_HASH`, `CHANNEL`.

3. Run scraper (interactive login on first run):
```bash
python telethon_scraper/dump_channel.py
```

4. Train baseline model:
```bash
python models/baseline_train.py --input data/sample_labeled.jsonl --out models/baseline_tfidf_lr.joblib
```

5. Run API:
```bash
uvicorn api.app:app --reload --port 8000
```

---

## Architecture (detailed)
**1. Data collection**
- `telethon_scraper/dump_channel.py` logs in with your user account (phone OTP), iterates channel messages, saves each message as a JSON line in `data/messages.jsonl`, and downloads media to `telethon_scraper/media/`.
- Script supports resuming after interruptions using the last saved message id.

**2. Data storage**
- Labeled dataset: `data/*.jsonl` with `{id, text, label}` lines.
- You can import JSONL into SQLite or a managed DB for production.

**3. Models**
- Baseline: `models/baseline_train.py` builds TF-IDF features + LogisticRegression (fast, interpretable). Saved with `joblib`.
- Advanced: `models/finetune_transformer.py` is a starter to fine-tune Hugging Face models (DistilBERT/XLM-R) using `datasets` & `transformers`.

**4. Serving**
- `api/app.py` loads either baseline or transformer model and exposes `/predict` POST endpoint returning `label_pred` and `prob_fraud`.
- For production, wrap with Docker and run behind a reverse proxy; use GPU nodes for transformer inference.

**5. Monitoring & Ops**
- Log predictions, false positives, and false negatives to a monitoring table.
- Periodically sample low-confidence predictions for human labeling (active learning).
- Retrain nightly/weekly using newly labeled data.

---

## Next steps & suggestions
- Add label-studio integration for annotation.
- Add active learning loop (uncertainty sampling).
- Add domain features (URL reputation lookups).
- Add unit tests and CI pipeline.

--- 
