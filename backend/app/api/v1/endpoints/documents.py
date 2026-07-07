from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import aiofiles, os, uuid, logging
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentType
from app.models.subscription import Subscription
from app.core.config import settings
from app.services.ocr_orchestrator import ocr_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()

class DocumentResponse(BaseModel):
    id: str
    title: str
    doc_type: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    ocr_processed: bool = False
    ocr_confidence: Optional[float] = None
    ocr_method: Optional[str] = None
    case_id: Optional[str] = None
    created_at: Optional[datetime] = None

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(case_id: Optional[str] = None, skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Document).where(Document.uploaded_by == current_user.id)
    if case_id:
        query = query.where(Document.case_id == case_id)
    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return [
        DocumentResponse(
            id=d.id, title=d.title, doc_type=d.doc_type.value,
            file_size=d.file_size, mime_type=d.mime_type,
            ocr_processed=d.ocr_processed, ocr_confidence=d.ocr_confidence,
            ocr_method=d.ocr_method, case_id=d.case_id, created_at=d.created_at,
        )
        for d in result.scalars().all()
    ]

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    if doc.uploaded_by != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="لا تملك صلاحية الوصول لهذا المستند")
    return DocumentResponse(id=doc.id, title=doc.title, doc_type=doc.doc_type.value, file_size=doc.file_size, mime_type=doc.mime_type, ocr_processed=doc.ocr_processed, ocr_confidence=doc.ocr_confidence, ocr_method=doc.ocr_method, case_id=doc.case_id, created_at=doc.created_at)

@router.get("/{doc_id}/download")
async def download_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    if doc.uploaded_by != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="لا تملك صلاحية تنزيل هذا المستند")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="ملف المستند غير موجود على الخادم")
    return FileResponse(doc.file_path, media_type=doc.mime_type or "application/octet-stream", filename=doc.title)

@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    if doc.uploaded_by != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="لا تملك صلاحية حذف هذا المستند")
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)
    await db.commit()
    return {"status": "success", "detail": "تم حذف المستند بنجاح"}

ALLOWED_MIME_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/tiff",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "text/csv",
}

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), title: str = "", doc_type: DocumentType = DocumentType.OTHER, case_id: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="حجم الملف يتجاوز الحد المسموح")
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"نوع الملف {file.content_type} غير مسموح")
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, file_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    doc = Document(title=title or file.filename, doc_type=doc_type, file_path=file_path, file_size=len(content), mime_type=file.content_type, case_id=case_id, uploaded_by=current_user.id)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    try:
        ocr_result = await ocr_orchestrator.process_document(file_path, doc.id)
        if ocr_result.get("text"):
            doc.content = ocr_result["text"]
            doc.ocr_processed = True
            doc.ocr_confidence = ocr_result.get("confidence")
            doc.ocr_method = ocr_result.get("method")
            await db.commit()
            logger.info(f"OCR processed for document {doc.id}: method={ocr_result.get('method')}, confidence={ocr_result.get('confidence')}")
    except Exception as e:
        logger.warning(f"OCR failed for document {doc.id}: {e}")
    return {"id": doc.id, "title": doc.title, "status": "uploaded", "ocr_processed": doc.ocr_processed, "ocr_confidence": doc.ocr_confidence, "ocr_method": doc.ocr_method}

@router.post("/{doc_id}/reprocess-advanced")
async def reprocess_document_advanced(doc_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    if doc.uploaded_by != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="لا تملك صلاحية الوصول لهذا المستند")
    sub_result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = sub_result.scalar_one_or_none()
    if not sub or sub.advanced_ocr_used >= sub.advanced_ocr_quota:
        raise HTTPException(status_code=403, detail="لقد استنفذت حصة المسح المتقدم الشهرية. قم بترقية خطتك")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="ملف المستند غير موجود على الخادم")
    try:
        ocr_result = await ocr_orchestrator.process_advanced(doc.file_path, doc.id)
        if ocr_result.get("text"):
            doc.content = ocr_result["text"]
            doc.ocr_processed = True
            doc.ocr_confidence = ocr_result.get("confidence")
            doc.ocr_method = ocr_result.get("method")
            sub.advanced_ocr_used += 1
            await db.commit()
            logger.info(f"Advanced OCR reprocessed for document {doc.id}")
            return {"status": "success", "ocr_processed": True, "ocr_confidence": doc.ocr_confidence, "ocr_method": doc.ocr_method, "advanced_ocr_left": max(0, sub.advanced_ocr_quota - sub.advanced_ocr_used)}
        raise HTTPException(status_code=500, detail="فشل المسح المتقدم للمستند")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Advanced OCR failed", exc_info=e)
        raise HTTPException(status_code=500, detail="خطأ في المسح المتقدم")
