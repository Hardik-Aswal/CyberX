import pandas as pd
import json

# Path to your CSV file
csv_file = "dataset.csv"

# Read the CSV file
df = pd.read_csv(csv_file)

# Open JSONL file for writing
with open("sample_labeled.jsonl", "w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        label = 1 if str(row["text_type"]).strip().lower() == "spam" else 0
        obj = {"text": str(row["text"]).strip(), "label": label}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

print("JSONL file saved as sample_labeled.jsonl")
