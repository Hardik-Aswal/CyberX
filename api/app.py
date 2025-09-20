# api/app.py
from fastapi import FastAPI
from pydantic import BaseModel
import joblib

app = FastAPI(title="Fraud Telegram Classifier")

# Load trained model
model = joblib.load("/home/gawd/fraud-telegram-classifier/models/baseline_tfidf_lr.joblib")

class Msg(BaseModel):
    text: str

@app.post("/predict")
def predict(msg: Msg):
    text = [msg.text]
    pred = model.predict(text)[0]           # 0 = normal, 1 = fraud
    prob = model.predict_proba(text)[0][1]  # probability of fraud
    return {"label_pred": int(pred), "prob_fraud": float(prob)}
