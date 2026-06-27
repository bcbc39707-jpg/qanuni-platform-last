# منصة قانوني الشاملة (Qanuni Platform)
## وثائق المشروع — كل ما تحتاج معرفته

---

## نظرة عامة عن المنصة

**اسم المشروع:** Qanuni / قانوني
**الوصف:** منصة قانونية متكاملة تهدف إلى تسهيل الوصول إلى المعلومات القانونية
**المستودع:** https://github.com/bcbc39707-jpg/qanuni-platform
**الحالة:** قيد التطوير — الإصدار 1-3 قيد العمل

---

## هيكلة المشروع (Architecture)

### المكونات الرئيسية:

`
qanuni-platform/
+-- backend/           ← FastAPI (Python 3.11) — خادم API
¦   +-- app/
¦   ¦   +-- api/v1/    ← نقاط API
¦   ¦   +-- core/      ← إعدادات أساسية
¦   ¦   +-- db/        ← قاعدة البيانات (SQLAlchemy)
¦   ¦   +-- models/    ← نماذج البيانات
¦   ¦   +-- services/  ← خدمات (مثل RAG و AI)
¦   +-- Dockerfile
¦   +-- requirements.txt
+-- frontend/          ← Next.js 14 (TypeScript + Tailwind)
¦   +-- src/
¦   ¦   +-- app/       ← صفحات التطبيق
¦   ¦   +-- components/ ← مكونات واجهة المستخدم
¦   ¦   +-- lib/       ← مكتبات (API client, Auth store)
¦   +-- Dockerfile
¦   +-- package.json
+-- ocr/               ← خدمة OCR (PaddleOCR)
+-- search/            ← محرك البحث Elasticsearch
+-- database/          ← ملفات قاعدة بيانات PostgreSQL
+-- docs/              ← وثائق
+-- docker-compose.yml ← تشغيل متعدد الحاويات
`

### التقنيات المستخدمة:

| التقنية | الإصدار | الغرض |
|--------|---------|-------|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS | SSR، SEO، دعم RTL |
| Backend | FastAPI + Python 3.11 | خادم API غير متزامن، توثيق OpenAPI |
| Database | PostgreSQL 16 | دعم JSON، بحث نصي كامل |
| ORM | SQLAlchemy 2.0 (async) | نوع آمن، ترحيل عبر Alembic |
| Search | Elasticsearch 8 | فهرسة نصوص مع محلل عربي |
| Vector DB | Qdrant | تخزين المتجهات لـ RAG |
| Cache | Redis 7 | تخزين مؤقت، تحديد معدل |
| AI | OpenAI GPT-4 + LangChain | تحليل قانوني ذكي |
| OCR | PaddleOCR | التعرف على النصوص |
| Container | Docker + Docker Compose | نشر سهل |

---

## مخطط قاعدة البيانات

### الجداول الرئيسية:

#### 1. users (المستخدمون)
| الحقل | النوع | الوصف |
|--------|-------|-------|
| id | UUID | معرف فريد |
| email | String(255) | بريد إلكتروني (فريد) |
| phone | String(20) | رقم الهاتف |
| hashed_password | String(255) | كلمة مرور مشفرة |
| full_name | String(255) | الاسم الكامل |
| role | Enum | admin, lawyer, client, reviewer |
| is_active | Boolean | حساب نشط |
| is_verified | Boolean | تم التحقق منه |

#### 2. cases (القضايا)
| الحقل | النوع | الوصف |
|--------|-------|-------|
| id | UUID | معرف |
| title | String(500) | عنوان القضية |
| description | Text | وصف القضية |
| case_number | String(100) | رقم القضية |
| case_type | Enum | civil, criminal, commercial, family, labor, administrative |
| status | Enum | open, in_progress, closed, archived |
| court_name | String(255) | اسم المحكمة |
| owner_id | FK→users | مالك القضية |
| lawyer_id | FK→users | المحامي المسؤول |

#### 3. documents (المستندات)
| الحقل | النوع | الوصف |
|--------|-------|-------|
| id | UUID | معرف |
| title | String(500) | عنوان المستند |
| content | Text | محتوى المستند |
| doc_type | Enum | law, ruling, contract, memo, claim, defense, evidence, other |
| file_path | String | مسار الملف |
| file_size | Integer | حجم الملف |
| ocr_processed | Boolean | هل تمت معالجته بـ OCR |
| case_id | FK→cases | القضية المرتبطة |
| uploaded_by | FK→users | من قام بالرفع |

#### 4. laws (القوانين والتشريعات)
| الحقل | النوع | الوصف |
|--------|-------|-------|
| id | UUID | معرف |
| title | String(500) | اسم القانون |
| law_number | String(100) | رقم القانون |
| year | Integer | سنة الإصدار |
| category | String(200) | التصنيف |
| full_text | Text | النص الكامل |
| articles | JSON | بنود القانون |
| is_active | Boolean | القانون ساري |

