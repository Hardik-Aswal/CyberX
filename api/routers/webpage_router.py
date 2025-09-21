# api/routers/webpage_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from datetime import datetime, timedelta
import os
from .auth_router import get_current_user

router = APIRouter()

# Database path
WEBPAGES_DB = os.getenv("WEBPAGES_DB", "webcrawler/fraud.db")

class SuspiciousWebpage(BaseModel):
    id: int
    url: str
    label: str
    score: float
    text_snippet: str
    scraped_at: str
    risk_level: str
    days_ago: int
    domain: str

class WebpageStats(BaseModel):
    total_flagged: int
    high_risk: int
    medium_risk: int
    low_risk: int
    found_today: int
    found_this_week: int
    avg_risk_score: float
    unique_domains: int

class WebpageResponse(BaseModel):
    pages: List[SuspiciousWebpage]
    stats: WebpageStats
    total_count: int

def get_risk_level(score: float) -> str:
    """Determine risk level based on score"""
    if score >= 0.8:
        return "HIGH"
    elif score >= 0.6:
        return "MEDIUM"
    else:
        return "LOW"

def calculate_days_ago(date_str: str) -> int:
    """Calculate days since the given date"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return (datetime.now() - date_obj.replace(tzinfo=None)).days
    except:
        return 0

def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return "unknown"

@router.get("/pages", response_model=WebpageResponse)
async def get_suspicious_webpages(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    risk_level: Optional[str] = Query(None, regex="^(HIGH|MEDIUM|LOW)$"),
    domain: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get suspicious webpages with filtering and pagination"""
    
    if not os.path.exists(WEBPAGES_DB):
        raise HTTPException(status_code=404, detail="Webpages database not found")
    
    try:
        conn = sqlite3.connect(WEBPAGES_DB)
        cursor = conn.cursor()
        
        # Base query
        base_query = """
            SELECT id, url, label, score, text_snippet, scraped_at
            FROM suspicious_pages
        """
        
        # Build where clause and parameters
        where_conditions = []
        params = []
        
        if risk_level:
            if risk_level == "HIGH":
                where_conditions.append("score >= 0.8")
            elif risk_level == "MEDIUM":
                where_conditions.append("score >= 0.6 AND score < 0.8")
            elif risk_level == "LOW":
                where_conditions.append("score < 0.6")
        
        if domain:
            where_conditions.append("url LIKE ?")
            params.append(f"%{domain}%")
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM suspicious_pages {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results
        query = f"{base_query} {where_clause} ORDER BY score DESC, scraped_at DESC LIMIT ? OFFSET ?"