# برومبت محدّث: استكمال تشغيل منصة "قانوني" على Docker
## النسخة 2 — مع حلول المشاكل التي واجهها الوكيل السابق

> **سياق جديد مهم**: الوكيل السابق (kimi 2.6) حاول تنفيذ البرومبت الأصلي وواجه 5 مشاكل. هذا البرومبت يحلّها كلها. **اقرأه بالكامل قبل البدء**.

---

## 🚨 المشاكل التي واجهها الوكيل السابق + حلولها

### المشكلة 1: Docker Desktop لا يعمل عند البدء
**الحل النهائي**: لا تنتظر Docker Desktop بصمت. استخدم هذه الإجراءات بالترتيب:
```powershell
# 1) تحقق سريع إن كان يعمل
docker info --format "{{.ServerVersion}}" 2>$null
# 2) إذا فشل (exit code 1)، شغّله:
Start-Process -FilePath "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# 3) حلقة انتظار ذكية (تتحقق كل 10 ثوان، أقصى 3 دقائق):
$ok = $false
for ($i = 0; $i -lt 18; $i++) {
    Start-Sleep -Seconds 10
    if (docker info --format "{{.ServerVersion}}" 2>$null) { $ok = $true; break }
}
if (-not $ok) { Write-Output "Docker لم يبدأ بعد 3 دقائق — تابع بأي حال فالبناء يعمل عند الجاهزية" }
```
**ملاحظة**: Docker Desktop على Windows يحتاج 1-3 دقائق عادةً، ليس 5+.

---

### المشكلة 2: لا يوجد build cache (docker images فارغ)
**الحقيقة**: الـ build cache محفوظ في **BuildKit** (`docker buildx`)، **وليس** في `docker images`. الفرق:
- `docker images` = الصور المُكتملة النهائية فقط (فعلاً فارغة لأن البناء لم يكتمل).
- BuildKit cache = الطبقات الوسيطة (الموجودة، 459MB).

**للتحقق من الـ cache الحقيقي**:
```powershell
docker buildx du   # يُظهر حجم build cache (إن كان > 0 فهو موجود)
```

**لكن حتى لو فُقد الـ cache**، البناء من الصفر ممكن. الحل في المشكلة 3.

---

### المشكلة 3: timeout 300 ثانية غير كافٍ للبناء ← هذه أهم مشكلة
**السبب الجذري**: قيد أداة Bash في وكيلك (300s). الحلول المتدرّجة:

#### الحل 3A (المفضّل): تشغيل البناء في الخلفية (detached)
هذا يتجاوز تماماً قيد timeout لأن العملية تستمر بعد انتهاء الاستدعاء:
```powershell
cd "D:\الشريعة - ابي\new22 - Copy - Copy"
# شغّل في الخلفية باستخدام Start-Process (لا يحجب):
Start-Process -FilePath "docker" -ArgumentList "compose","build","backend","frontend" `
    -RedirectStandardOutput "build.log" -RedirectStandardError "build.err" `
    -NoNewWindow -PassThru | Select-Object Id
```
ثم تحقق بشكل دوري:
```powershell
# تحقق إن انتهى (ابحث عن "DONE" أو "ERROR" في build.log):
Get-Content build.log -Tail 20
# أو تحقق من العمليات:
Get-Process docker -ErrorAction SilentlyContinue
```
كرّر التحقق كل 60 ثانية حتى يكتمل.

#### الحل 3B (البديل): بناء منفصل، خدمة واحدة في كل مرة
بناء كل خدمة منفصلة يقلّل المدة لكل استدعاء:
```powershell
docker compose build backend    # ~3-4 دقائق
# ثم بعد نجاحه:
docker compose build frontend   # ~2-3 دقائق
```

#### الحل 3C: تقسيم Dockerfile لتسريع التخزين المؤقت
إن استمر timeout، أضف طبقة `COPY requirements.txt` قبل `RUN pip install` (موجودة فعلاً في backend/Dockerfile ✓). هذا يجعل إعادة البناء بعد الإصلاحات سريعة.

---

### المشكلة 4: PythonRun فشل (docker.exe ليس في PATH)
**الحل**: لا تستخدم PythonRun لتشغيل Docker. استخدم PowerShell مباشرة مع المسار الكامل عند اللزوم:
```powershell
$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
& $docker compose build backend frontend
```
أو فقط `docker compose ...` لأنه عادةً في PATH بعد تثبيت Docker Desktop.

---

### المشكلة 5: نموذج aya:8b غير موجود في Ollama
**الحل الفوري والموصى به**: استخدم **`qwen2.5:3b`** الموجود بالفعل (1.9GB). هو يدعم العربية بشكل جيد.
```powershell
# عدّل ملف .env في الجذر:
# غيّر السطر: OLLAMA_MODEL=aya:8b
# إلى:        OLLAMA_MODEL=qwen2.5:3b
```
**لماذا هذا أفضل الآن**: 
- متوفّر فوراً (لا انتظار سحب 4.8GB).
- أصغر (1.9GB) → أسرع في توليد الإجابات.
- يدعم العربية بشكل مقبول للتجربة.

