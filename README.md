# 📚 Patent AI Translation System (JP → ZH)

A **RAG-powered Japanese → Traditional Chinese patent translation system** built on Claude, Gemini, optimized for technical accuracy, terminology consistency, and long-form legal documents.

Built to explore how retrieval and domain knowledge can improve technical translation quality while maintaining consistency, observability, and cost control.
![framework](https://i.imgur.com/l5WKs81.png)

---

## ✨ Key Features

- Patent-domain translation
- RAG (Retrieval-Augmented Generation)
- Terminology management (11,000+ terms)
- Vector search with ChromaDB
- Gemini integration
- Cost & latency monitoring
- REST API with FastAPI

---

## 🏗️ System Architecture (High Level)

### V1 — Translation System

```text
PDF / DOCX
      ↓
Parser
      ↓
RAG Retrieval
      ↓
Terminology Matching
      ↓
Claude Translation
      ↓
DOCX Output
```

**Tech Stack**

```text
FastAPI
Claude Sonnet
ChromaDB
PostgreSQL (Supabase)
Docker
Render
```

---

### V2 — AWS Serverless Platform

```text
React/Vite
      ↓
CloudFront + S3
      ↓
API Gateway
      ↓
Lambda Container
      ↓
ChromaDB + PostgreSQL
      ↓
Gemini
```

**Tech Stack**

```text
React
FastAPI
AWS Lambda
API Gateway
CloudFront
S3
Terraform
Gemini
ChromaDB
PostgreSQL
```

---

## 📊 Dataset

```text
Historical Translations: 1,269
Terminology Entries:    11,112
Vector Coverage:        100%
```

**Domains**

- Semiconductor
- Mechanical
- General

---

## 🌐 API Usage

### Basic Request (No Auth)

```bash
curl -X POST http://localhost:8000/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{
    "japanese_text": "半導体装置の製造方法",
    "domain": "semiconductor",
    "use_rag": true
  }'
```

### Public Endpoints (Always Available)

- `GET /api/v1/health` - Health check
- `GET /api/v1/system/status` - System statistics

## 🔒 Cost Control

RATE_LIMIT_PER_HOUR = 5
MAX_INPUT_CHARS = 3000
DAILY_COST_LIMIT_USD = 1
Monthly Budget = $10

---

## 📬 Contactgia

Built by **Shiki Wen**
