from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db
from app.services.rag_service import rag_service
import logging
import time
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMITS: dict[str, int] = {
    "/api/v1/auth/login": 5,
    "/api/v1/auth/register": 3,
    "/api/v1/auth/forgot-password": 2,
    "/api/v1/auth/reset-password": 5,
    "/api/v1/auth/verify-email": 5,
    "/api/v1/auth/refresh": 10,
}

async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in _RATE_LIMITS:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60
        max_requests = _RATE_LIMITS[path]
        _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if now - t < window]
        if len(_rate_limit_store[client_ip]) >= max_requests:
            return JSONResponse(status_code=429, content={"detail": "طلبات كثيرة جداً. حاول بعد دقيقة"})
        _rate_limit_store[client_ip].append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Qanuni Platform...")
    await init_db()
    try:
        await rag_service.init_collection()
        logger.info("Qdrant collection ready")
    except Exception as e:
        logger.warning(f"Qdrant not available: {e}")
    logger.info("Qanuni Platform started successfully!")
    yield
    logger.info("Shutting down Qanuni Platform...")
    await rag_service.close()

app = FastAPI(
    title="Qanuni API",
    description="منصة قانوني للبحث القانوني الذكي",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(rate_limit_middleware)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"name": "Qanuni API", "version": "1.0.0", "status": "running", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
