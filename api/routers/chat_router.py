from fastapi import APIRouter
from pydantic import BaseModel
from models.chat_model import chat_model
from datetime import datetime

router = APIRouter()

class SpamPredictRequest(BaseModel):
    text: str

class SpamPredictResponse(BaseModel):
    label: str
    label_bin: int
    score: float
    timestamp: str

@router.post("/predict")
def predict(req: SpamPredictRequest):
    text = req.text
    label_bin = int(chat_model.predict([text])[0])
    score = float(chat_model.predict_proba([text])[0,1])
    label = "spam" if label_bin else "not_spam"
    return SpamPredictResponse(
        label=label,
        label_bin=label_bin,
        score=score,
        timestamp=datetime.utcnow().isoformat()+"Z"
    )
