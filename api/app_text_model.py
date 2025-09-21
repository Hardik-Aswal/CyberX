"""
FastAPI model server exposing a /predict endpoint.
Runs on port specified by environment var MODEL_PORT (default 8100). Do not run on 8000.
"""
from dotenv import load_dotenv
import os
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uvicorn

load_dotenv()
MODEL_PATH = os.environ.get('MODEL_PATH', 'model_pipeline.joblib')
DEFAULT_PORT = int(os.environ.get('MODEL_PORT', '8100'))  # default port 8100; user asked not 8000

class PredictRequest(BaseModel):
    url: Optional[str] = None
    text: str

class PredictResponse(BaseModel):
    label: str
    label_bin: int
    score: float
    model: str
    timestamp: str

app = FastAPI(title="Goa Cyber-Scam Classifier")

@app.on_event("startup")
def load_model():
    global model
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Model file not found at {MODEL_PATH}; please train first.")
    model = joblib.load(MODEL_PATH)
    # check that model has predict_proba; if not we will fallback to decision_function
    print("Loaded model:", MODEL_PATH)

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    text = req.text
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    # we expect pipeline supporting predict and predict_proba or decision_function
    try:
        label_bin = int(model.predict([text])[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    score = None
    try:
        if hasattr(model, "predict_proba"):
            score = float(model.predict_proba([text])[0,1])
        elif hasattr(model, "decision_function"):
            # convert to sigmoid
            import math
            df = float(model.decision_function([text])[0])
            score = 1.0 / (1.0 + math.exp(-df))
        else:
            score = 1.0 if label_bin==1 else 0.0
    except Exception:
        score = 1.0 if label_bin==1 else 0.0

    label = "spam" if label_bin == 1 else "not_spam"
    return PredictResponse(
        label=label,
        label_bin=label_bin,
        score=score,
        model=os.path.basename(MODEL_PATH),
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

@app.get("/health")
def health():
    return {"status":"ok"}

if __name__ == "__main__":
    port = DEFAULT_PORT
    # Never bind to 8000 to honor user's constraint
    if port == 8000:
        raise SystemExit("Configured port cannot be 8000. Set MODEL_PORT to another port.")
    # run uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=port, workers=1)
