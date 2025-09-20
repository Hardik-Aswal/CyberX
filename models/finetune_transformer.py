#!/usr/bin/env python3
# models/finetune_transformer.py
# Starter script to fine-tune a HF transformer for binary classification.
# WARNING: Requires GPU for practical training speed.

from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import json, numpy as np
import argparse

def load_jsonl(path):
    data = []
    with open(path, 'r', encoding='utf8') as f:
        for line in f:
            j = json.loads(line)
            data.append({'text': j.get('text',''), 'label': int(j.get('label',0))})
    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='../data/sample_labeled.jsonl')
    parser.add_argument('--model', default='distilbert-base-uncased')
    parser.add_argument('--output', default='../models/fraud_transformer')
    args = parser.parse_args()

    raw = load_jsonl(args.input)
    ds = Dataset.from_list(raw)
    ds = ds.train_test_split(test_size=0.2, stratify_by_column='label', seed=42)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    def prep(ex):
        return tokenizer(ex['text'], truncation=True, padding='max_length', max_length=256)
    ds = ds.map(prep, batched=True)

    ds = ds.rename_column('label', 'labels')
    ds.set_format(type='torch', columns=['input_ids','attention_mask','labels'])

    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)

    training_args = TrainingArguments(
        output_dir=args.output,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        num_train_epochs=3,
        evaluation_strategy='epoch',
        save_strategy='epoch',
        logging_steps=100
    )

    def compute_metrics(eval_pred):
        from evaluate import load
        acc = load('accuracy')
        preds = np.argmax(eval_pred.predictions, axis=-1)
        return {'accuracy': acc.compute(predictions=preds, references=eval_pred.label_ids)['accuracy']}

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds['train'],
        eval_dataset=ds['test'],
        compute_metrics=compute_metrics
    )

    trainer.train()
    trainer.save_model(args.output)

if __name__ == '__main__':
    main()
