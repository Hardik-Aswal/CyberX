import os
import joblib
from dotenv import load_dotenv

load_dotenv()

CHAT_MODEL_PATH = os.environ.get("CHAT_MODEL_PATH")

# Load model once on import
chat_model = joblib.load(CHAT_MODEL_PATH)
