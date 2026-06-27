# Qanuni Platform - Project Map

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (HTML/JS)                     │
│  index.html | app.html | search.html | library.html          │
│  dashboard.html | law-viewer.html | generator.html           │
│  analyzer.html | pricing.html | login.html | register.html   │
│  api.js (API client)                                         │
│  styles/ (design-system.css, app.css, homepage.css, etc.)    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (port 3000)
┌──────────────────────────▼──────────────────────────────────┐
│                    Backend (FastAPI Python)                   │
│  /api/v1/auth        → register, login, refresh              │
│  /api/v1/users       → profile, password                     │
│  /api/v1/cases       → CRUD for legal cases                  │
│  /api/v1/documents   → upload, download, OCR                 │
│  /api/v1/laws        → list laws, get law details            │
│  /api/v1/search      → full-text semantic search             │
│  /api/v1/analysis    → RAG query, analyze, draft, PDF        │
│  /api/v1/subscriptions → quotas, plans                       │
│  /api/v1/admin       → users, content, RAG reindex           │
└──────────┬───────────────┬──────────────────┬────────────────┘
           │               │                  │
           ▼               ▼                  ▼
    ┌──────────┐    ┌──────────┐    ┌──────────────────┐
    │PostgreSQL│    │  Redis   │    │   Qdrant (Vector) │
    │ (laws,   │    │ (cache)  │    │   (embeddings)    │
    │  users,  │    └──────────┘    └──────────────────┘
    │  cases)  │
    └──────────┘

## Data Pipeline
PDF Files (laws/ + القوانين الرئيسية/) → extract_laws.py → JSON (legal_data/extracted_json/laws/)
                                                          → Chunks (legal_data/chunks/)
                                                          → Validation Reports (legal_data/extracted_json/validation_reports/)
import_laws_to_db.py → PostgreSQL (laws table)
                     → Qdrant (vector embeddings)

## Legal Data Statistics (Ju 2026)
| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Total laws | 29 | 29 |
| Total articles | 6,305 | 6,195 |
| Constitution articles | 3 | 162 |
| Medical law articles | 1,390 (duplicated) | 43 (actual) |
| Total chunks | 6,518 | 6,050 |

## Database Schema (PostgreSQL)
- users (id, email, phone, hashed_password, full_name, role, is_active, is_verified)
- cases (id, title, description, case_number, case_type, status, court_name, owner_id, lawyer_id)
- documents (id, title, content, doc_type, file_path, file_size, mime_type, ocr_processed, ocr_confidence, case_id, uploaded_by)
- laws (id, title, law_number, year, category, full_text, articles, is_active)
- rulings (id, title, ruling_number, court_name, ruling_date, case_type, summary, full_text, legal_principles)
- subscriptions (id, user_id, plan, status, expires_at, search_quota, analysis_quota, drafting_quota, searches_used, analyses_used, drafts_used)
- payments (id, user_id, subscription_id, amount, currency, provider, status, provider_txn_id, provider_response, paid_at)

## Vector DB (Qdrant)
- Collection: legal_documents
- Embedding dim: 768 (Ollama) / 3072 (OpenAI)
- Chunk metadata: doc_id, title, chunk_index, text, article_number, type
