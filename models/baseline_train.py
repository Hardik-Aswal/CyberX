#!/usr/bin/env python3
# models/baseline_train.py
# Train TF-IDF + Logistic Regression on labeled JSONL.
import argparse, json, re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib

def clean_text(s):
    s = str(s).lower()
    s = re.sub(r'http\\S+', ' <URL> ', s)
    s = re.sub(r'@\\w+', ' <MENTION> ', s)
    s = re.sub(r'\\d+', ' <NUM> ', s)
    return s

def load_jsonl(path):
    rows = []
    with open(path, 'r', encoding='utf8') as f:
        for line in f:
            rows.append(json.loads(line))
    return pd.DataFrame(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='../data/sample_labeled.jsonl')
    parser.add_argument('--out', default='../models/baseline_tfidf_lr.joblib')
    args = parser.parse_args()

    df = load_jsonl(args.input)
    df['text_clean'] = df['text'].apply(clean_text)
    X = df['text_clean'].values
    y = df['label'].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    vec = TfidfVectorizer(ngram_range=(1,2), max_df=0.9, min_df=2, max_features=50000)
    clf = LogisticRegression(max_iter=1000, class_weight='balanced')
    pipe = make_pipeline(vec, clf)
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:,1]
    print(classification_report(y_test, y_pred, digits=4))
    print("ROC AUC:", roc_auc_score(y_test, y_proba))

    joblib.dump(pipe, args.out)
    print("Saved model to", args.out)

if __name__ == '__main__':
    main()
