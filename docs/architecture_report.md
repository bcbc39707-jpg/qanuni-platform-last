# Architecture Report

## System Architecture
- **Frontend**: Static HTML + Vanilla JS (SPA-like with multiple pages)
- **Backend**: FastAPI (Python) with async SQLAlchemy
- **Database**: PostgreSQL 16 with pgvector extension
- **Vector DB**: Qdrant for semantic search embeddings
- **Cache**: Redis
- **AI**: Ollama (local) or OpenAI API for embeddings + chat
- **OCR**: PaddleOCR + Google Vision API
- **Containerization**: Docker Compose

## Component Interaction
Frontend (port 3000) → Backend API (port 8000) → PostgreSQL (5432), Redis (6379), Qdrant (6333)

## Data Flow
PDF → extract_laws.py → JSON files → import_laws_to_db.py → PostgreSQL + Qdrant

## Key Observations
1. Frontend uses vanilla JS with static HTML (no framework like React/Vue)
2. Backend uses modern async Python with clean separation
3. Database migrations/seeds are empty (tables created via SQLAlchemy create_all)
4. Full-text search uses PostgreSQL tsvector but without proper indexes