**خيار البديل (سحب aya:8b في الخلفية أثناء البناء)**:
```powershell
# في الخلفية — لا يحجب:
Start-Process -FilePath "ollama" -ArgumentList "pull","aya:8b" -NoNewWindow
```
لكن **يُنصح بتجاهل aya:8b حالياً** والبدء بـ qwen2.5:3b لتشغيل المنصة أولاً، ثم ترقيتها لاحقاً.

---

## 🎯 الخطة المنفّذة (بترتيب محدّث يتجنّب كل المشاكل)

### الخطوة 0: التحقق من Docker + Ollama
```powershell
docker info --format "{{.ServerVersion}}"   # يجب أن يعطي رقم إصدار
ollama list                                   # يجب أن يظهر nomic-embed-text و qwen2.5:3b
```

### الخطوة 1: تعديل `.env` الجذر لاستخدام qwen2.5:3b
في الملف `D:\الشريعة - ابي\new22 - Copy - Copy\.env`:
- غيّر `OLLAMA_MODEL=aya:8b` → `OLLAMA_MODEL=qwen2.5:3b`
- اترك الباقي كما هو (POSTGRES_PASSWORD=qanuni_secret، SECRET_KEY=yassinalzendany، إلخ).

### الخطوة 2: بناء الحاويات في الخلفية (الحل 3A)
```powershell
cd "D:\الشريعة - ابي\new22 - Copy - Copy"
Start-Process -FilePath "docker" -ArgumentList "compose","build","backend","frontend" `
    -RedirectStandardOutput "build.log" -RedirectStandardError "build.err" `
    -NoNewWindow -PassThru
```
راقب كل 60 ثانية:
```powershell
Get-Content build.log -Tail 25
```
- عند رؤية `=> => writing image` أو `[+] Building ... done` → اكتمل.
- عند رؤية `ERROR:` → اقرأ build.err بالكامل، أصلح، أعِد البناء.

### الخطوة 3: تشغيل قواعد البيانات والخدمات الأساسية
```powershell
cd "D:\الشريعة - ابي\new22 - Copy - Copy"
docker compose up -d postgres redis qdrant
docker compose ps   # انتظر حتى "healthy" لـ postgres و redis
```

### الخطوة 4: تشغيل الـ Backend
```powershell
docker compose up -d backend
# راقب السجلات:
docker compose logs --tail 50 backend
```
- يجب رؤية `Qanuni Platform started successfully!`.
- تحذير `Qdrant not available` مؤقتاً طبيعي.

### الخطوة 5: التحقق من API
```powershell
curl http://localhost:8000/health
# المتوقع: {"status":"healthy"}
curl http://localhost:8000/docs
# المتوقع: صفحة Swagger UI
```

### الخطوة 6: الترحيلات (Alembic)
```powershell
docker compose exec backend alembic upgrade head
```
يجب نجاح 3 ترحيلات. إن فشلت بسبب `yassin07`، تحقق أن `backend/alembic/env.py` يحتوي:
```python
import os
db_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
```

### الخطوة 7: استيراد البيانات القانونية (488 قانون)
```powershell
docker compose exec backend python scripts/import_legal_json_to_postgres.py
```
- اقرأ `backend/scripts/RUNBOOK.md` للتفاصيل.
- تحقق من العدد: يجب أن يُستورد ~487-488 قانوناً.

### الخطوة 8: فهرسة Qdrant (للبحث الدلالي و RAG)
```powershell
# تحقق أولاً من وصول Ollama من الحاوية:
docker compose exec backend curl -s http://host.docker.internal:11434/api/tags
# ثم:
docker compose exec backend python scripts/index_qdrant.py
```
يحتاج `nomic-embed-text` (موجود ✓). قد يستغرق وقتاً (توليد embeddings لكل المواد).

### الخطوة 9: تشغيل الـ Frontend
```powershell
docker compose up -d frontend
docker compose logs --tail 30 frontend
```
- يجب أن يعمل Vite على المنفذ 3000.

### الخطوة 10: الاختبار النهائي
```powershell
docker compose ps   # كل الخدمات "running"
```
- افتح المتصفح: **http://localhost:3000**
- جرّب: التسجيل → تسجيل الدخول → تصفّح المكتبة → البحث → المساعد الذكي.
- مثال سؤال: "ما هي عقوبة السرقة في القانون اليمني؟"

---

## 📋 حالة المشروع الحالية (تحقّق منها أولاً)

### التعديلات الموجودة (لا تكررها):
| الملف | التغيير | تحقق بـ |
|------|---------|---------|
| `frontend/vite.config.js` | `__dirname` → `fileURLToPath(import.meta.url)` | `Select-String "fileURLToPath" frontend\vite.config.js` |
| `backend/alembic/env.py` | قراءة `DATABASE_URL` من البيئة | `Select-String "DATABASE_URL" backend\alembic\env.py` |
| `docker-compose.yml` | حذف `version:`, تعطيل OCR بـ `profiles`, احتفظ بـ `extra_hosts` | `Select-String "profiles" docker-compose.yml` |
| `.dockerignore` (جذر + backend + frontend) | تجاهل venv/node_modules | `Test-Path .dockerignore` |
| `.env` (جذر) | كامل، يحتوي POSTGRES_PASSWORD | `Select-String "POSTGRES_PASSWORD" .env` |

