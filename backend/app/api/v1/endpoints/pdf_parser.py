import os
import re
import json
import tempfile
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.db.session import get_db
from app.api.v1.deps import get_admin_user
from app.models.user import User
from app.models.law import Law
from app.models.legal_division import LegalDivision
from app.models.legal_part import LegalPart
from app.models.legal_chapter import LegalChapter
from app.models.legal_article import LegalArticle
from app.core.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)
router = APIRouter()

PERSIAN_TO_DIGIT = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

PART_PATTERNS = [
    r"الباب\s*(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|الحادي\s*عشر|الثاني\s*عشر|[\d]+)",
    r"الكتاب\s*(الأول|الثاني|الثالث|الرابع|الخامس|[\d]+)",
    r"القسم\s*(الأول|الثاني|الثالث|الرابع|[\d]+)",
]

CHAPTER_PATTERNS = [
    r"الفصل\s*(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|الحادي\s*عشر|[\d]+)",
    r"المبحث\s*(الأول|الثاني|الثالث|الرابع|الخامس|[\d]+)",
    r"الفرع\s*(الأول|الثاني|الثالث|[\d]+)",
]

ARTICLE_PATTERN = r"مادة\s*[\(\[\{]?(\d+)[\)\]\}]?\s*[-\–\:]?\s*"
ARTICLE_WITH_TITLE = r"مادة\s*[\(\[\{]?(\d+)[\)\]\}]?\s*[-\–\:]\s*(.*?)(?=\n|$)"

ARABIC_WORDS = {
    "الأول": "1", "الثاني": "2", "الثالث": "3", "الرابع": "4",
    "الخامس": "5", "السادس": "6", "السابع": "7", "الثامن": "8",
    "التاسع": "9", "العاشر": "10", "الحادي": "11", "الثاني": "12",
}


def arabic_word_to_num(word: str) -> str:
    word = word.strip()
    if word in ARABIC_WORDS:
        return ARABIC_WORDS[word]
    if "عشر" in word:
        parts = word.split()
        if len(parts) == 2 and parts[0] in ARABIC_WORDS:
            base = int(ARABIC_WORDS[parts[0]])
            return str(base + 10) if base <= 2 else str(base * 10)
    digits = re.sub(r"[^\d]", "", word)
    return digits if digits else "0"


def normalize_text(text: str) -> str:
    text = text.translate(PERSIAN_TO_DIGIT)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_metadata(text: str) -> dict:
    meta = {}
    law_num_match = re.search(r"رقم\s*[\(\[\{]?(\d+)[\)\]\}]?\s*ل[سع]نة\s*(\d+)", text)
    if law_num_match:
        meta["law_number"] = law_num_match.group(1)
        meta["year"] = int(law_num_match.group(2))

    year_match = re.search(r"ل[سع]نة\s*(\d{4})", text)
    if year_match and "year" not in meta:
        meta["year"] = int(year_match.group(1))

    title_match = re.search(r"قانون[^\-\(\)]+", text)
    if title_match:
        meta["title"] = title_match.group(0).strip()

    return meta


def find_title(text: str) -> str:
    lines = text.strip().split("\n")
    for line in lines[:20]:
        line = line.strip()
        if line and ("قانون" in line or "دستور" in line or "لائحة" in line):
            return re.sub(r'^\d+[\.\-\:\)\s]+', '', line).strip()
    return lines[0].strip() if lines else "قانون"


