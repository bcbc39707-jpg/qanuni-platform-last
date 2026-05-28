from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import aiofiles, os, uuid
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentType
from app.core.config import settings

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), title: str = "", doc_type: DocumentType = DocumentType.OTHER, case_id: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="??? ????? ?????? ????")
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
    return {"id": doc.id, "title": doc.title, "status": "uploaded"}
