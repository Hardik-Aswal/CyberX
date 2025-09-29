# api/app.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from routers.chat_router import router as chat_router
from routers.text_router import router as text_router
from routers.auth_router import router as auth_router
from routers.telegram_router import router as telegram_router
from routers.webpage_router import router as webpage_router
from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()
PORT = int(os.environ.get("MODEL_PORT", 8100))

app = FastAPI(title="Goa Cyber Scam Cyber Patrolling", version="1.0.0")

# CORS middleware for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(telegram_router, prefix="/api/telegram", tags=["telegram"])
app.include_router(webpage_router, prefix="/api/webpages", tags=["webpages"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(text_router, prefix="/text", tags=["text"])

@app.get("/health")
def health():
    return {"status": "ok"}

# Serve the main frontend application
@app.get("/")
async def read_index():
    return FileResponse('frontend/templates/index.html')

# Catch-all route for SPA routing
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # If it's an API route, let it pass through
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # For all other routes, serve the main app
    return FileResponse('frontend/templates/index.html')

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, workers=1, reload=True)