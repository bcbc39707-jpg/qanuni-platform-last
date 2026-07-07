# Qanuni - Architecture

## Components
- **Backend**: FastAPI (Python 3.11) - REST API
- **Frontend**: Next.js 14 (TypeScript) - RTL Arabic UI
- **Database**: PostgreSQL 16
- **Search**: Elasticsearch 8
- **Vector DB**: Qdrant (RAG)
- **Cache**: Redis 7
- **OCR**: PaddleOCR (Arabic)
- **AI**: OpenAI GPT-4 + LangChain

## APIs: /api/v1/
- /auth - Authentication (JWT)
- /users - User management
- /cases - Case management
- /documents - Document upload/management
- /search - Legal search (Elasticsearch)
- /analysis - AI legal analysis (RAG)

## Roles (RBAC)
- Admin: Full access
- Lawyer: Cases, analysis, drafting
- Client: Search, consult, view
- Reviewer: Review AI outputs
