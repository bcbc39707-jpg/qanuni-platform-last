from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.db.session import get_db
from app.api.v1.deps import get_current_user, get_admin_user
from app.models.user import User
from app.models.law import Law
from app.models.legal_division import LegalDivision
from app.models.legal_part import LegalPart
from app.models.legal_chapter import LegalChapter
from app.models.legal_article import LegalArticle
from app.models.legal_tree_node import LegalTreeNode
from app.schemas.legal_tree import (
    LegalDivisionCreate, LegalDivisionResponse,
    LegalPartResponse, LegalChapterResponse, LegalArticleResponse,
    LegalTreeNodeResponse, LegalTreeResponse, LawWithHierarchy
)

router = APIRouter()

@router.get("/legal-tree", response_model=LegalTreeResponse)
async def get_legal_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    divisions_result = await db.execute(
        select(LegalDivision).where(LegalDivision.is_active == True).order_by(LegalDivision.sort_order, LegalDivision.name)
    )
    divisions = divisions_result.scalars().all()

    division_responses = []
    for div in divisions:
        law_count_result = await db.execute(
            select(func.count()).select_from(Law).where(Law.division_id == div.id, Law.is_active == True)
        )
        law_count = law_count_result.scalar() or 0
        division_responses.append(LegalDivisionResponse(
            id=div.id, name=div.name, slug=div.slug,
            description=div.description, level=div.level,
            sort_order=div.sort_order, icon=div.icon, color=div.color,
            parent_id=div.parent_id, is_active=div.is_active,
            created_at=div.created_at, law_count=law_count
        ))

    tree_result = await db.execute(
        select(LegalTreeNode).where(LegalTreeNode.is_active == True, LegalTreeNode.parent_id == None)
        .order_by(LegalTreeNode.sort_order, LegalTreeNode.name)
    )
    root_nodes = tree_result.scalars().all()

    async def build_tree(node: LegalTreeNode) -> LegalTreeNodeResponse:
        children_result = await db.execute(
            select(LegalTreeNode).where(LegalTreeNode.parent_id == node.id, LegalTreeNode.is_active == True)
            .order_by(LegalTreeNode.sort_order, LegalTreeNode.name)
        )
        children = children_result.scalars().all()
        return LegalTreeNodeResponse(
            id=node.id, parent_id=node.parent_id, name=node.name,
            slug=node.slug, description=node.description,
            node_type=node.node_type, level=node.level,
            sort_order=node.sort_order, icon=node.icon, color=node.color,
            ref_table=node.ref_table, ref_id=node.ref_id,
            is_active=node.is_active,
            children=[await build_tree(c) for c in children]
        )

    tree_node_responses = [await build_tree(n) for n in root_nodes]

    return LegalTreeResponse(divisions=division_responses, tree_nodes=tree_node_responses)

@router.get("/divisions", response_model=List[LegalDivisionResponse])
async def list_divisions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(LegalDivision).where(LegalDivision.is_active == True).order_by(LegalDivision.sort_order, LegalDivision.name)
    )
    divisions = result.scalars().all()
    responses = []
    for div in divisions:
        law_count_result = await db.execute(
            select(func.count()).select_from(Law).where(Law.division_id == div.id, Law.is_active == True)
        )
        law_count = law_count_result.scalar() or 0
        responses.append(LegalDivisionResponse(
            id=div.id, name=div.name, slug=div.slug,
            description=div.description, level=div.level,
            sort_order=div.sort_order, icon=div.icon, color=div.color,
            parent_id=div.parent_id, is_active=div.is_active,
            created_at=div.created_at, law_count=law_count
        ))
    return responses

