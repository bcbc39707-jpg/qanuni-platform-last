"""
Script to parse yemen_legal_tree.html and seed legal_tree_nodes and legal_divisions tables.
Run: python backend/parse_legal_tree.py
"""
import os
import sys
import asyncio
from bs4 import BeautifulSoup
from sqlalchemy import select, text
from pathlib import Path

# Fix sys.path to resolve app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import AsyncSessionLocal, engine
from app.models.legal_tree_node import LegalTreeNode
from app.models.legal_division import LegalDivision
from app.models.law import Law

HTML_FILE_PATH = Path("yemen_legal_tree.html")

def clean_value(val):
    if not val:
        return None
    val = val.strip()
    if val == "---" or val == "لا يوجد" or val == "null" or val == "":
        return None
    return val

def parse_node(article_el, level=0, parent_id=None):
    # Get direct header info
    header = article_el.find("div", class_="node-header")
    if not header:
        return []
    
    title_el = header.find("span", class_="node-title")
    title = title_el.text.strip() if title_el else "غير محدد"
    
    # Get classes for icons/colors
    classes = header.get("class", [])
    color_class = next((c for c in classes if c.startswith("level-")), None)
    
    # Get metadata tags
    tags = [t.text.strip() for t in header.find_all("span", class_="meta-tag")]
    
    # Find tag type (tag-constitution, tag-law, etc.)
    tag_type_el = header.find("span", class_="tag-constitution") or \
                  header.find("span", class_="tag-law") or \
                  header.find("span", class_="tag-regulation") or \
                  header.find("span", class_="tag-decree") or \
                  header.find("span", class_="tag-judicial") or \
                  header.find("span", class_="tag-doctrine") or \
                  header.find("span", class_="tag-specialty") or \
                  header.find("span", class_="tag-procedure") or \
                  header.find("span", class_="tag-source")
    
    tag_type = "general"
    if tag_type_el:
        tag_type_classes = tag_type_el.get("class", [])
        for c in tag_type_classes:
            if c.startswith("tag-"):
                tag_type = c.replace("tag-", "")
                break

    # Get content section
    content = article_el.find("div", class_="node-content", recursive=False)
    
    node_id = None
    official_name = title
    law_number = None
    year = None
    node_type = tag_type
    parent_dependency = parent_id
    status = "Active"
    slug = None
    description = ""
    meta_data = {}

    if content:
        fields = content.find("div", class_="data-fields")
        if fields:
            for field in fields.find_all("div", class_="field"):
                label_el = field.find("span", class_="field-label")
                value_el = field.find("span", class_="field-value")
                if label_el and value_el:
                    label = label_el.text.strip()
                    val = value_el.text.strip()
                    if "المعرف" in label:
                        node_id = clean_value(val)
                    elif "الاسم الرسمي" in label:
                        official_name = clean_value(val) or title
                    elif "الرقم والسنة" in label:
                        law_number = clean_value(val)
                    elif "النوع" in label:
                        node_type = clean_value(val) or node_type
                    elif "التبعية" in label:
                        parent_dependency = clean_value(val) or parent_dependency
                    elif "الحالة" in label:
                        status = clean_value(val) or status
                    elif "Slug" in label or "slug" in label:
                        slug = clean_value(val)
        
        desc_el = content.find("div", class_="description")
        if desc_el:
            description = desc_el.text.strip()
            
    # Fallback to a generated ID if not found
    if not node_id:
        import hashlib
        node_id = "YEM-NODE-" + hashlib.md5(title.encode('utf-8')).hexdigest()[:6].upper()

    # Parse year from law_number/year if possible
    if law_number:
        import re
        year_match = re.search(r'\b(19\d\d|20\d\d)\b', law_number)
        if year_match:
            year = int(year_match.group(1))

    node_data = {
        "id": node_id,
        "parent_id": parent_id,
        "name": official_name,
        "slug": slug or node_id.lower(),
        "description": description,
        "node_type": node_type,
        "level": level,
        "color": color_class,
        "is_active": status in ["فاعل", "نافذ", "Active", "active"],
        "meta_data": json.dumps({
            "law_number": law_number,
            "year": year,
            "original_title": title,
            "tag_type": tag_type
        }, ensure_ascii=False)
    }
    
    nodes = [node_data]
    
    # Process children recursively
    if content:
        children_div = content.find("div", class_="children", recursive=False)
        if children_div:
            child_articles = children_div.find_all("article", class_="legal-node", recursive=False)
            for sort_order, child_art in enumerate(child_articles):
                child_nodes = parse_node(child_art, level=level+1, parent_id=node_id)
                for cn in child_nodes:
                    cn["sort_order"] = sort_order
                nodes.extend(child_nodes)
            
    return nodes

