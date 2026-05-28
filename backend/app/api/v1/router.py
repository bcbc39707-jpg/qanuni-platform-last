from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, cases, documents, search, analysis, subscriptions

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(search.router, prefix="/search", tags=["Legal Search"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["AI Analysis & RAG"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
