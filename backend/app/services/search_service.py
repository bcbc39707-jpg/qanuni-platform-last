from elasticsearch import AsyncElasticsearch
from app.core.config import settings
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self.client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
        self.index_laws = "qanuni_laws"
        self.index_rulings = "qanuni_rulings"
        self.index_documents = "qanuni_documents"

    async def create_indices(self):
        arabic_settings = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "arabic_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "arabic_normalization", "arabic_stemmer", "arabic_stop"]
                        }
                    },
                    "filter": {
                        "arabic_stemmer": {"type": "stemmer", "language": "arabic"},
                        "arabic_stop": {"type": "stop", "stopwords": "_arabic_"}
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "arabic_analyzer", "boost": 2.0},
                    "content": {"type": "text", "analyzer": "arabic_analyzer"},
                    "category": {"type": "keyword"},
                    "doc_type": {"type": "keyword"},
                    "law_number": {"type": "keyword"},
                    "year": {"type": "integer"},
                    "court_name": {"type": "keyword"},
                    "created_at": {"type": "date"}
                }
            }
        }

        for index in [self.index_laws, self.index_rulings, self.index_documents]:
            if not await self.client.indices.exists(index=index):
                await self.client.indices.create(index=index, body=arabic_settings)
                logger.info(f"Created index: {index}")

    async def index_law(self, law_id: str, title: str, content: str, law_number: str = None, year: int = None, category: str = None):
        doc = {"title": title, "content": content, "law_number": law_number, "year": year, "category": category, "doc_type": "law"}
        await self.client.index(index=self.index_laws, id=law_id, body=doc)

    async def index_ruling(self, ruling_id: str, title: str, content: str, court_name: str = None, year: int = None, case_type: str = None):
        doc = {"title": title, "content": content, "court_name": court_name, "year": year, "case_type": case_type, "doc_type": "ruling"}
        await self.client.index(index=self.index_rulings, id=ruling_id, body=doc)

    async def index_document(self, doc_id: str, title: str, content: str, doc_type: str = "other"):
        doc = {"title": title, "content": content, "doc_type": doc_type}
        await self.client.index(index=self.index_documents, id=doc_id, body=doc)

    async def search(self, query: str, doc_type: Optional[str] = None, page: int = 1, size: int = 10, filters: Dict = None) -> Dict:
        indices = []
        if doc_type == "law":
            indices = [self.index_laws]
        elif doc_type == "ruling":
            indices = [self.index_rulings]
        elif doc_type == "document":
            indices = [self.index_documents]
        else:
            indices = [self.index_laws, self.index_rulings, self.index_documents]

        body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "content"],
                                "type": "best_fields",
                                "analyzer": "arabic_analyzer"
                            }
                        }
                    ],
                    "filter": []
                }
            },
            "from": (page - 1) * size,
            "size": size,
            "highlight": {
                "fields": {"title": {}, "content": {"fragment_size": 200, "number_of_fragments": 3}},
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            }
        }

        if filters:
            for key, value in filters.items():
                if value:
                    body["query"]["bool"]["filter"].append({"term": {key: value}})

        result = await self.client.search(index=",".join(indices), body=body)

        hits = []
        for hit in result["hits"]["hits"]:
            highlight = hit.get("highlight", {})
            snippet = ""
            if "content" in highlight:
                snippet = " ... ".join(highlight["content"])
            elif "title" in highlight:
                snippet = highlight["title"][0]
            else:
                snippet = (hit["_source"].get("content") or "")[:200]

            hits.append({
                "id": hit["_id"],
                "title": hit["_source"]["title"],
                "snippet": snippet,
                "doc_type": hit["_source"].get("doc_type", "unknown"),
                "score": hit["_score"],
                "source": hit["_index"]
            })

        return {"total": result["hits"]["total"]["value"], "results": hits}

    async def close(self):
        await self.client.close()

search_service = SearchService()
