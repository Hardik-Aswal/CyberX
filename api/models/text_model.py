import os
import joblib
from dotenv import load_dotenv

load_dotenv()

TEXT_MODEL_PATH = os.environ.get("TEXT_MODEL_PATH")

text_model = joblib.load(TEXT_MODEL_PATH)