def parse_legal_text(text: str) -> dict:
    text = normalize_text(text)
    metadata = extract_metadata(text)
    title = metadata.get("title") or find_title(text)

    segments = []
    pos = 0
    text_len = len(text)

    all_boundaries = []

    for pattern in PART_PATTERNS:
        for m in re.finditer(pattern, text):
            all_boundaries.append((m.start(), "part", m.group()))

    for pattern in CHAPTER_PATTERNS:
        for m in re.finditer(pattern, text):
            all_boundaries.append((m.start(), "chapter", m.group()))

    for m in re.finditer(ARTICLE_PATTERN, text):
        all_boundaries.append((m.start(), "article", m.group()))

    all_boundaries.sort(key=lambda x: x[0])

    if not all_boundaries:
        return {
            "title": title,
            "law_number": metadata.get("law_number"),
            "year": metadata.get("year"),
            "parts": [{
                "part_number": "1",
                "title": "المواد",
                "articles": parse_articles_flat(text)
            }]
        }

    current_part = None
    current_chapter = None
    parts = []

    for i, (boundary_pos, btype, btext) in enumerate(all_boundaries):
        if btype == "part":
            part_title = re.sub(r"(الباب|الكتاب|القسم)\s*", "", btext).strip()
            part_num = arabic_word_to_num(part_title)
            current_part = {
                "part_number": part_num,
                "title": btext.strip(),
                "chapters": [],
                "articles": []
            }
            current_chapter = None
            parts.append(current_part)
        elif btype == "chapter" and current_part is not None:
            ch_title = re.sub(r"(الفصل|المبحث|الفرع)\s*", "", btext).strip()
            ch_num = arabic_word_to_num(ch_title)
            current_chapter = {
                "chapter_number": ch_num,
                "title": btext.strip(),
                "articles": []
            }
            current_part["chapters"].append(current_chapter)
        elif btype == "article":
            art_match = re.match(ARTICLE_WITH_TITLE, text[boundary_pos:boundary_pos + 200])
            art_text_start = boundary_pos
            art_text_end = text_len
            if i + 1 < len(all_boundaries):
                art_text_end = all_boundaries[i + 1][0]

            art_num = re.match(ARTICLE_PATTERN, text[boundary_pos:boundary_pos + 50])
            article_number = art_num.group(1) if art_num else "0"

            article_content = text[art_text_start:art_text_end].strip()

            article_title = None
            if art_match and art_match.group(2):
                article_title = art_match.group(2).strip()

            content_lines = article_content.split("\n", 1)
            article_body = content_lines[1].strip() if len(content_lines) > 1 else article_content

            article_obj = {
                "article_number": article_number,
                "title": article_title,
                "content": article_body
            }

            if current_chapter is not None:
                current_chapter["articles"].append(article_obj)
            elif current_part is not None:
                current_part["articles"].append(article_obj)
            else:
                if not parts:
                    current_part = {
                        "part_number": "1",
                        "title": "المواد العامة",
                        "chapters": [],
                        "articles": []
                    }
                    parts.append(current_part)
                current_part["articles"].append(article_obj)

    return {
        "title": title,
        "law_number": metadata.get("law_number"),
        "year": metadata.get("year"),
        "parts": parts if parts else [{
            "part_number": "1",
            "title": "المواد",
            "articles": parse_articles_flat(text)
        }]
    }


def parse_articles_flat(text: str) -> list:
    articles = []
    for m in re.finditer(ARTICLE_WITH_TITLE, text):
        article_obj = {
            "article_number": m.group(1),
            "title": m.group(2).strip() if m.group(2) else None,
            "content": text[m.end():].split("\n\n")[0].strip() if text[m.end():] else ""
        }
        articles.append(article_obj)
    if not articles:
        articles.append({
            "article_number": "1",
            "title": None,
            "content": text[:1000]
        })
    return articles


@router.post("/admin/parse-pdf")
async def parse_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    division_id: str = Form(...),
    law_title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف PDF فقط")

    division_result = await db.execute(select(LegalDivision).where(LegalDivision.id == division_id))
    division = division_result.scalar_one_or_none()
    if not division:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="حجم الملف يتجاوز الحد المسموح")
    if file.content_type and file.content_type not in ("application/pdf",):
        raise HTTPException(status_code=400, detail="نوع الملف غير مسموح")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            temp_path = tmp.name

        extracted_text = await extract_text_from_pdf(temp_path)

        if not extracted_text or len(extracted_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="لم يتم استخراج نصوص كافية من الملف. قد يحتاج الملف إلى معالجة OCR")

        parsed = parse_legal_text(extracted_text)
        title = law_title or parsed.get("title", file.filename.replace(".pdf", ""))

        result_json = {
            "title": title,
            "law_number": parsed.get("law_number"),
            "year": parsed.get("year"),
            "division_id": division_id,
            "division_name": division.name,
            "total_parts": len(parsed.get("parts", [])),
            "total_articles": sum(
                len(p.get("articles", [])) + sum(
                    len(ch.get("articles", [])) for ch in p.get("chapters", [])
                ) for p in parsed.get("parts", [])
            ),
            "parsed_structure": parsed,
            "raw_text_preview": extracted_text[:2000],
        }

        return {
            "status": "parsed",
            "message": "تم استخراج الهيكل القانوني بنجاح. راجع النتيجة ثم استخدم /admin/confirm-parse للتأكيد",
            "data": result_json
        }

    except Exception as e:
        logger.error("PDF parsing failed", exc_info=e)
        raise HTTPException(status_code=500, detail="فشل معالجة الملف")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/admin/confirm-parse")