import json

async def seed_tree():
    print(f"Reading and parsing HTML file: {HTML_FILE_PATH}")
    with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        
    root_article = soup.find("article", class_="legal-node")
    if not root_article:
        print("Root article not found in HTML!")
        return
        
    all_nodes = parse_node(root_article, level=0, parent_id=None)
    print(f"Extracted {len(all_nodes)} nodes from legal tree HTML.")

    async with AsyncSessionLocal() as db:
        # 1. Clear existing nodes
        print("Clearing old legal tree nodes and divisions...")
        await db.execute(text("DELETE FROM legal_tree_nodes"))
        await db.execute(text("DELETE FROM legal_divisions"))
        await db.commit()

        # 2. Insert into legal_divisions first for top-level categories (level 1 nodes)
        divisions_map = {}
        level_1_nodes = [n for n in all_nodes if n["level"] == 1]
        
        for sort_order, node in enumerate(level_1_nodes):
            div = LegalDivision(
                id=node["id"],
                name=node["name"],
                slug=node["slug"],
                description=node["description"],
                level=node["level"],
                sort_order=sort_order,
                icon="⚖️",
                color=node["color"],
                parent_id=node["parent_id"],
                is_active=node["is_active"]
            )
            db.add(div)
            divisions_map[node["id"]] = div
            print(f"Seeding Division: {div.name} (Slug: {div.slug})")

        await db.commit()

        # 3. Seed all nodes to legal_tree_nodes
        for sort_order, node in enumerate(all_nodes):
            meta = json.loads(node["meta_data"])
            
            # Find if there's a corresponding law in PostgreSQL to link
            ref_id = None
            ref_table = None
            
            # Match by name or metadata slug
            law_stmt = select(Law).where(
                (Law.title.like(f"%{node['name']}%")) | 
                (Law.slug == node["slug"])
            )
            law_res = await db.execute(law_stmt)
            matched_law = law_res.scalars().first()
            if matched_law:
                ref_id = matched_law.id
                ref_table = "laws"
                
                # Update the law's division relation
                # Find which division (level 1 node) this node belongs to
                parent_div_id = node["parent_id"]
                # Traverse up to find level 1 parent
                current_parent_id = node["parent_id"]
                level_1_parent_id = None
                while current_parent_id:
                    parent_node = next((n for n in all_nodes if n["id"] == current_parent_id), None)
                    if parent_node:
                        if parent_node["level"] == 1:
                            level_1_parent_id = parent_node["id"]
                            break
                        current_parent_id = parent_node["parent_id"]
                    else:
                        break
                
                if level_1_parent_id and level_1_parent_id in divisions_map:
                    matched_law.division_id = level_1_parent_id
                    print(f"Linked Law: '{matched_law.title}' to Division: '{divisions_map[level_1_parent_id].name}'")
            
            tree_node = LegalTreeNode(
                id=node["id"],
                parent_id=node["parent_id"],
                name=node["name"],
                slug=node["slug"],
                description=node["description"],
                node_type=node["node_type"],
                level=node["level"],
                sort_order=node.get("sort_order", sort_order),
                icon="📜" if "دستور" in node["node_type"] or "قانون" in node["node_type"] else "⚖️",
                color=node["color"],
                ref_table=ref_table,
                ref_id=ref_id,
                is_active=node["is_active"],
                meta_data=node["meta_data"]
            )
            db.add(tree_node)

        await db.commit()
        print("Successfully seeded all legal tree nodes and divisions! 🎉")

if __name__ == "__main__":
    asyncio.run(seed_tree())
