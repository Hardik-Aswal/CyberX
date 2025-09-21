from fastapi import APIRouter
from pydantic import BaseModel
from models.text_model import text_model
from datetime import datetime

router = APIRouter()

# Request model
class PhishingPredictRequest(BaseModel):
    text: str

# Response model
class PhishingPredictResponse(BaseModel):
    label: str        # "phishing" or "not_phishing"
    label_bin: int    # 1 or 0
    score: float      # probability
    timestamp: str

# POST endpoint for prediction
@router.post("/predict")
def predict(req: PhishingPredictRequest):
    text = req.text
    if not text.strip():
        return {"error": "Empty text"}
    
    # Predict class (0/1)
    label_bin = int(text_model.predict([text])[0])
    
    # Predict probability for class 1
    try:
        score = float(text_model.predict_proba([text])[0,1])
    except Exception:
        # fallback if model doesn't have predict_proba
        import math
        try:
            df = float(text_model.decision_function([text])[0])
            score = 1.0 / (1.0 + math.exp(-df))
        except Exception:
            score = 1.0 if label_bin==1 else 0.0
    
    label = "phishing" if label_bin == 1 else "not_phishing"
    
    return PhishingPredictResponse(
        label=label,
        label_bin=label_bin,
        score=score,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
