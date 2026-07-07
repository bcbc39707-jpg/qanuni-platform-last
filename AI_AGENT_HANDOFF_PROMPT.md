# برومبت وكيل ذكاء اصطناعي: استكمال تشغيل منصة "قانوني" على Docker

> **السياق**: هذا البرومبت معدّ لوكيل ذكاء اصطناعي (مثل Claude/Cursor/Copilot) ليُكمل عملية تشغيل منصة "قانوني" القانونية اليمنية محلياً على Docker. وكيل سابق أنجز 70% من العمل ووصل لمرحلة بناء الحاويات التي توقفت بسبب بطء الشبكة. مهمتك أن توصل العمل للنهاية.

---

## 📋 معلومات أساسية

- **مسار المشروع**: `D:\الشريعة - ابي\new22 - Copy - Copy`
- **النظام**: Windows 11 (win32), PowerShell
- **المنصة**: منصة "قانوني" — FastAPI backend + Vite/HTML frontend + PostgreSQL + Redis + Qdrant + Ollama
- **بيانات قانونية**: 488 ملف JSON جاهزة في `legal_data_json/`

---

## ✅ ما تم إنجازه (لا تكرره)

1. **فحص البيئة**: كل الأدوات مثبتة وتعمل:
   - Docker 29.6.1 (daemon يعمل على Linux engine)
   - Node v24.14.1, npm 11.11.0
   - Python 3.13.5
   - Ollama 0.21.0

2. **إصلاح `frontend/vite.config.js`**: استُبدل `__dirname` (غير متاح في ESM) بـ `fileURLToPath(import.meta.url)` — تمّ ✓

3. **إنشاء `.dockerignore`** (في الجذر + `backend/` + `frontend/`): يتجاهل `venv/`, `node_modules/`, `__pycache__`, `.next`, إلخ — تمّ ✓

4. **تعديل `backend/alembic/env.py`**: أصبح يعطي أولوية لمتغير البيئة `DATABASE_URL` بدلاً من القيمة المضمّنة في `alembic.ini` (`yassin07@127.0.0.1`) — تمّ ✓

5. **تعطيل خدمة OCR** في `docker-compose.yml` عبر `profiles: ["ocr"]` (PaddleOCR ثقيلة ~2GB وغير ضرورية للتجربة) — تمّ ✓

6. **حذف `version: '3.8'`** المهمل من docker-compose.yml — تمّ ✓

7. **سحب نموذج `nomic-embed-text`**: اكتمل (274 MB) — تمّ ✓

8. **build cache**: كل الطبقات الأساسية محفوظة في Docker (الصورة الأساسية + apt install + WORKDIR + COPY). البناء يستأنف من `npm install` (frontend) و`apt-get install` (backend).

---

## ⚠️ الحالة الحالية (نقطة التوقف)

- **بناء الحاويات**: توقف بسبب timeout بعد 10 دقائق. وصل لخطوة `RUN npm install` (frontend) و`RUN apt-get update && apt-get install` (backend). كل ما سبقها **CACHED**.
- **سبب البطء**: منافسة سحب نموذج `aya:8b` (4.8GB) على عرض النطاق.
- **`aya:8b`**: ~4% منزّل فقط، لا يزال يسحب في الخلفية.
- **لا توجد صور/حاويات مبنية بعد** (`docker images` فارغ، `docker ps -a` فارغ).
- **ملفات `.env`**: ملف `.env` في الجذر **كامل ويحتوي كل المتغيرات** بما فيها `POSTGRES_PASSWORD=qanuni_secret` و`SECRET_KEY=yassinalzendany`. **لا تعدّله**.

---

## 🎯 المهام المتبقية (ابدأ من هنا)

