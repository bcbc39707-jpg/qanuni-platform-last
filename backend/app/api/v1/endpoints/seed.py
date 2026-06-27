from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.law import Law
from app.models.ruling import Ruling
from app.models.legal_division import LegalDivision
from app.models.legal_tree_node import LegalTreeNode
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

SAMPLE_LAWS = [
    {"title": "القانون المدني اليمني", "law_number": "14", "year": 2002, "category": "مدني", "full_text": "القانون المدني اليمني رقم (14) لسنة 2002م يتضمن الأحكام المنظمة للمعاملات المدنية في اليمن. الباب الأول: الأحكام العامة. الباب الثاني: الالتزامات والعقود. الباب الثالث: الحقوق العينية.", "articles": {"chapters": [{"chapter_number": "1", "chapter_title": "القانون المدني اليمني", "sections": [{"section_number": "1", "section_title": "جميع المواد", "articles": []}]}]}},
    {"title": "قانون الإجراءات الجزائية", "law_number": "13", "year": 1994, "category": "جزائي", "full_text": "قانون الإجراءات الجزائية اليمني رقم (13) لسنة 1994م. ينظم هذا القانون إجراءات التحقيق والمحاكمة والطعن في المواد الجزائية أمام المحاكم اليمنية.", "articles": {"chapters": [{"chapter_number": "1", "chapter_title": "قانون الإجراءات الجزائية", "sections": [{"section_number": "1", "section_title": "جميع المواد", "articles": []}]}]}},
    {"title": "قانون الأحوال الشخصية", "law_number": "20", "year": 1992, "category": "أحوال شخصية", "full_text": "قانون الأحوال الشخصية اليمني رقم (20) لسنة 1992م. ينظم هذا القانون الأحكام المتعلقة بالزواج والطلاق والنفقة والحضانة والوصية والميراث.", "articles": {"chapters": [{"chapter_number": "1", "chapter_title": "قانون الأحوال الشخصية", "sections": [{"section_number": "1", "section_title": "جميع المواد", "articles": []}]}]}},
    {"title": "قانون العمل اليمني", "law_number": "5", "year": 1995, "category": "عمل", "full_text": "قانون العمل اليمني رقم (5) لسنة 1995م. ينظم هذا القانون علاقات العمل بين أصحاب العمل والعمال في القطاعين العام والخاص.", "articles": {"chapters": [{"chapter_number": "1", "chapter_title": "قانون العمل اليمني", "sections": [{"section_number": "1", "section_title": "جميع المواد", "articles": []}]}]}},
    {"title": "قانون التجارة اليمني", "law_number": "32", "year": 1991, "category": "تجاري", "full_text": "قانون التجارة اليمني رقم (32) لسنة 1991م. يتضمن الأحكام المنظمة للأعمال التجارية والتجار والشركات التجارية والأوراق التجارية.", "articles": {"chapters": [{"chapter_number": "1", "chapter_title": "قانون التجارة اليمني", "sections": [{"section_number": "1", "section_title": "جميع المواد", "articles": []}]}]}},
]

SAMPLE_RULINGS = [
    {"title": "حكم المحكمة العليا - طعن مدني", "ruling_number": "451", "court_name": "المحكمة العليا", "case_type": "مدني", "summary": "قضت المحكمة العليا بأن عقد البيع الصادر من مالك العقار يعتبر نافذاً في مواجهة الغير متى تم تسجيله في السجل العقاري.", "full_text": "في الطعن المقيد برقم (451) لسنة 1444هـ أمام المحكمة العليا - الدائرة المدنية، حيث أن المدعي أقام دعواه بطلب إثبات ملكيته للعقار رقم (15) بناءً على عقد بيع عرفي. وقد قضت المحكمة العليا بأن عقد البيع الصادر من مالك العقار يعتبر نافذاً في مواجهة الغير متى تم تسجيله في السجل العقاري وفقاً لأحكام القانون المدني.", "legal_principles": "عقد البيع - التسجيل العقاري - نفاذ العقد في مواجهة الغير"},
    {"title": "حكم محكمة استئناف - قضية عمالية", "ruling_number": "88", "court_name": "محكمة استئناف صنعاء", "case_type": "عمالي", "summary": "قضت محكمة الاستئناف بأن إنهاء خدمة العامل دون اتباع الإجراءات القانونية يعتبر فسخاً تعسفياً يستوجب التعويض.", "full_text": "في الدعوى العمالية رقم (88) والمقامة من عامل ضد شركة المقاولات الحديثة، حيث أنهي خدماته دون إنذار مسبق. قضت محكمة استئناف صنعاء بأن إنهاء خدمة العامل دون اتباع الإجراءات المنصوص عليها في قانون العمل يعتبر فسخاً تعسفياً يستوجب تعويض العامل عن الأضرار المادية والمعنوية.", "legal_principles": "قانون العمل - الفسخ التعسفي - تعويض العامل"},
]

