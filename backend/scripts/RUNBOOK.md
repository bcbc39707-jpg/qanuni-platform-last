# دليل تشغيل منصة "قانوني" — استيراد البيانات وفهرسة Qdrant

## 📋 نظرة عامة

هذا الدليل يشرح خطوات إنهاء مشروع منصة "قانوني" القانونية اليمنية، بعد التوقف عند مرحلة **استيراد JSON إلى PostgreSQL**.

## 🗂️ الملفات المُنشأة

| الملف | المسار | الوظيفة |
|-------|--------|---------|
| `import_legal_json_to_postgres.py` | `backend/scripts/` | استيراد JSON → PostgreSQL + بناء الشجرة الهيكلية |
| `index_qdrant.py` | `backend/scripts/` | فهرسة المواد في Qdrant للبحث الدلالي |
| `full_pipeline.py` | `backend/scripts/` | سكربت شامل يربط الاستيراد + الفهرسة + التحقق |
| `rag_service.py` (مُحدَّث) | `backend/app/services/` | ضبط System Prompt لمنع التأليف |

## ⚙️ المتطلبات

1. **Docker Desktop** مثبّت ويعمل
2. **Docker Compose** متاح
3. **Ollama** (اختياري) لتوليد Embeddings محلياً
4. **مفتاح OpenAI** (إذا لم يكن Ollama متاحاً)

## 🚀 الخطوات

### الخطوة 1: تشغيل Docker Compose

```bash
cd "D:\الشريعة - ابي\new22"

# التأكد من وجود .env
cp .env.example .env

# تعديل .env — إضافة POSTGRES_PASSWORD و SECRET_KEY
# POSTGRES_PASSWORD=your_strong_password
# SECRET_KEY=your_32_char_secret_key
# OPENAI_API_KEY=sk-... (إذا كنت تستخدم OpenAI)

# تشغيل الحاويات
docker-compose up -d --build

# التحقق من أن جميع الحاويات تعمل
docker-compose ps
```

الحاويات المطلوبة:
- `qanuni-postgres` (PostgreSQL)
- `qanuni-qdrant` (Qdrant)
- `qanuni-redis` (Redis)
- `qanuni-backend` (FastAPI)
- `qanuni-frontend` (Vite)
- `qanuni-ocr` (OCR)

### الخطوة 2: تأكيد إنشاء الجداول

```bash
# دخول حاوية Backend
docker-compose exec backend bash

# تشغيل Alembic migrations
alembic upgrade head

# الخروج
exit
```

### الخطوة 3: استيراد البيانات إلى PostgreSQL

```bash
# دخول حاوية Backend
docker-compose exec backend bash

# تشغيل سكربت الاستيراد
python scripts/import_legal_json_to_postgres.py

# الخروج
exit
```

**ما يفعله السكربت:**
1. يحذف البيانات القديمة (بيانات فقط، لا الجداول)
2. يبني 13 تصنيف قانوني من `index.json` (LegalDivisions + LegalTreeNodes)
3. يستورد 487 ملف JSON إلى:
   - `laws` (القوانين)
   - `legal_parts` (الكتب)
   - `legal_chapters` (الأبواب/الفصول)
   - `legal_articles` (المواد)
4. يربط كل قانون بشجرة التصنيفات
5. يحوّل الأرقام العربية إلى غربية
6. ينظّف النصوص من الكشيدة والمسافات غير المرئية

### الخطوة 4: فهرسة Qdrant

```bash
# دخول حاوية Backend
docker-compose exec backend bash

# تشغيل سكربت الفهرسة
python scripts/index_qdrant.py

# الخروج
exit
```

**ما يفعله السكربت:**
1. يعيد إنشاء Collection في Qdrant
2. يحمل كل المواد من PostgreSQL
3. يولّد Embeddings (Ollama nomic-embed-text أو OpenAI)
4. يرفع النقاط إلى Qdrant في دفعات

**ملاحظة:** إذا كنت تستخدم Ollama، تأكد من تشغيله:
```bash
ollama pull nomic-embed-text
ollama serve
```

