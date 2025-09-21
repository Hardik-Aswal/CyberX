"""
Finetuner does incremental training on top of an existing pipeline.
It expects the saved pipeline from baseline_train.py. It uses partial_fit
to update an SGDClassifier head (so we replace the final clf with a partial-fit capable one).
If you want batch re-training instead, you can call baseline_train again with merged data.
"""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import LabelBinarizer
from sklearn.metrics import classification_report

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
    pipeline_path = Path(args.pipeline)
    if not pipeline_path.exists():
        raise SystemExit("Pipeline not found: " + str(pipeline_path))
    pipeline = joblib.load(pipeline_path)

    data = load_jsonl(args.input)
    data = data.dropna(subset=['text', 'label'])
    data['label_bin'] = data['label'].apply(lambda x: 1 if str(x).lower() in ('spam','fraud','scam','1','true') else 0)
    X = data['text'].astype(str).values
    y = data['label_bin'].values

    # Extract vectorizer and features
    # Assume pipeline steps: tfidf -> clf
    tfidf = pipeline.named_steps.get('tfidf')
    old_clf = pipeline.named_steps.get('clf')

    # Build features
    X_feats = tfidf.transform(X)

    # Create or reuse an SGDClassifier (supports partial_fit)
    if not isinstance(old_clf, SGDClassifier):
        print("Replacing final classifier with SGDClassifier for incremental training.")
        clf = SGDClassifier(loss='log', max_iter=5, tol=None)
    else:
        clf = old_clf

    # partial_fit requires the classes list
    classes = np.array([0,1])
    clf.partial_fit(X_feats, y, classes=classes)

    # put back to pipeline and save
    pipeline.named_steps['clf'] = clf
    joblib.dump(pipeline, pipeline_path)
    print(f"Updated pipeline saved to {pipeline_path}")

    # quick eval on the finetune data
    y_pred = pipeline.predict(X)
    print("Finetune data performance:")
    print(classification_report(y, y_pred, digits=4))

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--pipeline', default='model_pipeline.joblib', help='existing pipeline')
    p.add_argument('--input', default='sample_labeled.jsonl', help='jsonl of new labeled data')
    args = p.parse_args()
    main(args)