LEGAL_DIVISIONS = [
    {"name": "الدستور", "slug": "constitution", "description": "القانون الأسمى في الدولة", "sort_order": 1, "icon": "📜", "color": "tag-constitution"},
    {"name": "السلطات الدستورية", "slug": "constitutional-authorities", "description": "السلطات الثلاث: التشريعية والتنفيذية والقضائية", "sort_order": 2, "icon": "🏛️", "color": "tag-source"},
    {"name": "القوانين الرئيسية", "slug": "main-laws", "description": "القوانين الأساسية التي تنظم المجالات الرئيسية في الدولة", "sort_order": 3, "icon": "⚖️", "color": "tag-law"},
    {"name": "القوانين الفرعية", "slug": "sub-laws", "description": "القوانين المنظمة للمجالات المتخصصة", "sort_order": 4, "icon": "📋", "color": "tag-law"},
    {"name": "اللوائح التنفيذية", "slug": "executive-regulations", "description": "اللوائح التي تصدر عن مجلس الوزراء لتنفيذ أحكام القوانين", "sort_order": 5, "icon": "📄", "color": "tag-regulation"},
    {"name": "القرارات الجمهورية", "slug": "republican-decrees", "description": "القرارات التي يصدرها رئيس الجمهورية", "sort_order": 6, "icon": "📜", "color": "tag-decree"},
    {"name": "القرارات الوزارية", "slug": "ministerial-decisions", "description": "القرارات التي تصدرها الوزارات", "sort_order": 7, "icon": "📑", "color": "tag-decree"},
    {"name": "الأنظمة واللوائح الداخلية", "slug": "internal-regulations", "description": "أنظمة الجهات الحكومية والمؤسسات العامة", "sort_order": 8, "icon": "📋", "color": "tag-regulation"},
    {"name": "الأحكام القضائية", "slug": "judgments", "description": "الأحكام الصادرة عن المحاكم اليمنية", "sort_order": 9, "icon": "⚖️", "color": "tag-judicial"},
    {"name": "المبادئ القضائية", "slug": "judicial-doctrine", "description": "المبادئ القانونية المستقرة", "sort_order": 10, "icon": "💡", "color": "tag-doctrine"},
    {"name": "الاجتهادات القضائية", "slug": "jurisprudence", "description": "الاجتهادات القضائية المعتمدة", "sort_order": 11, "icon": "📚", "color": "tag-doctrine"},
    {"name": "السوابق القضائية", "slug": "precedents", "description": "الأحكام السابقة كمرجعية", "sort_order": 12, "icon": "📌", "color": "tag-judicial"},
    {"name": "الفقه القانوني", "slug": "legal-scholarship", "description": "الكتب والدراسات القانونية", "sort_order": 13, "icon": "📖", "color": "tag-doctrine"},
    {"name": "الموضوعات القانونية المتخصصة", "slug": "specialized-topics", "description": "تصنيفات موضوعية حسب المجالات", "sort_order": 14, "icon": "🎯", "color": "tag-specialty"},
]

LEGAL_TREE_NODES = [
    # Constitution branch
    {"name": "الجمهورية اليمنية", "node_type": "root", "level": 0, "sort_order": 0, "slug": "yemen-republic", "icon": "🇾🇪", "color": "level-0"},
]

@router.post("/seed-data")
async def seed_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")

    created = {"laws": 0, "rulings": 0, "divisions": 0, "tree_nodes": 0}

    for law_data in SAMPLE_LAWS:
        existing = await db.execute(select(Law).where(Law.title == law_data["title"]))
        if not existing.scalar_one_or_none():
            law = Law(**law_data)
            db.add(law)
            created["laws"] += 1

    for ruling_data in SAMPLE_RULINGS:
        existing = await db.execute(select(Ruling).where(Ruling.title == ruling_data["title"]))
        if not existing.scalar_one_or_none():
            ruling = Ruling(**ruling_data)
            db.add(ruling)
            created["rulings"] += 1

    for div_data in LEGAL_DIVISIONS:
        existing = await db.execute(select(LegalDivision).where(LegalDivision.slug == div_data["slug"]))
        if not existing.scalar_one_or_none():
            division = LegalDivision(**div_data)
            db.add(division)
            created["divisions"] += 1

    for node_data in LEGAL_TREE_NODES:
        existing = await db.execute(select(LegalTreeNode).where(LegalTreeNode.name == node_data["name"]))
        if not existing.scalar_one_or_none():
            node = LegalTreeNode(**node_data)
            db.add(node)
            created["tree_nodes"] += 1

    await db.commit()
    logger.info(f"Seed data inserted: {created}")
    return {"status": "success", "created": created}
