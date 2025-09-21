# api/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import sqlite3
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "goa-police-cyber-patrol-secret-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Database path
USERS_DB = os.getenv("USERS_DB", "databases/users.db")

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

class UserInfo(BaseModel):
    username: str
    full_name: str
    role: str
    badge_number: str

def init_users_db():
    """Initialize users database with default officers"""
    os.makedirs(os.path.dirname(USERS_DB), exist_ok=True)
    
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            badge_number TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Default users with hashed passwords
    default_users = [
        ("officer1", "goa123", "Inspector Rajesh Sharma", "Inspector", "GP001"),
        ("officer2", "cyber456", "Constable Priya Patel", "Constable", "GP002"),
        ("admin", "admin789", "SP Cyber Crime Division", "Superintendent", "GP000"),
        ("cyber_head", "cyber2024", "DySP Cyber Crime", "Deputy Superintendent", "GP003"),
        ("constable1", "duty123", "Constable Amit Singh", "Constable", "GP004")
    ]
    
    for username, password, full_name, role, badge_number in default_users:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (username, password_hash, full_name, role, badge_number, created_at) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password_hash, full_name, role, badge_number, datetime.utcnow().isoformat()))
    
    conn.commit()
    conn.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def authenticate_user(username: str, password: str):
    """Authenticate user credentials"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, password_hash, full_name, role, badge_number, is_active
        FROM users WHERE username = ?
    ''', (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user or not user[5]:  # Check if user exists and is active
        return None
    
    if not verify_password(password, user[1]):
        return None
    
    return {
        "username": user[0],
        "full_name": user[2],
        "role": user[3],
        "badge_number": user[4]
    }

def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def get_current_user(username: str = Depends(verify_token)):
    """Get current authenticated user"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, full_name, role, badge_number
        FROM users WHERE username = ? AND is_active = 1
    ''', (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return {
        "username": user[0],
        "full_name": user[1],
        "role": user[2],
        "badge_number": user[3]
    }

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Authenticate user and return access token"""
    user = authenticate_user(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Update last login
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET last_login = ? WHERE username = ?
    ''', (datetime.utcnow().isoformat(), user["username"]))
    conn.commit()
    conn.close()
    
    # Create access token
    access_token = create_access_token(data={"sub": user["username"]})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_info=user
    )

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserInfo(
        username=current_user["username"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        badge_number=current_user["badge_number"]
    )

@router.post("/logout")
async def logout():
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}

# Initialize database on module load
init_users_db()