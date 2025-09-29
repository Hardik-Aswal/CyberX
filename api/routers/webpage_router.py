# api/routers/webpage_router.py - Complete Fixed Implementation
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
        cursor.execute(query, params + [limit, offset])
        
        rows = cursor.fetchall()
        pages = []
        
        for row in rows:
            page = SuspiciousWebpage(
                id=row[0],
                url=row[1],
                label=row[2],
                score=row[3],
                text_snippet=row[4] or "",
                scraped_at=row[5],
                risk_level=get_risk_level(row[3]),
                days_ago=calculate_days_ago(row[5]),
                domain=extract_domain(row[1])
            )
            pages.append(page)
        
        # Calculate statistics
        cursor.execute("SELECT score, scraped_at, url FROM suspicious_pages")
        all_pages = cursor.fetchall()
        
        total_flagged = len(all_pages)
        high_risk = len([p for p in all_pages if p[0] >= 0.8])
        medium_risk = len([p for p in all_pages if 0.6 <= p[0] < 0.8])
        low_risk = len([p for p in all_pages if p[0] < 0.6])
        
        # Calculate today and this week counts
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        found_today = 0
        found_this_week = 0
        unique_domains = set()
        
        for p in all_pages:
            try:
                page_date = datetime.fromisoformat(p[1].replace('Z', '+00:00')).date()
                if page_date == today:
                    found_today += 1
                if page_date >= week_ago:
                    found_this_week += 1
                unique_domains.add(extract_domain(p[2]))
            except:
                continue
        
        avg_risk_score = sum([p[0] for p in all_pages]) / len(all_pages) if all_pages else 0
        
        stats = WebpageStats(
            total_flagged=total_flagged,
            high_risk=high_risk,
            medium_risk=medium_risk,
            low_risk=low_risk,
            found_today=found_today,
            found_this_week=found_this_week,
            avg_risk_score=round(avg_risk_score, 3),
            unique_domains=len(unique_domains)
        )
        
        conn.close()
        
        return WebpageResponse(
            pages=pages,
            stats=stats,
            total_count=total_count
        )
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/stats", response_model=WebpageStats)
async def get_webpage_stats(current_user: dict = Depends(get_current_user)):
    """Get webpage statistics"""
    
    if not os.path.exists(WEBPAGES_DB):
        raise HTTPException(status_code=404, detail="Webpages database not found")
    
    try:
        conn = sqlite3.connect(WEBPAGES_DB)
        cursor = conn.cursor()
        
        cursor.execute("SELECT score, scraped_at, url FROM suspicious_pages")
        all_pages = cursor.fetchall()
        
        total_flagged = len(all_pages)
        high_risk = len([p for p in all_pages if p[0] >= 0.8])
        medium_risk = len([p for p in all_pages if 0.6 <= p[0] < 0.8])
        low_risk = len([p for p in all_pages if p[0] < 0.6])
        
        # Calculate today and this week counts
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        found_today = 0
        found_this_week = 0
        unique_domains = set()
        
        for p in all_pages:
            try:
                page_date = datetime.fromisoformat(p[1].replace('Z', '+00:00')).date()
                if page_date == today:
                    found_today += 1
                if page_date >= week_ago:
                    found_this_week += 1
                unique_domains.add(extract_domain(p[2]))
            except:
                continue
        
        avg_risk_score = sum([p[0] for p in all_pages]) / len(all_pages) if all_pages else 0
        
        conn.close()
        
        return WebpageStats(
            total_flagged=total_flagged,
            high_risk=high_risk,
            medium_risk=medium_risk,
            low_risk=low_risk,
            found_today=found_today,
            found_this_week=found_this_week,
            avg_risk_score=round(avg_risk_score, 3),
            unique_domains=len(unique_domains)
        )
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/pages/{page_id}")
async def get_webpage_details(
    page_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific webpage"""
    
    if not os.path.exists(WEBPAGES_DB):
        raise HTTPException(status_code=404, detail="Webpages database not found")
    
    try:
        conn = sqlite3.connect(WEBPAGES_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM suspicious_pages WHERE id = ?
        """, (page_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Webpage not found")
        
        return {
            "id": row[0],
            "url": row[1],
            "label": row[2],
            "score": row[3],
            "text_snippet": row[4],
            "scraped_at": row[5],
            "risk_level": get_risk_level(row[3]),
            "days_ago": calculate_days_ago(row[5]),
            "domain": extract_domain(row[1])
        }
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/domains")
async def get_unique_domains(current_user: dict = Depends(get_current_user)):
    """Get list of unique domains found in suspicious pages"""
    
    if not os.path.exists(WEBPAGES_DB):
        raise HTTPException(status_code=404, detail="Webpages database not found")
    
    try:
        conn = sqlite3.connect(WEBPAGES_DB)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT url FROM suspicious_pages")
        urls = cursor.fetchall()
        
        domains = {}
        for (url,) in urls:
            domain = extract_domain(url)
            if domain in domains:
                domains[domain] += 1
            else:
                domains[domain] = 1
        
        conn.close()
        
        # Sort by count descending
        sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "domains": [{"domain": domain, "count": count} for domain, count in sorted_domains],
            "total_domains": len(sorted_domains)
        }
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")