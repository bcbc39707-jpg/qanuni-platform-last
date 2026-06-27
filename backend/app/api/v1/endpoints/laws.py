from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.law import Law
from app.models.legal_part import LegalPart
from app.models.legal_chapter import LegalChapter
from app.models.legal_article import LegalArticle
import json

router = APIRouter()

class ArticleItem(BaseModel):
    article_number: str
    article_title: Optional[str] = None
    article_text: str
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    legal_topics: Optional[List[str]] = None

class ChapterItem(BaseModel):
    title: Optional[str] = None
    articles: List[ArticleItem] = []

class LawDetailResponse(BaseModel):
    id: str
    title: str
    law_number: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    total_articles: int
    articles: List[ArticleItem]
    chapters: List[ChapterItem] = []

class LawListResponse(BaseModel):
    id: str
    title: str
    law_number: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None

@router.get("/", response_model=List[LawListResponse])
async def list_laws(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Law).where(Law.is_active == True)
    if category:
        if category == "law":
            query = query.where(Law.category.notin_(["دستور", "لائحة", "لائحة تنفيذية", "قرار"]))
        elif category == "constitution":
            query = query.where(Law.category == "دستور")
        elif category == "regulation":
            query = query.where(Law.category.in_(["لائحة", "لائحة تنفيذية"]))
        elif category == "decree":
            query = query.where(Law.category.like("%قرار%"))
        else:
            query = query.where(Law.category == category)

    query = query.order_by(Law.year.desc().nullslast(), Law.title).offset(skip).limit(limit)
    result = await db.execute(query)
    laws = result.scalars().all()
    return [
        LawListResponse(
            id=l.id,
            title=l.title,
            law_number=l.law_number,
            year=l.year,
            category=l.category
        ) for l in laws
    ]

@router.get("/{law_id}", response_model=LawDetailResponse)
async def get_law(
    law_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Law).where(Law.id == law_id))
    law = result.scalar_one_or_none()
    if not law:
        raise HTTPException(status_code=404, detail="القانون غير موجود")

    # Fetch structured articles
    articles_result = await db.execute(
        select(LegalArticle)
        .where(LegalArticle.law_id == law_id, LegalArticle.is_active == True)
        .order_by(LegalArticle.sort_order, LegalArticle.article_number)
    )
    db_articles = articles_result.scalars().all()

    # Fetch structured chapters
    chapters_result = await db.execute(
        select(LegalChapter)
        .where(LegalChapter.law_id == law_id)
        .order_by(LegalChapter.sort_order)
    )
    db_chapters = chapters_result.scalars().all()

    articles = []
    articles_by_chapter = {}

    for a in db_articles:
        # Deserialize keywords and topics if present
        keywords_list = []
        if a.keywords:
            try:
                keywords_list = json.loads(a.keywords)
                if not isinstance(keywords_list, list):
                    keywords_list = [keywords_list]
            except Exception:
                keywords_list = [a.keywords]

        topics_list = []
        if a.legal_topics:
            try:
                topics_list = json.loads(a.legal_topics)
                if not isinstance(topics_list, list):
                    topics_list = [topics_list]
            except Exception:
                topics_list = [a.legal_topics]

        art_item = ArticleItem(
            article_number=a.article_number,
            article_title=a.title,
            article_text=a.content,
            summary=a.summary,
            keywords=keywords_list,
            legal_topics=topics_list
        )
        articles.append(art_item)

        if a.chapter_id:
            if a.chapter_id not in articles_by_chapter:
                articles_by_chapter[a.chapter_id] = []
            articles_by_chapter[a.chapter_id].append(art_item)

    chapters_data = []
    
    # Hide chapters wrapper if there is only 1 chapter and it has a placeholder name
    is_placeholder_chapter = len(db_chapters) == 1 and db_chapters[0].title in ["جميع المواد", "كل المواد", "الأحكام العامة", law.title]
    
    if db_chapters and not is_placeholder_chapter:
        for ch in db_chapters:
            ch_articles = articles_by_chapter.get(ch.id, [])
            if ch_articles:
                chapters_data.append(
                    ChapterItem(
                        title=ch.title,
                        articles=ch_articles
                    )
                )

    # Fallback to parsing database full_text/JSON if no structured articles found (safety net)
    if not articles:
        if law.articles and isinstance(law.articles, dict):
            raw_articles = []
            doc_chapters = law.articles.get("chapters", []) or law.articles.get("document", {}).get("chapters", [])
            for ch in doc_chapters:
                for sec in ch.get("sections", []):
                    for art in sec.get("articles", []):
                        raw_articles.append(art)
                for art in ch.get("articles", []):
                    raw_articles.append(art)
            
            for art in raw_articles:
                articles.append(
                    ArticleItem(
                        article_number=str(art.get("article_number", "")),
                        article_title=art.get("article_title"),
                        article_text=art.get("article_text", ""),
                        summary=art.get("summary"),
                        keywords=art.get("keywords", []),
                        legal_topics=art.get("legal_topics", [])
                    )
                )

        if not articles and law.full_text:
            articles.append(
                ArticleItem(
                    article_number="1",
                    article_title=None,
                    article_text=law.full_text,
                    summary=None,
                    keywords=[],
                    legal_topics=[]
                )
            )

    return LawDetailResponse(
        id=law.id,
        title=law.title,
        law_number=law.law_number,
        year=law.year,
        category=law.category,
        total_articles=len(articles),
        articles=articles,
        chapters=chapters_data
    )

