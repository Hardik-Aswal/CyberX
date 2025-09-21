"""
Train a baseline TF-IDF + LogisticRegression classifier for 'spam' (cyber scam in Goa)
Input: sample_labeled.jsonl (one JSON object per line: {"text": "...", "label": "spam"|"not_spam"})
Output: saved pipeline -> model_pipeline.joblib
"""
import json
import argparse
from pathlib import Path
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib

def load_jsonl(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(rows)

def main(args):
    data = load_jsonl(args.input)
    if data.empty:
        raise SystemExit("No data found in sample_labeled.jsonl")
    if 'text' not in data.columns or 'label' not in data.columns:
        raise SystemExit("Each line must have 'text' and 'label' fields")
    # Normalize labels to 0/1
    data = data.dropna(subset=['text', 'label'])
    data['label_bin'] = data['label'].apply(lambda x: 1 if str(x).lower() in ('spam','fraud','scam','1','true') else 0)

    X = data['text'].astype(str).values
    y = data['label_bin'].values

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(strip_accents='unicode', lowercase=True,
                                  ngram_range=(1,2), max_features=50000)),
        ('clf', LogisticRegression(max_iter=200, solver='saga', class_weight='balanced', n_jobs=-1))
    ])

    print("Training baseline model...")
    pipeline.fit(X_train, y_train)

    print("Evaluating...")
    y_pred = pipeline.predict(X_val)
    y_proba = pipeline.predict_proba(X_val)[:,1] if hasattr(pipeline, "predict_proba") else None

    print(classification_report(y_val, y_pred, digits=4))
    if y_proba is not None and len(set(y_val)) > 1:
        try:
            print("ROC AUC:", roc_auc_score(y_val, y_proba))
        except Exception:
            pass

    out = Path(args.output)
    joblib.dump(pipeline, out)
    print(f"Saved pipeline to {out}")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='sample_labeled.jsonl', help='jsonl file with sample labeled data')
    p.add_argument('--output', default='model_pipeline.joblib', help='where to save trained pipeline')
    args = p.parse_args()
    main(args)
