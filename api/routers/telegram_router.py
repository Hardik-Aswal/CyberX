# api/routers/telegram_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from datetime import datetime, timedelta
import os
from .auth_router import get_current_user

router = APIRouter()

# Database path
CHANNELS_DB = os.getenv("CHANNELS_DB", "telethon_scraper/suspicious_channels.db")

class TelegramChannel(BaseModel):
    id: int
    channel_username: str
    channel_id: Optional[int]
    channel_title: Optional[str]
    first_seen: str
    sample_size: int
    avg_prob: float
    median_prob: float
    pct90_prob: float
    reason: str
    risk_level: str
    days_ago: int

class TelegramStats(BaseModel):
    total_flagged: int
    high_risk: int
    medium_risk: int
    low_risk: int
    found_today: int
    found_this_week: int
    avg_risk_score: float

class TelegramResponse(BaseModel):
    channels: List[TelegramChannel]
    stats: TelegramStats
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

@router.get("/channels", response_model=TelegramResponse)
async def get_telegram_channels(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    risk_level: Optional[str] = Query(None, regex="^(HIGH|MEDIUM|LOW)$"),
    current_user: dict = Depends(get_current_user)
):
    """Get flagged Telegram channels with filtering and pagination"""
    
    if not os.path.exists(CHANNELS_DB):
        raise HTTPException(status_code=404, detail="Channels database not found")
    
    try:
        conn = sqlite3.connect(CHANNELS_DB)
        cursor = conn.cursor()
        
        # Base query
        base_query = """
            SELECT id, channel_username, channel_id, channel_title, 
                   first_seen, sample_size, avg_prob, median_prob, 
                   pct90_prob, reason
            FROM suspicious_channels
        """
        
        # Add risk level filtering if specified
        where_clause = ""
        params = []
        
        if risk_level:
            if risk_level == "HIGH":
                where_clause = "WHERE avg_prob >= 0.8"
            elif risk_level == "MEDIUM":
                where_clause = "WHERE avg_prob >= 0.6 AND avg_prob < 0.8"
            elif risk_level == "LOW":
                where_clause = "WHERE avg_prob < 0.6"
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM suspicious_channels {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results
        query = f"{base_query} {where_clause} ORDER BY avg_prob DESC, first_seen DESC LIMIT ? OFFSET ?"
        cursor.execute(query, params + [limit, offset])
        
        rows = cursor.fetchall()
        channels = []
        
        for row in rows:
            channel = TelegramChannel(
                id=row[0],
                channel_username=row[1],
                channel_id=row[2],
                channel_title=row[3],
                first_seen=row[4],
                sample_size=row[5],
                avg_prob=row[6],
                median_prob=row[7],
                pct90_prob=row[8],
                reason=row[9],
                risk_level=get_risk_level(row[6]),
                days_ago=calculate_days_ago(row[4])
            )
            channels.append(channel)
        
        # Calculate statistics
        cursor.execute("SELECT avg_prob, first_seen FROM suspicious_channels")
        all_channels = cursor.fetchall()
        
        total_flagged = len(all_channels)
        high_risk = len([ch for ch in all_channels if ch[0] >= 0.8])
        medium_risk = len([ch for ch in all_channels if 0.6 <= ch[0] < 0.8])
        low_risk = len([ch for ch in all_channels if ch[0] < 0.6])
        
        # Calculate today and this week counts
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        found_today = 0
        found_this_week = 0
        
        for ch in all_channels:
            try:
                ch_date = datetime.fromisoformat(ch[1].replace('Z', '+00:00')).date()
                if ch_date == today:
                    found_today += 1
                if ch_date >= week_ago:
                    found_this_week += 1
            except:
                continue
        
        avg_risk_score = sum([ch[0] for ch in all_channels]) / len(all_channels) if all_channels else 0
        
        stats = TelegramStats(
            total_flagged=total_flagged,
            high_risk=high_risk,
            medium_risk=medium_risk,
            low_risk=low_risk,
            found_today=found_today,
            found_this_week=found_this_week,
            avg_risk_score=round(avg_risk_score, 3)
        )
        
        conn.close()
        
        return TelegramResponse(
            channels=channels,
            stats=stats,
            total_count=total_count
        )
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/stats", response_model=TelegramStats)
async def get_telegram_stats(current_user: dict = Depends(get_current_user)):
    """Get Telegram channels statistics"""
    
    if not os.path.exists(CHANNELS_DB):
        raise HTTPException(status_code=404, detail="Channels database not found")
    
    try:
        conn = sqlite3.connect(CHANNELS_DB)
        cursor = conn.cursor()
        
        cursor.execute("SELECT avg_prob, first_seen FROM suspicious_channels")
        all_channels = cursor.fetchall()
        
        total_flagged = len(all_channels)
        high_risk = len([ch for ch in all_channels if ch[0] >= 0.8])
        medium_risk = len([ch for ch in all_channels if 0.6 <= ch[0] < 0.8])
        low_risk = len([ch for ch in all_channels if ch[0] < 0.6])
        
        # Calculate today and this week counts
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        found_today = 0
        found_this_week = 0
        
        for ch in all_channels:
            try:
                ch_date = datetime.fromisoformat(ch[1].replace('Z', '+00:00')).date()
                if ch_date == today:
                    found_today += 1
                if ch_date >= week_ago:
                    found_this_week += 1
            except:
                continue
        
        avg_risk_score = sum([ch[0] for ch in all_channels]) / len(all_channels) if all_channels else 0
        
        conn.close()
        
        return TelegramStats(
            total_flagged=total_flagged,
            high_risk=high_risk,
            medium_risk=medium_risk,
            low_risk=low_risk,
            found_today=found_today,
            found_this_week=found_this_week,
            avg_risk_score=round(avg_risk_score, 3)
        )
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/channels/{channel_id}")
async def get_channel_details(
    channel_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific channel"""
    
    if not os.path.exists(CHANNELS_DB):
        raise HTTPException(status_code=404, detail="Channels database not found")
    
    try:
        conn = sqlite3.connect(CHANNELS_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM suspicious_channels WHERE id = ?
        """, (channel_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return {
            "id": row[0],
            "channel_username": row[1],
            "channel_id": row[2],
            "channel_title": row[3],
            "first_seen": row[4],
            "sample_size": row[5],
            "avg_prob": row[6],
            "median_prob": row[7],
            "pct90_prob": row[8],
            "reason": row[9],
            "raw_metadata": row[10] if len(row) > 10 else None,
            "risk_level": get_risk_level(row[6]),
            "days_ago": calculate_days_ago(row[4])
        }
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")