### المهمة 1: إكمال سحب نموذج aya:8b
```powershell
ollama list   # تحقق أولاً — ربما اكتمل
# إذا لم يكتمل:
ollama pull aya:8b
```
- حجمه ~4.8GB. اصبر حتى يكتمل.
- **بديل إن تعذّر**: استخدم `qwen2.5:3b` (موجود بالفعل، 1.9GB) — لكنه أقل جودة للعربية. في هذه الحالة عدّل `OLLAMA_MODEL=aya:8b` → `OLLAMA_MODEL=qwen2.5:3b` في ملف `.env` الجذر.

### المهمة 2: بناء الحاويات (الإعادة ستكون سريعة من الـ cache)
```powershell
cd "D:\الشريعة - ابي\new22 - Copy - Copy"
docker compose build backend frontend
```
- استخدم timeout طويل (15-20 دقيقة) لأن `npm install` و`pip install -r requirements.txt` يستغرقان وقتاً.
- يجب أن يكتمل بناء كل من `new22-copy-copy-backend` و`new22-copy-copy-frontend` بنجاح.
- **عند الخطأ**: اقرأ السجل كاملاً، حدّد المشكلة، أصلحها، أعد المحاولة. الأخطاء المتوقعة:
  - `weasyprint==68.1` قد يفشل في التثبيت → قد تحتاج إضافة مكتبات نظام للـ backend Dockerfile أو تخفيض الإصدار.
  - `bcrypt==4.0.1` قد يحتاج `gcc` (موجود في Dockerfile).
  - مشاكل ESM في `vite.config.js` → تأكد أن التعديل موجود (`fileURLToPath`).

### المهمة 3: تشغيل الخدمات الأساسية (DB + Redis + Qdrant)
```powershell
docker compose up -d postgres redis qdrant
# انتظر جاهزية postgres:
docker compose ps   # يجب أن يظهر postgres وredis كـ "healthy"
```
- إذا فشل postgres بسبب `POSTGRES_PASSWORD`: تحقق أن ملف `.env` الجذر يحتوي على `POSTGRES_PASSWORD=qanuni_secret`.

### المهمة 4: تشغيل الـ Backend
```powershell
docker compose up -d backend
docker compose logs -f backend   # راقب السجلات
```
- عند بدء التشغيل، الـ backend ينشئ الجداول تلقائياً عبر `Base.metadata.create_all`، ثم يحاول فهرسة Qdrant.
- **خطأ متوقع**: تحذير `Qdrant not available` في أول تشغيل (طبيعي، Qdrant قد لا يكون جاهزاً بعد).
- تحقق أن `/health` يستجيب: `curl http://localhost:8000/health` → `{"status":"healthy"}`.

### المهمة 5: تشغيل الترحيلات (Alembic)
```powershell
docker compose exec backend alembic upgrade head
```
- يجب أن تنجح الترحيلات الثلاثة: `001_initial_schema`, `002_add_ocr_and_advanced_ocr`, `003_add_legal_hierarchy`.
- إذا فشلت بسبب `yassin07` → هذا يعني أن تعديل `env.py` لم يُطبّق؛ تحقق أن `backend/alembic/env.py` يحتوي السطر: `db_url = os.getenv("DATABASE_URL") or ...`.

### المهمة 6: استيراد البيانات القانونية (488 قانون)
```powershell
docker compose exec backend python scripts/import_legal_json_to_postgres.py
```
- هذا السكربت يستورد كل ملفات JSON إلى PostgreSQL (laws, legal_parts, legal_chapters, legal_articles, legal_divisions, legal_tree_nodes).
- اقرأ `backend/scripts/RUNBOOK.md` لتفاصيل أكثر.
- تحقق من النجاح: يجب أن يُستورد ~487-488 قانوناً.

### المهمة 7: فهرسة Qdrant (للبحث الدلالي و RAG)
```powershell
docker compose exec backend python scripts/index_qdrant.py
```
- يحتاج `nomic-embed-text` (موجود ✓) ووصول Ollama. تحقق من الاتصال من داخل الحاوية:
  ```powershell
  docker compose exec backend curl -s http://host.docker.internal:11434/api/tags
  ```
