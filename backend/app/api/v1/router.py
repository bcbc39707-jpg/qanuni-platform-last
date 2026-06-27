from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, cases, documents, search, analysis, subscriptions, seed, admin, laws, legal_tree, pdf_parser

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(search.router, prefix="/search", tags=["Legal Search"])
api_router.include_router(laws.router, prefix="/laws", tags=["Laws"])
api_router.include_router(legal_tree.router, prefix="", tags=["Legal Tree"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["AI Analysis & RAG"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
api_router.include_router(seed.router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(pdf_parser.router, prefix="", tags=["PDF Parser"])