#### 5. rulings (الأحكام القضائية)
| الحقل | النوع | الوصف |
|--------|-------|-------|
| id | UUID | معرف |
| title | String(500) | عنوان الحكم |
| ruling_number | String(100) | رقم الحكم |
| court_name | String(255) | المحكمة |
| ruling_date | Date | تاريخ الحكم |
| summary | Text | ملخص الحكم |
| full_text | Text | نص الحكم الكامل |
| legal_principles | Text | المبادئ القانونية المستخلصة |

#### 6. subscriptions (الاشتراكات)
| الحقل | النوع | الوصف |
|--------|-------|-------|
| id | UUID | معرف |
| user_id | FK→users | المستخدم |
| plan | Enum | free, professional, enterprise |
| status | Enum | active, expired, cancelled |
| search_quota | Integer | حد البحث |
| analysis_quota | Integer | حد التحليل |
| drafting_quota | Integer | حد الصياغة |

---

## نقاط API

### Authentication (المصادقة)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | /api/v1/auth/register | تسجيل مستخدم جديد |
| POST | /api/v1/auth/login | تسجيل الدخول |

**آلية المصادقة:** JWT (JSON Web Tokens)
- Access Token: صلاحية 30 دقيقة
- Refresh Token: صلاحية 7 أيام
- التوقيع: HS256
- تشفير كلمة المرور: bcrypt

### Users (المستخدمون)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | /api/v1/users/me | عرض الملف الشخصي |

### Cases (القضايا)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | /api/v1/cases/ | إنشاء قضية جديدة |
| GET | /api/v1/cases/ | عرض القضايا |

### Documents (المستندات)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | /api/v1/documents/upload | رفع مستند |

### Search (البحث القانوني)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | /api/v1/search/?q=... | بحث عبر المحتوى المفهرس |
| POST | /api/v1/search/index-init | تهيئة فهرس البحث |

**ميزات البحث:**
- Arabic Analyzer مخصص (تجذيع + تطبيع + كلمات توقف)
- بحث عبر القوانين (تشريعات + أحكام + مستندات)
- Highlighting للنتائج
- دعم استعلامات معقدة باستخدام bool query
- Pagination

### AI Analysis (التحليل الذكي)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | /api/v1/analysis/analyze | تحليل مستند قانوني |
| POST | /api/v1/analysis/query | استعلام قانوني (RAG) |
| POST | /api/v1/analysis/draft | صياغة مستند قانوني |
| POST | /api/v1/analysis/ingest | إضافة مستند للمعرفة القانونية |

**أنواع الصياغة المدعومة:**
- صحيفة دعوى (claim)
- مذكرة دفاع (defense)
- مذكرة قانونية (memo)
- استئناف/تمييز (appeal)
- عقد (contract)

### Subscriptions (الاشتراكات)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | /api/v1/subscriptions/me | عرض الاشتراك |
| POST | /api/v1/subscriptions/upgrade | ترقية الاشتراك |

**خطط الأسعار:**
| الخطة | السعر | البحث | التحليل | الصياغة |
|--------|-------|-------|---------|---------|
| مجاني | 0$ | 10/شهر | 0 | 0 |
| احترافي | 29$/شهر | غير محدود | 50/شهر | 20/شهر |
| مؤسسي | 99$/شهر | غير محدود | غير محدود | غير محدود |

---

## محرك البحث (Elasticsearch)

### الميزات:
- Arabic Analyzer مخصص
- تجذيع (Stemming) مخصص
- كلمات توقف عربية
- تطبيع (Normalization) عربي
- 3 فهارس: qanuni_laws, qanuni_rulings, qanuni_documents

### Mapping:
- title: معزز text بوزن boost 3.0
- content: مع محلل عربي text
- category, doc_type, court_name: keyword (قابل للتصفية)
- year: integer
- created_at: date

---

## محرك RAG (Retrieval-Augmented Generation)

### سير العمل:
1. **التقسيم (Ingest):** تقسيم المستندات إلى chunks (1000 حرف مع تداخل 200)
2. **التضمين (Embedding):** كل chunk يحول إلى vector عبر OpenAI text-embedding-3-large (3072 بعد)
3. **التخزين:** Vectors تخزن في Qdrant مع metadata
4. **الاستعلام:** تحويل الاستعلام إلى vector وجلب 5 نتائج مطابقة وإرسالها إلى GPT-4
5. **التوليد:** GPT-4 ينتج رد قانوني دقيق بناءً على المعلومات المسترجعة

### الإعدادات:
- **Text Splitter:** RecursiveCharacterTextSplitter (مخصص)
- **Embeddings:** OpenAI text-embedding-3-large
- **Vector Store:** Qdrant (تشابه تجميلي)
- **LLM:** GPT-4 Turbo (درجة حرارة: 0.1 للدقة)
- **Prompt:** قالب قانوني متخصص بالعربية