### الخطوة 5: التحقق من السلامة

```bash
# دخول حاوية Backend
docker-compose exec backend bash

# تشغيل السكربت الشامل
python scripts/full_pipeline.py

# أو التحقق اليدوي
python check_db.py
```

### الخطوة 6: اختبار النظام

1. افتح المتصفح: `http://localhost:3000`
2. سجّل الدخول
3. اذهب إلى **المساعد القانوني الذكي**
4. اطرح سؤالاً مثل: "ما هي عقوبة السرقة في القانون اليمني؟"
5. تحقق من:
   - ✅ الإجابة تستند إلى نصوص قانونية
   - ✅ الاستشهاد بـ `🏛️ اسم القانون — المادة (رقم)`
   - ✅ الرابط ينقلك إلى `law-viewer.html` مع التمرير للمادة
   - ✅ عند السؤال خارج نطاق القاعدة، يرفض التأليف

## 📊 التحقق من المعايير

- [ ] قاعدة البيانات القديمة محذوفة بالكامل (بيانات فقط)
- [ ] 487 قانون/وثيقة مُدخلة
- [ ] الشجرة الهيكلية القانونية مبنية بشكل صحيح (13 تصنيف + الجذر)
- [ ] جميع المواد مفهرسة في Qdrant
- [ ] النصوص نظيفة 100% من الأخطاء الإملائية والتنسيقية
- [ ] نظام RAG يعمل بصرامة — لا تأليف ولا اختراع
- [ ] المصادر المرجعية تعرض اسم القانون ورقم المادة بوضوح
- [ ] التنقل المباشر للمادة عند النقر على المصدر يعمل بسلاسة
- [ ] جميع حاويات Docker تعمل بشكل مستقر

## 🔧 استكشاف الأخطاء

### مشكلة: Docker لا يعمل
```bash
# تأكد من تشغيل Docker Desktop
# أو استخدم Docker Engine إذا كنت على Linux
sudo systemctl start docker
```

### مشكلة: PostgreSQL غير متاح
```bash
# التحقق من سجلات الحاوية
docker-compose logs postgres

# التحقق من صحة الاتصال
docker-compose exec postgres pg_isready -U qanuni -d qanuni_db
```

### مشكلة: Qdrant غير متاح
```bash
# التحقق من سجلات الحاوية
docker-compose logs qdrant

# التحقق من الصحة
curl http://localhost:6333/healthz
```

### مشكلة: Embeddings بطيئة أو تفشل
- إذا كنت تستخدم Ollama: تأكد من تشغيل `ollama serve` وإن `nomic-embed-text` محمل
- إذا كنت تستخدم OpenAI: تأكد من صحة `OPENAI_API_KEY`
- يمكن تقليل `MAX_CONCURRENT_EMBEDDINGS` في `index_qdrant.py` إذا كان Ollama بطيئاً

### مشكلة: خطأ في ترميز النصوص العربية
```bash
# في Windows Git Bash، قد تحتاج لتعيين:
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8
```

## 📞 ملاحظات مهمة

1. **لا تتعامل مع تطبيق الأندرويد** — هو خارج نطاق المهمة
2. **لا تخمّن أو تفترض بنية أي قانون** — اعتمد فقط على البيانات في ملفات JSON
3. **لا تترك أي خطأ إملائي أو تنسيقي** — النصوص نظيفة بالفعل عبر `clean_text()`
4. **إذا واجهت مشكلة لا تستطيع حلها** — أبلغ عنها بوضوح بدلاً من تجاوزها

## ✅ النجاح

عند اكتمال جميع الخطوات، ستكون منصة "قانوني" جاهزة للاستخدام مع:
- 487 وثيقة قانونية يمنية مُدخلة
- 13 تصنيف قانوني هرمي
- بحث دلالي ذكي عبر Qdrant
- مساعد RAG صارم لا يُؤلّف المعلومات
- مصادر مرجعية قابلة للنقر
