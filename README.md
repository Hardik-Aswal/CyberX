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

