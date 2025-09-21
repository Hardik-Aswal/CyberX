from fastapi import FastAPI
from routers.chat_router import router as chat_router
from routers.text_router import router as text_router
from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()
PORT = int(os.environ.get("MODEL_PORT", 8100))

app = FastAPI(title="Goa Cyber Scam Cyber Patrolling")

# Include both routers
app.include_router(chat_router, prefix="/chat")
app.include_router(text_router, prefix="/text")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, workers=1)
