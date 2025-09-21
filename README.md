# 🕵️ CyberX — Online Cyber Patrolling & Fraudulent Link Detection

**CyberX** is an automated cyber-patrolling system that continuously **scrapes the web, discovers links, and classifies them** as `benign`, `fraud`, `phishing`, `gambling`, `malware`, or `suspicious`.  
It combines scalable crawling, rule-based heuristics, and modern ML to surface high-risk links and provide human-review tooling.

---

## 🚀 Features
- **Automated Web Crawler**: Surfs the web, scrapes links and page content (Playwright + Scrapy).  
- **Fraud & Gambling Detection**: Ensemble of heuristics + ML (XGBoost + Transformers).  
- **Rule + ML Ensemble**: Fast rules for precision + ML for semantic detection.  
- **Continuous Monitoring**: 24/7 scanning with incremental crawling.  
- **Dashboard & API**: Inspect flagged links, evidence, and confidence scores.  
- **Human-in-the-loop**: Analysts review and provide feedback used for retraining.  
- **Scalable Architecture**: Worker queues, containerized services, and search infra.

---

## 🏗 High-level Architecture

# Goa Police Cyber Patrolling - Complete Directory Structure

```
goa-cyber-patrol/
├── .env                              # Environment variables
├── .gitignore                        # Git ignore file
├── requirements.txt                  # Python dependencies
├── README.md                         # Project documentation
│
├── api/                              # Backend API
│   ├── __init__.py
│   ├── app.py                        # Main FastAPI application
│   ├── config.py                     # Configuration settings
│   │
│   ├── models/                       # ML Models
│   │   ├── __init__.py
│   │   ├── chat_model.py
│   │   └── text_model.py
│   │
│   ├── routers/                      # API Routes
│   │   ├── __init__.py
│   │   ├── auth_router.py            # Authentication endpoints
│   │   ├── chat_router.py            # Chat/Telegram classification
│   │   ├── text_router.py            # Text/Webpage classification
│   │   ├── telegram_router.py        # Telegram data endpoints
│   │   └── webpage_router.py         # Webpage data endpoints
│   │
│   ├── database/                     # Database utilities
│   │   ├── __init__.py
│   │   ├── connection.py             # Database connections
│   │   └── queries.py                # SQL queries
│   │
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       ├── auth.py                   # JWT authentication
│       └── helpers.py                # Common helper functions
│
├── frontend/                         # Frontend files
│   ├── static/                       # Static assets
│   │   ├── css/
│   │   │   └── styles.css           # Custom CSS
│   │   ├── js/
│   │   │   ├── main.js              # Main JavaScript
│   │   │   ├── auth.js              # Authentication handling
│   │   │   └── api.js               # API communication
│   │   └── images/
│   │       └── goa-police-logo.png  # Logo/images
│   │
│   └── templates/                    # HTML templates
│       ├── index.html               # Main dashboard
│       ├── login.html               # Login page (optional)
│       ├── telegram.html            # Telegram channels view
│       └── webpages.html            # Webpages view
│
├── data/                             # Training data
│   ├── sample_labeled.jsonl
│   └── sample_labeled_text.jsonl
│
├── models/                           # ML model training
│   ├── baseline_train.py
│   ├── baseline_train_text.py
│   ├── finetune_transformer.py
│   └── finetuner_text.py
│
├── telethon_scraper/                 # Telegram scraping
│   ├── discover_and_check_modified.py
│   ├── keywords.txt
│   └── suspicious_channels.db        # SQLite DB for channels
│
├── webcrawler/                       # Web crawling
│   ├── crawler.py
│   ├── baseurl.txt
│   └── fraud.db                     # SQLite DB for webpages
│
├── labeling/                         # Data labeling
│   └── labeling_guidelines.md
│
├── utils/                            # Shared utilities
│   └── text_clean.py
│
└── databases/                        # All SQLite databases
    ├── suspicious_channels.db        # Telegram channels
    ├── fraud.db                     # Suspicious webpages
    └── users.db                     # User authentication (new)
```

## Key Integration Points

### 1. **FastAPI Application Structure**
- Main app in `api/app.py` serves both API endpoints and static files
- Separate routers for different functionalities
- Database utilities for SQLite connections

### 2. **Frontend Integration**
- Static files served by FastAPI
- Single-page application with dynamic content loading
- API calls to backend endpoints

### 3. **Database Structure**
- Existing: `suspicious_channels.db`, `fraud.db`
- New: `users.db` for authentication
- Centralized in `databases/` folder

### 4. **Authentication Flow**
- JWT-based authentication
- Session management
- Role-based access control

### 5. **API Endpoints Structure**
```
/api/auth/login          # User authentication
/api/auth/logout         # User logout
/api/telegram/channels   # Get flagged Telegram channels
/api/telegram/stats      # Get Telegram statistics
/api/webpages/pages      # Get flagged webpages
/api/webpages/stats      # Get webpage statistics
/chat/predict            # Existing chat classification
/text/predict            # Existing text classification
```

### 6. **Development vs Production**
- Development: Serve static files via FastAPI
- Production: Use Nginx to serve static files, FastAPI for API only