### تحقّق سريع شامل قبل البدء:
```powershell
cd "D:\الشريعة - ابي\new22 - Copy - Copy"
Select-String "fileURLToPath" frontend\vite.config.js
Select-String "DATABASE_URL" backend\alembic\env.py
Select-String "profiles" docker-compose.yml
Test-Path .dockerignore
Test-Path backend\.dockerignore
Test-Path frontend\.dockerignore
Select-String "POSTGRES_PASSWORD" .env
ollama list
docker info --format "{{.ServerVersion}}"
```
كلها يجب أن تعطي نتيجة. إن أعطى أيٌّ منها فارغاً، أصلحه أولاً (راجع البرومبت الأصلي `AI_AGENT_HANDOFF_PROMPT.md`).

---

## 🔧 أخطاء متوقعة وحلولها

| الخطأ | السبب | الحل |
|------|------|-----|
| `weasyprint==68.1` فشل التثبيت | مكتبات نظام ناقصة في backend | أضف `libxml2-dev libxslt-dev zlib1g-dev` لـ `backend/Dockerfile` أو خفّض إلى `weasyprint==60.2` |
| `bcrypt==4.0.1` فشل | ناقص gcc | موجود gcc في Dockerfile ✓، لكن جرّب `bcrypt==4.1.2` إن فشل |
| `pangocairo` مفقود | apt packages | موجودة في Dockerfile ✓ |
| postgres يرفض الاتصال | كلمة سر خاطئة | تحقق `.env`: `POSTGRES_PASSWORD=qanuni_secret` مطابقة لـ docker-compose |
| `Qdrant not available` عند بدء backend | ترتيب الخدمات | طبيعي مؤقتاً؛ ابدأ qdrant قبل backend |
| Ollama غير قابل للوصول من الحاوية | host.docker.internal | تأكد `extra_hosts: host.docker.internal:host-gateway` موجود (✓) |
| Vite خطأ ESM | vite.config.js | تحقق `fileURLToPath` موجود |
| Alembic يتصل بـ `yassin07` | env.py لم يُحدّث | أضف قراءة `DATABASE_URL` من البيئة |

---

## 🚨 قواعد صارمة (مهمة)

1. **لا تخمّن** — اقرأ السجلات كاملة قبل أي إجراء.
2. **استخدم `Start-Process` للعمليات الطويلة** (build، pull، index_qdrant) لتجنّب timeout.
3. **لا تستخدم PythonRun** لتشغيل Docker — استخدم PowerShell مباشرة.
4. **لا تعدّل `.env`** إلا `OLLAMA_MODEL` (إن لزم). وثّق أي تغيير آخر.
5. **لا تحذف build cache** (`docker builder prune`) — البناء يحتاجه.
6. **لا تشغّل OCR** إلا إذا طُلب (ثقيلة جداً).
7. **لا تشغّل `docker compose down -v`** — هذا يمسح بيانات postgres.
8. **جرّب كل خطوة** قبل الانتقال للتالية.
9. **اللغة العربية**: تعامل بحذر مع UTF-8. في PowerShell: `chcp 65001` عند الحاجة.
10. **عند أي خطأ، أصلّحه وأعد المحاولة** — لا تتجاوزه.

---

## ✅ معايير النجاح

- [ ] `qwen2.5:3b` (أو aya:8b إن سُحب) مستخدم في `.env`
- [ ] `docker compose build` يكتمل لـ backend و frontend
- [ ] كل الخدمات (postgres, redis, qdrant, backend, frontend) "running"
- [ ] `curl http://localhost:8000/health` → `{"status":"healthy"}`
- [ ] `alembic upgrade head` ينجح
- [ ] استيراد ~488 قانون إلى PostgreSQL
- [ ] فهرسة Qdrant تكتمل
- [ ] `http://localhost:3000` يفتح في المتصفح
- [ ] التسجيل/الدخول يعمل
- [ ] البحث والمساعد الذكي يعملان

---

## 📂 ملفات لقراءتها أولاً (مرجعية)

1. `backend/scripts/RUNBOOK.md` — دليل التشغيل الرسمي.
2. `.env` (الجذر) — كل المتغيرات.
3. `backend/app/core/config.py` — إعدادات Pydantic.
4. `backend/app/main.py` — نقطة الدخول.
5. `backend/app/api/v1/router.py` — مسارات API.
6. `backend/app/services/rag_service.py` — منطق RAG.
7. `AI_AGENT_HANDOFF_PROMPT.md` — البرومبت الأصلي (للمرجعية).

---

**ابدأ من الخطوة 0 (التحقق الشامل). بالتوفيق!**
