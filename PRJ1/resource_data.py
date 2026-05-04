"""
資源資料模組 (SQLite)
"""
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
from database import get_db_connection


@dataclass
class ResourceLink:
    id: int
    title: str
    description: str
    url: str
    category: str
    sensitivity: str
    active: bool = True
    last_checked: str = ""


@dataclass
class ResourceCategory:
    name: str
    description: str
    links: List[ResourceLink] = field(default_factory=list)


class ResourceManager:
    def __init__(self):
        self._load_resources()

    def _load_resources(self):
        self._categories = {}
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM resources ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        
        # Group by category
        for row in rows:
            cat = row["category"] or "未分類"
            if cat not in self._categories:
                self._categories[cat] = ResourceCategory(
                    name=cat,
                    description=f"{cat}相關資源",
                    links=[],
                )
            self._categories[cat].links.append(ResourceLink(
                id=row["id"],
                title=row["name"],
                description=row["description"] or "",
                url=row["file_path"] or "",
                category=cat,
                sensitivity="公開",
                active=True,
            ))

    def add_resource(self, name: str, category: str, file_path: str, description: str, uploaded_by: str) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO resources (name, category, file_path, description, uploaded_by, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, category, file_path, description, uploaded_by, now))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        self._load_resources()
        return new_id

    def list_categories(self) -> List[ResourceCategory]:
        return list(self._categories.values())

    def total_links(self) -> int:
        return sum(len(category.links) for category in self._categories.values())

    def total_categories(self) -> int:
        return len(self._categories)

    def find_link(self, title: str) -> ResourceLink:
        for category in self._categories.values():
            for link in category.links:
                if link.title == title:
                    return link
        raise KeyError(f"Link not found: {title}")


resource_manager = ResourceManager()