async def confirm_parse(
    background_tasks: BackgroundTasks,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    try:
        parsed = data.get("parsed_structure")
        if not parsed:
            raise HTTPException(status_code=400, detail="البيانات غير صالحة")

        title = data.get("title", parsed.get("title", "قانون"))
        division_id = data.get("division_id")

        if not division_id:
            raise HTTPException(status_code=400, detail="معرف التصنيف مطلوب")

        existing = await db.execute(
            select(Law).where(Law.title == title, Law.is_active == True)
        )
        existing_law = existing.scalar_one_or_none()
        if existing_law:
            law_id = existing_law.id
            law = existing_law
            logger.info(f"Updating existing law: {law_id}")
        else:
            law = Law(
                title=title,
                law_number=parsed.get("law_number"),
                year=parsed.get("year"),
                category=data.get("division_name") or data.get("division_id"),
                division_id=division_id,
                slug=re.sub(r'[^\w\s-]', '', title).replace(' ', '-')[:200],
                description=parsed.get("parts", [{}])[0].get("title") if parsed.get("parts") else None,
                is_active=True,
                full_text="",
            )
            db.add(law)
            await db.flush()
            law_id = law.id

        total_articles = 0
        parts_data = parsed.get("parts", [])

        for p_idx, part_data in enumerate(parts_data):
            part = LegalPart(
                law_id=law_id,
                part_number=part_data.get("part_number", str(p_idx + 1)),
                title=part_data.get("title", f"الباب {part_data.get('part_number', p_idx + 1)}"),
                sort_order=p_idx,
            )
            db.add(part)
            await db.flush()

            chapters_data = part_data.get("chapters", [])
            if chapters_data:
                for c_idx, ch_data in enumerate(chapters_data):
                    chapter = LegalChapter(
                        part_id=part.id,
                        law_id=law_id,
                        chapter_number=ch_data.get("chapter_number", str(c_idx + 1)),
                        title=ch_data.get("title", f"الفصل {ch_data.get('chapter_number', c_idx + 1)}"),
                        sort_order=c_idx,
                    )
                    db.add(chapter)
                    await db.flush()

                    for a_idx, art_data in enumerate(ch_data.get("articles", [])):
                        article = LegalArticle(
                            law_id=law_id,
                            part_id=part.id,
                            chapter_id=chapter.id,
                            article_number=art_data.get("article_number", str(a_idx + 1)),
                            title=art_data.get("title"),
                            content=art_data.get("content", ""),
                            sort_order=a_idx,
                        )
                        db.add(article)
                        total_articles += 1
            else:
                for a_idx, art_data in enumerate(part_data.get("articles", [])):
                    article = LegalArticle(
                        law_id=law_id,
                        part_id=part.id,
                        article_number=art_data.get("article_number", str(a_idx + 1)),
                        title=art_data.get("title"),
                        content=art_data.get("content", ""),
                        sort_order=a_idx,
                    )
                    db.add(article)
                    total_articles += 1

        law.total_articles_count = total_articles
        await db.commit()

        background_tasks.add_task(index_law_in_qdrant, law_id, title, parts_data)

        return {
            "status": "success",
            "message": f"تم إدراج القانون بنجاح مع {total_articles} مادة",
            "law_id": law_id,
            "total_articles": total_articles,
        }

    except Exception as e:
        await db.rollback()
        logger.error("Confirm parse failed", exc_info=e)
        raise HTTPException(status_code=500, detail="فشل الإدراج")


async def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        result = "\n\n".join(text_parts)
        if result.strip():
            return result
    except ImportError:
        logger.warning("pdfplumber not available, trying PyPDF2...")
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    try:
        from pypdf import PdfReader
        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except ImportError:
        logger.warning("pypdf not available either")

    raise HTTPException(status_code=500, detail="لا توجد مكتبة لقراءة PDF. يرجى تثبيت pdfplumber أو pypdf")


async def index_law_in_qdrant(law_id: str, title: str, parts_data: list):
    try:
        for part in parts_data:
            for art in part.get("articles", []):
                content = art.get("content", "")
                if content:
                    meta = {
                        "type": "law_article",
                        "law_id": law_id,
                        "article_number": art.get("article_number"),
                        "part_title": part.get("title"),
                    }
                    await rag_service.ingest_document(
                        doc_id=f"{law_id}_art_{art.get('article_number')}",
                        title=f"{title} - مادة {art.get('article_number')}",
                        content=content,
                        metadata=meta
                    )
            for ch in part.get("chapters", []):
                for art in ch.get("articles", []):
                    content = art.get("content", "")
                    if content:
                        meta = {
                            "type": "law_article",
                            "law_id": law_id,
                            "article_number": art.get("article_number"),
                            "part_title": part.get("title"),
                            "chapter_title": ch.get("title"),
                        }
                        await rag_service.ingest_document(
                            doc_id=f"{law_id}_art_{art.get('article_number')}",
                            title=f"{title} - مادة {art.get('article_number')}",
                            content=content,
                            metadata=meta
                        )
        logger.info(f"Indexed law {law_id} in Qdrant")
    except Exception as e:
        logger.error(f"Qdrant indexing failed for law {law_id}: {e}")


@router.post("/admin/parse-ocr-pdf")
async def parse_ocr_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    division_id: str = Form(...),
    law_title: Optional[str] = Form(None),
    use_advanced_ocr: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف PDF فقط")

    division_result = await db.execute(select(LegalDivision).where(LegalDivision.id == division_id))
    division = division_result.scalar_one_or_none()
    if not division:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")

    content = await file.read()
    from app.core.config import settings as app_settings
    if len(content) > app_settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="حجم الملف يتجاوز الحد المسموح")
    if file.content_type and file.content_type not in ("application/pdf",):
        raise HTTPException(status_code=400, detail="نوع الملف غير مسموح")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            temp_path = tmp.name

        is_image_pdf = await check_if_image_pdf(temp_path)

        extracted_text = ""
        if not is_image_pdf:
            extracted_text = await extract_text_from_pdf(temp_path)

        if not extracted_text or len(extracted_text.strip()) < 50:
            ocr_text = await call_ocr_service(temp_path, use_advanced_ocr)
            extracted_text = ocr_text or extracted_text

        if not extracted_text or len(extracted_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="لم يتم استخراج نصوص. قد يكون الملف تالفاً أو غير قابل للقراءة")

        parsed = parse_legal_text(extracted_text)
        title = law_title or parsed.get("title", file.filename.replace(".pdf", ""))

        result_json = {
            "title": title,
            "law_number": parsed.get("law_number"),
            "year": parsed.get("year"),
            "division_id": division_id,
            "division_name": division.name,
            "total_parts": len(parsed.get("parts", [])),
            "total_articles": sum(
                len(p.get("articles", [])) + sum(
                    len(ch.get("articles", [])) for ch in p.get("chapters", [])
                ) for p in parsed.get("parts", [])
            ),
            "parsed_structure": parsed,
            "raw_text_preview": extracted_text[:2000],
        }

        return {
            "status": "parsed",
            "message": "تم استخراج الهيكل القانوني بنجاح",
            "data": result_json
        }

    except Exception as e:
        logger.error("OCR PDF parsing failed", exc_info=e)
        raise HTTPException(status_code=500, detail="فشل معالجة الملف")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


async def check_if_image_pdf(pdf_path: str) -> bool:
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text and len(text.strip()) > 100:
                    return False
        return True
    except Exception:
        return True


async def call_ocr_service(pdf_path: str, advanced: bool = False) -> str:
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=300.0) as client:
            with open(pdf_path, "rb") as f:
                files = {"file": ("document.pdf", f, "application/pdf")}
                if advanced and settings.GOOGLE_VISION_API_KEY:
                    resp = await client.post(
                        f"{settings.PADDLEOCR_URL}/extract-advanced",
                        files=files,
                        params={"google_vision": "true"}
                    )
                else:
                    resp = await client.post(
                        f"{settings.PADDLEOCR_URL}/extract",
                        files=files
                    )
                if resp.status_code == 200:
                    return resp.json().get("text", "")
                logger.warning(f"OCR service returned {resp.status_code}")
                return ""
    except Exception as e:
        logger.error(f"OCR service call failed: {e}")
        return ""