---

## صفحات الواجهة الأمامية (Frontend)

### الصفحات الرئيسية:

| الصفحة | المسار | الوصف |
|--------|--------|-------|
| الرئيسية | / | Landing page مع تعريف بالمنصة |
| البحث | /search | بحث قانوني متقدم |
| التحليل | /analysis | تحليل ذكي + استعلام/استفسار |
| الصياغة | /drafting | صياغة مستندات قانونية |
| القضايا | /cases | إدارة القضايا |
| المحامون | /lawyers | دليل المحامين |
| لوحة التحكم | /dashboard | لوحة تحكم المستخدم |
| الإدارة | /admin | لوحة تحكم المشرف |
| الاشتراكات | /subscribe | خطط الأسعار |
| تسجيل الدخول | /login | دخول المستخدم |
| التسجيل | /register | إنشاء حساب |

### المكونات:
- **Navbar:** شريط تنقل علوي (يتغير حسب دور المستخدم وصلاحياته)
- **API Client:** Axios مع interceptors (تجديد تلقائي للـ token + تحويل عند 401)
- **Auth Store:** Zustand (إدارة الحالة)

### ميزات التصميم:
- دعم RTL (من اليمين إلى اليسار)
- خط Tajawal المحسن
- تصميم متجاوب
- Tailwind CSS مع ألوان مخصصة
- حالات التحميل

---

## خدمة OCR

### التقنية: PaddleOCR
- دعم اللغة العربية
- الصيغ المدعومة: PNG، JPEG، TIFF، PDF
- تصحيح زاوية (Angle classification)
- نقطة API: POST /extract

---

## تشغيل Docker Compose

### الخدمات:
| الخدمة | المنفذ | الغرض |
|--------|--------|-------|
| backend | 8000 | FastAPI |
| frontend | 3000 | Next.js |
| postgres | 5432 | قاعدة البيانات |
| redis | 6379 | Cache |
| elasticsearch | 9200 | محرك بحث |
| qdrant | 6333 | Vector DB |
| ocr | 8001 | خدمة OCR |

### التشغيل:
```bash
docker-compose up -d
```

---

## تدابير الأمان

- **JWT Authentication** مع refresh tokens
- **RBAC** (4 أدوار: Admin، Lawyer، Client، Reviewer)
- **Password Hashing**: bcrypt
- **CORS** مخصصة
- **Input Validation**: Pydantic schemas
- **SQL Injection Prevention**: SQLAlchemy ORM
- **File Upload Limits**: 50MB حد أقصى
- **Rate Limiting**: Redis (تقييد الطلبات)

---

## دليل البدء السريع

### المتطلبات:
- Docker + Docker Compose
- أدوات: Python 3.11 + Node.js 20 + PostgreSQL + Redis + Elasticsearch

### خطوات التشغيل:
```bash
# 1. Clone
git clone https://github.com/bcbc39707-jpg/qanuni-platform.git
cd qanuni-platform

# 2. Environment
cp backend/.env.example backend/.env
# أضف OPENAI_API_KEY في .env

# 3. Start
docker-compose up -d

# 4. Access
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

---

## الميزات القادمة (قيد التطوير)

1. **Alembic Migrations** — إدارة تغييرات قاعدة البيانات تلقائياً
2. **نظام إشعارات متقدم** — إشعارات البريد الإلكتروني والتطبيق
3. **تنبيهات ذكية** — email + in-app
4. **Rate Limiting** — حماية واجهة API من الإساءة
5. **Testing** — اختبارات وحدة وتكامل
6. **CI/CD** — GitHub Actions
7. **Deployment** — VPS + Cloudflare
8. **تطبيق أندرويد** — React Native أو Flutter

---

## حالة المشروع

| المكون | الحالة | الملاحظات |
|---------|--------|---------|
| Architecture + Project Structure | ✓ مكتمل | هيكل نظيف |
| Backend (FastAPI + Auth + APIs) | ✓ مكتمل | 20+ نقطة |
| Database Models | ✓ مكتمل | 6 نماذج |
| Search Engine (Elasticsearch) | ✓ مكتمل | محلل عربي |
| RAG Engine (LangChain + Qdrant) | ✓ مكتمل | query + ingest |
| AI Analysis & Drafting | ✓ مكتمل | 5 أنواع صياغة |
| OCR Service | ✓ مكتمل | PaddleOCR |
| Frontend Pages | ✓ مكتمل | 11 صفحة |
| Subscription System | ✓ مكتمل | 3 خطط |
| Docker Compose | ✓ مكتمل | 7 خدمات |

**إجمالي الملفات:** 50+ ملف
**إجمالي الأسطر:** 1500+ سطر
