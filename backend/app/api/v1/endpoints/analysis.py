from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.v1.deps import get_current_user, check_analysis_quota, check_drafting_quota
from app.models.user import User
from app.models.subscription import Subscription
from app.services.rag_service import rag_service
import os, tempfile, logging

logger = logging.getLogger(__name__)

MAX_EXTRACT_SIZE = 50 * 1024 * 1024

router = APIRouter()

class AnalysisRequest(BaseModel):
    text: str
    analysis_type: str = "general"

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

class DraftRequest(BaseModel):
    doc_type: str
    context: str
    instructions: str = ""

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    chunks_used: int

@router.post("/analyze")
async def analyze_legal_text(data: AnalysisRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), sub: Subscription = Depends(check_analysis_quota)):
    try:
        result = await rag_service.analyze_case(data.text)
        sub.analyses_used += 1
        await db.commit()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analysis failed", exc_info=e)
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

@router.post("/query", response_model=QueryResponse)
async def query_legal(data: QueryRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), sub: Subscription = Depends(check_analysis_quota)):
    try:
        result = await rag_service.query(data.question, top_k=data.top_k)
        sub.analyses_used += 1
        await db.commit()
        return QueryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Query failed", exc_info=e)
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

@router.post("/draft")
async def draft_document(data: DraftRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), sub: Subscription = Depends(check_drafting_quota)):
    try:
        result = await rag_service.draft_legal_document(data.doc_type, data.context, data.instructions)
        sub.drafts_used += 1
        await db.commit()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Drafting failed", exc_info=e)
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

from fastapi.responses import Response

class DraftToPdfRequest(BaseModel):
    text: str
    title: str = "مستند قانوني"
    doc_type: str = "document"

@router.post("/draft-to-pdf")
async def draft_to_pdf(data: DraftToPdfRequest):
    try:
        from weasyprint import HTML
        import html as html_mod

        type_labels = {"claim": "صحيفة دعوى", "defense": "مذكرة دفاع", "memo": "مذكرة قانونية", "contract": "عقد", "appeal": "استئناف / تمييز"}
        label = type_labels.get(data.doc_type, "مستند قانوني")

        lines_html = ""
        for line in data.text.split("\n"):
            stripped = line.strip()
            if not stripped:
                lines_html += "<br/>"
            else:
                lines_html += f"<p>{html_mod.escape(stripped)}</p>"

        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "assets")
        font_regular = os.path.join(font_dir, "Tajawal-Regular.ttf")
        font_bold = os.path.join(font_dir, "Tajawal-Bold.ttf")

        font_face = ""
        body_font = "sans-serif"
        title_font = "sans-serif"
        if os.path.exists(font_regular) and os.path.exists(font_bold):
            font_face = f"""
                @font-face {{ font-family: 'Tajawal'; src: url('file:///{font_regular}'); }}
                @font-face {{ font-family: 'Tajawal-Bold'; src: url('file:///{font_bold}'); }}
            """
            body_font = "Tajawal, sans-serif"
            title_font = "Tajawal-Bold, sans-serif"

        html_str = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
{font_face}
<style>
  @page {{ size: A4; margin: 2cm; }}
  body {{ font-family: {body_font}; font-size: 12pt; line-height: 1.6; }}
  h1 {{ font-family: {title_font}; font-size: 18pt; text-align: center; margin-bottom: 0.5cm; }}
  .meta {{ text-align: left; font-size: 10pt; margin-bottom: 1cm; }}
  p {{ text-align: justify; margin: 0.2cm 0; }}
</style>
</head>
<body>
<h1>{html_mod.escape(data.title)}</h1>
<div class="meta">{html_mod.escape(label)}</div>
{lines_html}
</body>
</html>"""

        pdf_bytes = HTML(string=html_str).write_pdf()
        return Response(content=pdf_bytes, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{data.title}.pdf"'})
    except Exception as e:
        logger.error("PDF generation failed", exc_info=e)
        raise HTTPException(status_code=500, detail="فشل إنشاء PDF")

@router.post("/extract-text")
async def extract_text_from_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "file")[1].lower()
    content_bytes = await file.read()
    if len(content_bytes) > MAX_EXTRACT_SIZE:
        raise HTTPException(status_code=413, detail="حجم الملف يتجاوز الحد المسموح (50MB)")
    text = ""

    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            method = "pdf"
        elif ext == ".docx":
            from docx import Document
            import io
            doc = Document(io.BytesIO(content_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
            method = "docx"
        elif ext == ".txt":
            text = content_bytes.decode("utf-8", errors="replace")
            method = "txt"
        else:
            raise HTTPException(status_code=400, detail=f"نوع الملف {ext} غير مدعوم. استخدم PDF, DOCX, أو TXT")
    except Exception as e:
        logger.error("Text extraction failed", exc_info=e)
        raise HTTPException(status_code=500, detail="فشل استخراج النص")

    if not text.strip():
        raise HTTPException(status_code=400, detail="لم يتم استخراج أي نص من الملف. قد يكون الملف فارغاً أو محمياً بكلمة مرور")

    return {"text": text, "method": method, "filename": os.path.basename(file.filename or "file")}

@router.post("/ingest")
async def ingest_document(doc_id: str, title: str, content: str, metadata: dict = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.value not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")
    try:
        chunks_count = await rag_service.ingest_document(doc_id, title, content, metadata)
        return {"status": "success", "chunks_indexed": chunks_count}
    except Exception as e:
        logger.error("Document ingestion failed", exc_info=e)
        raise HTTPException(status_code=500, detail="فشل إدراج المستند")