- قد يستغرق وقتاً طويلاً (توليد embeddings لكل المواد).
- **إذا فشل الاتصال بـ Ollama**: تحقق أن `OLLAMA_BASE_URL=http://host.docker.internal:11434` موجود في `.env` وأن `extra_hosts: host.docker.internal:host-gateway` موجود في docker-compose.yml (موجود ✓).

### المهمة 8: تشغيل الـ Frontend
```powershell
docker compose up -d frontend
docker compose logs frontend
```
- يجب أن يعمل Vite على المنفذ 3000.

### المهمة 9: التحقق والاختبار النهائي
```powershell
docker compose ps   # كل الخدمات "running" و"healthy"
curl http://localhost:8000/docs      # توثيق API (Swagger)
curl http://localhost:8000/health    # حالة الـ backend
```
- افتح المتصفح: `http://localhost:3000`
- جرّب: التسجيل ← تسجيل الدخول ← تصفّح المكتبة ← البحث ← اطرح سؤالاً على المساعد الذكي مثل: "ما هي عقوبة السرقة في القانون اليمني؟"

---

## 🔧 ملفات تم تعديلها (للمرجعية)

| الملف | التغيير |
|------|---------|
| `frontend/vite.config.js` | `__dirname` → `fileURLToPath(import.meta.url)` |
| `backend/alembic/env.py` | إضافة قراءة `DATABASE_URL` من البيئة |
| `docker-compose.yml` | حذف `version`, تعطيل OCR بـ `profiles`, احتفظ بـ `extra_hosts` |
| `.dockerignore` (جديد) | تجاهل venv/node_modules/__pycache__ |
| `backend/.dockerignore` (جديد) | تجاهل venv محلياً |
| `frontend/.dockerignore` (جديد) | تجاهل node_modules محلياً |

---

## 📌 ملفات مهمة يجب قراءتها أولاً

1. **`backend/scripts/RUNBOOK.md`** — دليل التشغيل الرسمي (استيراد + فهرسة).
2. **`.env`** (الجذر) — كل المتغيرات. **لا تعدّل إلا `OLLAMA_MODEL` إن لزم**.
3. **`backend/app/core/config.py`** — إعدادات Pydantic (Settings).
4. **`backend/app/main.py`** — نقطة الدخول (lifespan, init_db, rag_service.init_collection).
5. **`backend/app/api/v1/router.py`** — مسارات API.
6. **`backend/app/services/rag_service.py`** — منطق RAG (hybrid search).

---

## 🚨 قواعد صارمة

1. **لا تخمّن** — إذا واجهت خطأ، اقرأ السجل كاملاً قبل أي إجراء.
2. **لا تعدّل `.env`** إلا إذا كان هناك سبب قاهر (وثّق السبب).
3. **لا تحذف build cache** النشط — البناء يحتاجه (`docker builder prune` يكسر التقدّم).
4. **لا تشغّل خدمة OCR** إلا إذا طُلب منك صراحةً (ثقيلة جداً).
5. **عند أي خطأ، أصلّحه وأعد المحاولة** — لا تتجاوزه ولا تخفيه.
6. **جرّب كل خطوة** قبل الانتقال للتالية (لا تفترض النجاح).
7. **اللغة**: المشروع عربي — تعامل بحذر مع ترميز UTF-8.

---

## ✅ معايير النجاح

- [ ] `aya:8b` (أو بديل) منزّل في Ollama
- [ ] `docker compose build` يكتمل لـ backend و frontend
- [ ] كل الخدمات (postgres, redis, qdrant, backend, frontend) "running"
- [ ] `curl http://localhost:8000/health` → `{"status":"healthy"}`
- [ ] `alembic upgrade head` ينجح
- [ ] استيراد ~488 قانون إلى PostgreSQL
- [ ] فهرسة Qdrant تكتمل
- [ ] `http://localhost:3000` يفتح في المتصفح
- [ ] التسجيل/الدخول يعمل
- [ ] البحث والمساعد الذكي يعملان

بالتوفيق! ابدأ من المهمة 1.
