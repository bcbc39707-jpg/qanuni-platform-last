from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db
from app.services.search_service import search_service
from app.services.rag_service import rag_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Qanuni Platform...")
    await init_db()
    try:
        await search_service.create_indices()
        logger.info("Elasticsearch indices ready")
    except Exception as e:
        logger.warning(f"Elasticsearch not available: {e}")
    try:
        await rag_service.init_collection()
        logger.info("Qdrant collection ready")
    except Exception as e:
        logger.warning(f"Qdrant not available: {e}")
    logger.info("Qanuni Platform started successfully!")
    yield
    # Shutdown
    await search_service.close()

app = FastAPI(
    title="Qanuni API",
    description="???? ??????? ????? ???? ???????",
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

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"name": "Qanuni API", "version": "1.0.0", "status": "running", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
