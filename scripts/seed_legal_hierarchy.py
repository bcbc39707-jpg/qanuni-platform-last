"""
Seed script for legal hierarchy (divisions, tree nodes).
Run: python scripts/seed_legal_hierarchy.py
"""
import asyncio
import sys
sys.path.insert(0, "backend")

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.legal_division import LegalDivision
from app.models.legal_tree_node import LegalTreeNode
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

ROOT_NODES = [
    {"name": "الجمهورية اليمنية", "node_type": "root", "level": 0, "sort_order": 0, "slug": "yemen-republic", "icon": "🇾🇪", "color": "level-0"},
    {"name": "النظام القضائي", "node_type": "judicial", "level": 1, "sort_order": 1, "slug": "judicial-system", "icon": "⚖️", "color": "level-1"},
]


async def seed():
    async with AsyncSessionLocal() as db:
        count = {"divisions": 0, "tree_nodes": 0}

        for div_data in LEGAL_DIVISIONS:
            existing = await db.execute(select(LegalDivision).where(LegalDivision.slug == div_data["slug"]))
            if not existing.scalar_one_or_none():
                division = LegalDivision(**div_data)
                db.add(division)
                count["divisions"] += 1

        for node_data in ROOT_NODES:
            existing = await db.execute(select(LegalTreeNode).where(LegalTreeNode.name == node_data["name"]))
            if not existing.scalar_one_or_none():
                node = LegalTreeNode(**node_data)
                db.add(node)
                count["tree_nodes"] += 1

        await db.commit()
        logger.info(f"Seeded: divisions={count['divisions']}, tree_nodes={count['tree_nodes']}")


if __name__ == "__main__":
    asyncio.run(seed())
