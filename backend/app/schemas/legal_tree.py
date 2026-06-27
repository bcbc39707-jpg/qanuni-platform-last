from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class LegalDivisionCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None

class LegalDivisionResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    level: int
    sort_order: int
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    law_count: int = 0

    class Config:
        from_attributes = True

class LegalPartResponse(BaseModel):
    id: str
    law_id: str
    part_number: str
    title: str
    description: Optional[str] = None
    sort_order: int
    chapter_count: int = 0
    article_count: int = 0

    class Config:
        from_attributes = True

class LegalChapterResponse(BaseModel):
    id: str
    part_id: Optional[str] = None
    law_id: Optional[str] = None
    chapter_number: str
    title: str
    description: Optional[str] = None
    sort_order: int
    article_count: int = 0

    class Config:
        from_attributes = True

class LegalArticleResponse(BaseModel):
    id: str
    law_id: str
    part_id: Optional[str] = None
    chapter_id: Optional[str] = None
    article_number: str
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
    keywords: Optional[str] = None
    legal_topics: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True

class LegalArticleCreate(BaseModel):
    article_number: str
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
    keywords: Optional[str] = None
    legal_topics: Optional[str] = None
    sort_order: int = 0

class LegalTreeNodeResponse(BaseModel):
    id: str
    parent_id: Optional[str] = None
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    node_type: str
    level: int
    sort_order: int
    icon: Optional[str] = None
    color: Optional[str] = None
    ref_table: Optional[str] = None
    ref_id: Optional[str] = None
    is_active: bool
    children: List["LegalTreeNodeResponse"] = []

    class Config:
        from_attributes = True

class LegalTreeResponse(BaseModel):
    divisions: List[LegalDivisionResponse]
    tree_nodes: List[LegalTreeNodeResponse]

class LawWithHierarchy(BaseModel):
    id: str
    title: str
    law_number: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    total_articles_count: int = 0
    division: Optional[LegalDivisionResponse] = None
    parts: List[LegalPartResponse] = []

    class Config:
        from_attributes = True

class ArticleSearchResult(BaseModel):
    id: str
    article_number: str
    title: Optional[str] = None
    content: str
    law_id: str
    law_title: str
    part_title: Optional[str] = None
    chapter_title: Optional[str] = None
    score: float = 0.0
