from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "law": "قانون",
    "ruling": "حكم قضائي",
    "document": "مستند",
    "article": "مادة قانونية",
}

class SearchService:
    MIN_QUERY_LENGTH = 2
    SNIPPET_MAX_LENGTH = 200

    def __init__(self):
        self.models = {}
        self._init_models()

    def _init_models(self):
        from app.models.law import Law
        from app.models.ruling import Ruling
        from app.models.document import Document
        from app.models.legal_article import LegalArticle
        self.models = {
            "law": {"model": Law, "title_field": Law.title, "text_field": Law.full_text, "year_field": getattr(Law, "year", None), "court_field": None, "search_table": "law"},
            "ruling": {"model": Ruling, "title_field": Ruling.title, "text_field": Ruling.full_text, "year_field": None, "court_field": Ruling.court_name, "search_table": "ruling"},
            "document": {"model": Document, "title_field": Document.title, "text_field": Document.content, "year_field": None, "court_field": None, "search_table": "document"},
            "article": {"model": LegalArticle, "title_field": LegalArticle.title, "text_field": LegalArticle.content, "year_field": None, "court_field": None, "search_table": "article"},
        }

    async def search(self, db: AsyncSession, query: str, doc_type: Optional[str] = None, page: int = 1, size: int = 10, filters: Dict = None) -> Dict:
        models_to_search = [self.models[doc_type]] if doc_type and doc_type in self.models else list(self.models.values())
        all_results = []
        total = 0

        if not query or len(query.strip()) < self.MIN_QUERY_LENGTH:
            for entry in models_to_search:
                model = entry["model"]
                stmt = select(model)

                if hasattr(model, "is_active"):
                    stmt = stmt.where(model.is_active == True)

                if filters:
                    if "year" in filters and filters["year"] and entry["year_field"] is not None:
                        stmt = stmt.where(entry["year_field"] == filters["year"])
                    if "court_name" in filters and filters["court_name"] and entry["court_field"] is not None:
                        stmt = stmt.where(entry["court_field"] == filters["court_name"])
                    if "category" in filters and filters["category"] and hasattr(model, "category"):
                        cat_val = filters["category"]
                        if cat_val == "law":
                            stmt = stmt.where(model.category.notin_(["دستور", "لائحة", "لائحة تنفيذية", "قرار"]))
                        elif cat_val == "constitution":
                            stmt = stmt.where(model.category == "دستور")
                        elif cat_val == "regulation":
                            stmt = stmt.where(model.category.in_(["لائحة", "لائحة تنفيذية"]))
                        elif cat_val == "decree":
                            stmt = stmt.where(model.category.like("%قرار%"))
                        else:
                            stmt = stmt.where(model.category == cat_val)
                    if "division_id" in filters and filters["division_id"] and hasattr(model, "division_id"):
                        stmt = stmt.where(model.division_id == filters["division_id"])

                count_stmt = select(func.count()).select_from(stmt.subquery())
                total += (await db.execute(count_stmt)).scalar() or 0

                if hasattr(model, "updated_at"):
                    stmt = stmt.order_by(model.updated_at.desc())
                elif hasattr(model, "created_at"):
                    stmt = stmt.order_by(model.created_at.desc())

                stmt = stmt.offset((page - 1) * size).limit(size)
                db_results = (await db.execute(stmt)).scalars().all()

                for r in db_results:
                    raw_text = (r.full_text if hasattr(r, "full_text") else r.content) or ""
                    title_val = getattr(r, "title", None)
                    if not title_val:
                        title_val = f"المادة ({r.article_number})" if hasattr(r, "article_number") else "وثيقة بدون عنوان"
                    all_results.append({
                        "id": r.id,
                        "title": title_val,
                        "snippet": raw_text[:self.SNIPPET_MAX_LENGTH],
                        "doc_type": entry["search_table"],
                        "score": 0.0,
                        "source": SOURCE_LABELS.get(entry["search_table"], entry["search_table"]),
                    })
            return {"total": total, "results": all_results}

        tsquery = func.plainto_tsquery("arabic", query)

        for entry in models_to_search:
            model = entry["model"]
            text_field = entry["text_field"]
            title_field = entry["title_field"]

            search_vector = func.to_tsvector("arabic", func.concat(func.coalesce(title_field, ""), " ", func.coalesce(text_field, "")))
            ts_rank = func.ts_rank(search_vector, tsquery)

            stmt = select(model, ts_rank).where(search_vector.op("@@", is_comparison=True)(tsquery))

            if hasattr(model, "is_active"):
                stmt = stmt.where(model.is_active == True)

            if filters:
                if "year" in filters and filters["year"] and entry["year_field"] is not None:
                    stmt = stmt.where(entry["year_field"] == filters["year"])
                if "court_name" in filters and filters["court_name"] and entry["court_field"] is not None:
                    stmt = stmt.where(entry["court_field"] == filters["court_name"])
                if "category" in filters and filters["category"] and hasattr(model, "category"):
                    cat_val = filters["category"]
                    if cat_val == "law":
                        stmt = stmt.where(model.category.notin_(["دستور", "لائحة", "لائحة تنفيذية", "قرار"]))
                    elif cat_val == "constitution":
                        stmt = stmt.where(model.category == "دستور")
                    elif cat_val == "regulation":
                        stmt = stmt.where(model.category.in_(["لائحة", "لائحة تنفيذية"]))
                    elif cat_val == "decree":
                        stmt = stmt.where(model.category.like("%قرار%"))
                    else:
                        stmt = stmt.where(model.category == cat_val)
                if "division_id" in filters and filters["division_id"] and hasattr(model, "division_id"):
                    stmt = stmt.where(model.division_id == filters["division_id"])

            count_stmt = select(func.count()).select_from(stmt.subquery())
            total += (await db.execute(count_stmt)).scalar() or 0

            stmt = stmt.order_by(ts_rank.desc()).offset((page - 1) * size).limit(size)
            db_results = (await db.execute(stmt)).all()

            for r, rank in db_results:
                raw_text = (r.full_text if hasattr(r, "full_text") else r.content) or ""
                doc_type_label = entry["search_table"]
                extra = {}
                if doc_type_label == "article":
                    extra["law_id"] = r.law_id
                    extra["article_number"] = r.article_number
                    extra["part_id"] = r.part_id
                    extra["chapter_id"] = r.chapter_id
                
                title_val = getattr(r, "title", None)
                if not title_val:
                    title_val = f"المادة ({r.article_number})" if hasattr(r, "article_number") else "وثيقة بدون عنوان"
                    
                all_results.append({
                    "id": r.id,
                    "title": title_val,
                    "snippet": raw_text[:self.SNIPPET_MAX_LENGTH],
                    "doc_type": doc_type_label,
                    "score": float(rank),
                    "source": SOURCE_LABELS.get(entry["search_table"], entry["search_table"]),
                    **extra,
                })

        return {"total": total, "results": all_results}

    async def rebuild_index(self, db: AsyncSession):
        """Rebuild full-text search GIN indexes for all models."""
        index_definitions = [
            ("idx_laws_full_text_tsv", "laws", "to_tsvector('arabic', COALESCE(full_text, ''))"),
            ("idx_laws_title_tsv", "laws", "to_tsvector('arabic', COALESCE(title, ''))"),
            ("idx_rulings_full_text_tsv", "rulings", "to_tsvector('arabic', COALESCE(full_text, ''))"),
            ("idx_documents_content_tsv", "documents", "to_tsvector('arabic', COALESCE(content, ''))"),
        ]
        for idx_name, table, tsvec_expr in index_definitions:
            try:
                await db.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} USING GIN ({tsvec_expr})"))
                await db.execute(text(f"REINDEX INDEX {idx_name}"))
                logger.info(f"Rebuilt GIN index {idx_name} on {table}")
            except Exception as e:
                logger.warning(f"Failed to rebuild index {idx_name}: {e}")

        for entry in self.models.values():
            model = entry["model"]
            try:
                stmt = select(model)
                results = (await db.execute(stmt)).scalars().all()
                logger.info(f"Rebuild index: {entry['search_table']} - {len(results)} records verified")
            except Exception as e:
                logger.error(f"Rebuild index failed for {entry['search_table']}: {e}")

    async def close(self):
        pass

search_service = SearchService()
