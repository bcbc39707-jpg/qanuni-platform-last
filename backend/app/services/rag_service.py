import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from typing import List, Dict, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "?", " "]
        )

        self.ollama_base = settings.OLLAMA_BASE_URL.rstrip("/")
        self.ollama_model = settings.OLLAMA_MODEL
        self.ollama_embed_model = settings.OLLAMA_EMBEDDING_MODEL

        if settings.AI_PROVIDER == "ollama":
            self._http = httpx.AsyncClient(timeout=300.0)
            self.llm = None
            self.embeddings = None
            self.embedding_dim = 768
        else:
            self._http = None
            self.embeddings = OpenAIEmbeddings(
                model=settings.OPENAI_EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY
            )
            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1
            )
            self.embedding_dim = 3072

    async def _aembed(self, text: str) -> List[float]:
        if settings.AI_PROVIDER == "ollama":
            resp = await self._http.post(
                f"{self.ollama_base}/api/embed", 
                json={"model": self.ollama_embed_model, "input": text}
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"][0]
        return await self.embeddings.aembed_query(text)

    def _to_ollama_messages(self, messages: list) -> list:
        result = []
        for role, content in messages:
            result.append({"role": "system" if role == "system" else "user", "content": content})
        return result

    async def _achat(self, messages: list) -> str:
        if settings.AI_PROVIDER == "ollama":
            ollama_msgs = self._to_ollama_messages(messages)
            resp = await self._http.post(
                f"{self.ollama_base}/api/chat", 
                json={
                    "model": self.ollama_model, 
                    "messages": ollama_msgs, 
                    "stream": False, 
                    "options": {"temperature": 0.1}
                }
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        
        prompt = ChatPromptTemplate.from_messages(messages)
        resp = await self.llm.ainvoke(prompt.format_messages())
        return resp.content

    async def init_collection(self):
        collections = await self.qdrant.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        if not exists:
            dim = 768 if settings.AI_PROVIDER == "ollama" else 3072
            await self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection: {self.collection_name} (dim={dim})")

    async def ingest_document(self, doc_id: str, title: str, content: str, metadata: Dict = None):
        chunks = self.text_splitter.split_text(content)
        points = []
        for i, chunk in enumerate(chunks):
            embedding = await self._aembed(chunk)
            point_id = str(uuid.uuid4())
            payload = {
                "doc_id": doc_id,
                "title": title,
                "chunk_index": i,
                "text": chunk,
                **(metadata or {})
            }
            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

        if points:
            await self.qdrant.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    async def query(self, question: str, top_k: int = 5, filter_metadata: Dict = None) -> Dict:
        # Hybrid Search: Combine Postgres keyword matching and Qdrant semantic search
        postgres_articles = []
        matched_law_id = None
        article_num_query = None
        
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.legal_article import LegalArticle
            from app.models.law import Law
            from sqlalchemy import select, or_, and_
            import re

            # Extract any digits for article number
            digits = re.findall(r'\d+', question)
            article_num_query = digits[0] if digits else None

            async with AsyncSessionLocal() as db:
                # 1. Detect if a specific law is mentioned in the query (prioritize laws with articles)
                stmt_laws = select(Law.id, Law.title).order_by(Law.total_articles_count.desc())
                db_laws = (await db.execute(stmt_laws)).all()
                
                norm_question = question.lower()
                for char in ["أ", "إ", "آ", "ا", "ى", "ي", "ة", "ه", " ", "-", "_"]:
                    norm_question = norm_question.replace(char, "")
                    
                for law_id, law_title in db_laws:
                    # Strip suffixes on original string first
                    title_clean = law_title.replace("اليمني", "").replace("اليمنية", "").replace("اليمن", "").replace("القانون", "")
                    
                    norm_title = title_clean.lower()
                    for char in ["أ", "إ", "آ", "ا", "ى", "ي", "ة", "ه", " ", "-", "_"]:
                        norm_title = norm_title.replace(char, "")
                    
                    if len(norm_title) > 3 and (norm_title in norm_question or norm_question in norm_title):
                        matched_law_id = law_id
                        break

                # 2. Perform search based on matching parameters
                db_results = []
                if matched_law_id and article_num_query:
                    # Exact article inside exact law
                    stmt = select(LegalArticle, Law).join(Law, LegalArticle.law_id == Law.id).where(
                        LegalArticle.law_id == matched_law_id,
                        LegalArticle.article_number == article_num_query
                    )
                    db_results = (await db.execute(stmt)).all()
                    
                    if not db_results:
                        # Fallback to fuzzy article number inside exact law
                        stmt = select(LegalArticle, Law).join(Law, LegalArticle.law_id == Law.id).where(
                            LegalArticle.law_id == matched_law_id,
                            LegalArticle.article_number.like(f"%{article_num_query}%")
                        )
                        db_results = (await db.execute(stmt)).all()

                if not db_results:
                    # Clean question keywords
                    q = re.sub(r'[^\w\s]', ' ', question)
                    words = q.split()
                    stop_words = {
                        "ما", "هي", "هو", "كيف", "في", "من", "على", "عن", "إلى", "ان", "أن", 
                        "أو", "او", "لا", "الذي", "التي", "القانون", "اليمني", "قانون", "اليمن",
                        "ماذا", "هل", "حقوق", "عقوبة", "عقوبات", "شروط", "أحكام", "احكام", "مادة", "المادة",
                        "المساعد", "القانوني", "الذكي", "ماهو", "نص", "الماده", "رقم", "الاحوال", "الشخصيه",
                        "شخصية", "شخصيه", "أحوال", "احوال"
                    }
                    keywords = [w for w in words if len(w) > 2 and w not in stop_words]
                    if not keywords:
                        keywords = [w for w in words if len(w) > 1]

                    if keywords:
                        conditions = []
                        for kw in keywords:
                            norm_kw = kw.strip()
                            for char in ["أ", "إ", "آ", "ا", "ى", "ي", "ة", "ه"]:
                                norm_kw = norm_kw.replace(char, "%")
                            norm_kw = re.sub(r'%+', '%', norm_kw)
                            conditions.append(LegalArticle.content.like(f"%{norm_kw}%"))

                        if conditions:
                            stmt = select(LegalArticle, Law).join(Law, LegalArticle.law_id == Law.id)
                            
                            # If we matched a law, restrict keywords to that law
                            if matched_law_id:
                                stmt = stmt.where(
                                    LegalArticle.law_id == matched_law_id,
                                    or_(*conditions)
                                )
                            else:
                                stmt = stmt.where(or_(*conditions))
                                
                            stmt = stmt.limit(60)
                            db_results = (await db.execute(stmt)).all()

                # Score and rank results
                scored = []
                is_exact_match = (matched_law_id is not None and article_num_query is not None and len(db_results) > 0)
                
                for art, law in db_results:
                    if is_exact_match:
                        score = 1.0
                    else:
                        matches = 0
                        content_lower = art.content.lower()
                        for kw in keywords:
                            norm_kw = kw.strip()
                            for char in ["أ", "إ", "آ", "ا", "ى", "ي", "ة", "ه"]:
                                norm_kw = norm_kw.replace(char, " ")
                            words_in_kw = [w for w in norm_kw.split() if len(w) > 1]
                            if any(w in content_lower for w in words_in_kw):
                                matches += 1
                        
                        score = matches / len(keywords) if keywords else 0.5
                        # Boost score if the law title matches keywords
                        if not matched_law_id:
                            law_title_lower = law.title.lower()
                            for kw in keywords:
                                if kw in law_title_lower:
                                    score += 0.25
                                    
                    scored.append((art, law, score))

                scored.sort(key=lambda x: x[2], reverse=True)
                postgres_articles = scored[:5]
        except Exception as db_err:
            logger.warning(f"Postgres hybrid search failed: {db_err}")

        context_chunks = []
        sources = []
        seen_articles = set()

        # 1. Add Postgres results first (very high precision)
        for art, law, score in postgres_articles:
            art_num = art.article_number
            key = (law.id, art_num)
            if key not in seen_articles:
                seen_articles.add(key)
                chunk_text = f"من {law.title} (المادة {art_num}):\n{art.content}"
                context_chunks.append(chunk_text)
                sources.append({
                    "doc_id": law.id,
                    "title": law.title,
                    "chunk_index": 0,
                    "article_number": art_num,
                    "score": min(score, 1.0)
                })

        # 2. Add Qdrant results (semantic search fallback/supplement)
        try:
            # If using nomic-embed-text, prefix with search_query:
            embed_q = question
            if settings.AI_PROVIDER == "ollama" and "nomic" in self.ollama_embed_model:
                embed_q = f"search_query: {question}"

            query_embedding = await self._aembed(embed_q)
            
            # Apply filter in Qdrant if a specific law was matched
            qdrant_filter = None
            if matched_law_id:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                qdrant_filter = Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=matched_law_id)
                        )
                    ]
                )

            results = await self.qdrant.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=qdrant_filter,
                limit=top_k
            )

            for result in results.points:
                doc_id = result.payload["doc_id"]
                art_num = result.payload.get("article_number", "")
                chunk_idx = result.payload.get("chunk_index", 0)
                if art_num:
                    key = (doc_id, art_num)
                else:
                    key = (doc_id, chunk_idx)
                
                if key not in seen_articles:
                    seen_articles.add(key)
                    context_chunks.append(result.payload["text"])
                    sources.append({
                        "doc_id": doc_id,
                        "title": result.payload["title"],
                        "chunk_index": chunk_idx,
                        "article_number": art_num,
                        "score": result.score
                    })
        except Exception as q_err:
            logger.warning(f"Qdrant query failed: {q_err}")

        context = "\n\n---\n\n".join(context_chunks)

        messages = [
            ("system", (
                "أنت مساعد قانوني يمني متخصص وصارم. مهمتك الوحيدة هي الإجابة على الأسئلة القانونية بالاعتماد **الحصري** والكامل على النصوص القانونية اليمنية المسترجعة في المعلومات أدناه.\n"
                "قواعد صارمة يجب الالتزام بها:\n"
                "1. **لا تأليف**: لا تخترع أو تؤلف أي قانون، مادة، عقوبة، أو نص قانوني لم يوجد في المعلومات المسترجعة.\n"
                "2. **لا تفسير شخصي**: لا تُعِد صياغة النصوص القانونية ولا تضف تفسيرات شخصية. انقل النص كما هو مع ذكر المصدر.\n"
                "3. **الاستشهاد الإلزامي**: عند الإشارة إلى أي مادة قانونية، يجب أن تذكر بوضوح: 🏛️ اسم القانون — المادة (رقم المادة).\n"
                "4. **الرفع الصريح**: إذا لم تكن المعلومات المسترجعة كافية أو ذات صلة مباشرة بالسؤال، قل بوضوح: 'عذراً، لم أجد إجابة كافية على هذا السؤال في قاعدة البيانات القانونية المتوفرة لدي حالياً.' ولا تُجب بناءً على معلوماتك العامة.\n"
                "5. **لا افتراضات**: لا تفترض أو تخمن أي معلومة غير مذكورة صراحةً في النصوص المسترجعة.\n"
                "6. **الترقيم**: استخدم الأرقام الغربية (0-9) دائماً عند ذكر أرقام المواد.\n"
                "7. **اللغة**: اكتب باللغة العربية الفصحى السليمة.\n"
                "تذكر: أنت لست محامياً عاماً، أنت مساعد استرجاعي يعتمد فقط على النصوص المسترجعة."
            )),
            ("human", f"المعلومات المسترجعة:\n{context}\n\nالسؤال: {question}\n\nيرجى تقديم إجابة قانونية مبنية على المعلومات أعلاه:")
        ]

        answer = await self._achat(messages)

        return {
            "answer": answer,
            "sources": sources,
            "chunks_used": len(context_chunks)
        }

    async def analyze_case(self, case_text: str) -> Dict:
        messages = [
            ("system", "أنت محامٍ خبير في تحليل القضايا. قم بتحليل النص القانوني المقدم مع:\n1. ملخص القضية\n2. المشكلات القانونية الرئيسية\n3. الأحكام والقوانين ذات الصلة\n4. نقاط القوة والضعف لكل طرف\n5. التوصيات القانونية\n6. السيناريوهات المحتملة (صلح/حكم/استئناف)\nكن دقيقاً ومهنياً في تحليلك."),
            ("human", f"نص القضية:\n{case_text}\n\nالتحليل القانوني:")
        ]

        analysis = await self._achat(messages)
        return {"analysis": analysis}

    async def draft_legal_document(self, doc_type: str, context: str, instructions: str = "") -> Dict:
        templates = {
            "claim": "صياغة صحيفة دعوى",
            "defense": "صياغة مذكرة دفاع",
            "memo": "صياغة مذكرة قانونية",
            "contract": "صياغة عقد",
            "appeal": "صياغة استئناف/تمييز"
        }
        doc_name = templates.get(doc_type, "صياغة مستند قانوني")

        # RAG: Search Qdrant for relevant Yemeni laws
        retrieved_laws = ""
        try:
            embed_q = f"{doc_name} {context} {instructions}"
            if settings.AI_PROVIDER == "ollama" and "nomic" in self.ollama_embed_model:
                embed_q = f"search_query: {embed_q}"

            query_embedding = await self._aembed(embed_q)
            search_results = await self.qdrant.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=4
            )
            chunks = []
            for res in search_results.points:
                if res.payload and "text" in res.payload:
                    law_title = res.payload.get("title", "")
                    art_num = res.payload.get("article_number", "")
                    chunk_text = res.payload["text"]
                    chunks.append(f"من {law_title} (المادة {art_num}):\n{chunk_text}")
            
            if chunks:
                retrieved_laws = "\n\n---\n\n".join(chunks)
                logger.info(f"Retrieved {len(chunks)} law chunks for RAG drafting.")
        except Exception as e:
            logger.warning(f"RAG search failed during drafting: {e}")

        system_prompt = (
            f"أنت محامٍ ومستشار قانوني يمني خبير في صياغة المستندات والعقود القضائية والقانونية.\n"
            f"مهمتك هي صياغة {doc_name} بشكل رسمي ومفصل وتجاري/قضائي سليم وفق أحكام القوانين والتشريعات اليمنية المعمول بها.\n"
            f"يجب أن تكون الصياغة متوافقة تماماً مع الأسلوب والصيغ الرسمية المعتمدة في اليمن (مثل البسملة في البداية، والصيغ القضائية التقليدية، وإقرار الأهلية، والبنود الإلزامية).\n"
            f"اعتمد في صياغتك بشكل أساسي على القوانين اليمنية (القانون المدني اليمني، قانون المرافعات والتنفيذ المدني، قانون الإثبات، قانون العمل اليمني) بحسب نوع الوثيقة المطلوبة.\n"
            f"لا تخترع نصوصاً قانونية أو مواد وهمية من رأسك، بل اعتمد على نصوص قانونية ومواد حقيقية ومفصلة.\n"
        )

        if retrieved_laws:
            system_prompt += (
                f"\nفيما يلي نصوص ومواد قانونية يمنية حقيقية ذات صلة تم استرجاعها من قاعدة البيانات القانونية، استعن بها وادمجها أو استشهد بها في الصياغة (مثال: 'وفقاً للمادة (...) من القانون المدني اليمني'):\n"
                f"{retrieved_laws}\n"
            )

        messages = [
            ("system", system_prompt),
            ("human", f"المعلومات المدخلة والخاصة بالأطراف والوثيقة:\n{context}\n\nالتعليمات الإضافية من المستخدم: {instructions}\n\nيرجى صياغة المستند القانوني المطلوب بشكل احترافي وكامل مع الإشارة للمواد والقوانين اليمنية ذات الصلة:")
        ]

        document = await self._achat(messages)
        return {"document": document, "type": doc_type}

    async def close(self):
        if self._http:
            await self._http.aclose()
        await self.qdrant.close()

rag_service = RAGService()