@router.get("/laws/{law_id}/hierarchy", response_model=LawWithHierarchy)
async def get_law_hierarchy(
    law_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Law).where(Law.id == law_id, Law.is_active == True))
    law = result.scalar_one_or_none()
    if not law:
        raise HTTPException(status_code=404, detail="القانون غير موجود")

    division_response = None
    if law.division:
        law_count_result = await db.execute(
            select(func.count()).select_from(Law).where(Law.division_id == law.division.id, Law.is_active == True)
        )
        law_count = law_count_result.scalar() or 0
        division_response = LegalDivisionResponse(
            id=law.division.id, name=law.division.name, slug=law.division.slug,
            description=law.division.description, level=law.division.level,
            sort_order=law.division.sort_order, icon=law.division.icon,
            color=law.division.color, parent_id=law.division.parent_id,
            is_active=law.division.is_active, created_at=law.division.created_at,
            law_count=law_count
        )

    parts_result = await db.execute(
        select(LegalPart).where(LegalPart.law_id == law_id).order_by(LegalPart.sort_order)
    )
    parts = parts_result.scalars().all()
    part_responses = []
    for part in parts:
        chapter_count_result = await db.execute(
            select(func.count()).select_from(LegalChapter).where(LegalChapter.part_id == part.id)
        )
        article_count_result = await db.execute(
            select(func.count()).select_from(LegalArticle).where(LegalArticle.part_id == part.id)
        )
        part_responses.append(LegalPartResponse(
            id=part.id, law_id=part.law_id, part_number=part.part_number,
            title=part.title, description=part.description, sort_order=part.sort_order,
            chapter_count=chapter_count_result.scalar() or 0,
            article_count=article_count_result.scalar() or 0
        ))

    return LawWithHierarchy(
        id=law.id, title=law.title, law_number=law.law_number,
        year=law.year, category=law.category, slug=law.slug,
        description=law.description, total_articles_count=law.total_articles_count or 0,
        division=division_response, parts=part_responses
    )

@router.get("/laws/{law_id}/parts", response_model=List[LegalPartResponse])
async def get_law_parts(
    law_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(LegalPart).where(LegalPart.law_id == law_id).order_by(LegalPart.sort_order)
    )
    parts = result.scalars().all()
    responses = []
    for part in parts:
        ch_count = await db.execute(select(func.count()).select_from(LegalChapter).where(LegalChapter.part_id == part.id))
        art_count = await db.execute(select(func.count()).select_from(LegalArticle).where(LegalArticle.part_id == part.id))
        responses.append(LegalPartResponse(
            id=part.id, law_id=part.law_id, part_number=part.part_number,
            title=part.title, description=part.description, sort_order=part.sort_order,
            chapter_count=ch_count.scalar() or 0, article_count=art_count.scalar() or 0
        ))
    return responses

@router.get("/parts/{part_id}/chapters", response_model=List[LegalChapterResponse])
async def get_part_chapters(
    part_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(LegalChapter).where(LegalChapter.part_id == part_id).order_by(LegalChapter.sort_order)
    )
    chapters = result.scalars().all()
    responses = []
    for ch in chapters:
        art_count = await db.execute(select(func.count()).select_from(LegalArticle).where(LegalArticle.chapter_id == ch.id))
        responses.append(LegalChapterResponse(
            id=ch.id, part_id=ch.part_id, law_id=ch.law_id,
            chapter_number=ch.chapter_number, title=ch.title,
            description=ch.description, sort_order=ch.sort_order,
            article_count=art_count.scalar() or 0
        ))
    return responses

@router.get("/laws/{law_id}/articles", response_model=List[LegalArticleResponse])
async def get_law_articles(
    law_id: str,
    part_id: Optional[str] = Query(None),
    chapter_id: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(LegalArticle).where(LegalArticle.law_id == law_id, LegalArticle.is_active == True)
    if part_id:
        query = query.where(LegalArticle.part_id == part_id)
    if chapter_id:
        query = query.where(LegalArticle.chapter_id == chapter_id)
    query = query.order_by(LegalArticle.sort_order, LegalArticle.article_number).offset(skip).limit(limit)
    result = await db.execute(query)
    articles = result.scalars().all()
    return [
        LegalArticleResponse(
            id=a.id, law_id=a.law_id, part_id=a.part_id, chapter_id=a.chapter_id,
            article_number=a.article_number, title=a.title, content=a.content,
            summary=a.summary, keywords=a.keywords, legal_topics=a.legal_topics,
            sort_order=a.sort_order
        ) for a in articles
    ]

@router.get("/articles/{article_id}", response_model=LegalArticleResponse)
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(LegalArticle).where(LegalArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="المادة غير موجودة")
    return LegalArticleResponse(
        id=article.id, law_id=article.law_id, part_id=article.part_id,
        chapter_id=article.chapter_id, article_number=article.article_number,
        title=article.title, content=article.content, summary=article.summary,
        keywords=article.keywords, legal_topics=article.legal_topics,
        sort_order=article.sort_order
    )

@router.post("/admin/divisions", response_model=LegalDivisionResponse)
async def create_division(
    data: LegalDivisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    division = LegalDivision(**data.model_dump())
    db.add(division)
    await db.commit()
    await db.refresh(division)
    return LegalDivisionResponse(
        id=division.id, name=division.name, slug=division.slug,
        description=division.description, level=division.level,
        sort_order=division.sort_order, icon=division.icon, color=division.color,
        parent_id=division.parent_id, is_active=division.is_active,
        created_at=division.created_at, law_count=0
    )
