"""
公告資料模組 (SQLite)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import difflib
from datetime import datetime
from database import get_db_connection


# 公告發布狀態 (ANN-02)
PUBLISH_STATUS = ["草稿", "審核中", "已發布", "已歸檔"]

# 公告分類 (ANN-01)
ANNOUNCEMENT_CATEGORIES = ["法規更新", "內部政策變更", "稽核提醒", "最佳實踐"]

# 重要級
IMPORTANCE_LEVELS = ["高", "中", "低"]


@dataclass
class AnnouncementVersion:
    title: str
    body: str
    version_label: str
    published_at: str


@dataclass
class Announcement:
    id: int
    category: str
    importance: str
    current_version: AnnouncementVersion
    version_history: List[AnnouncementVersion] = field(default_factory=list)
    force_read: bool = False
    publish_status: str = "已發布"
    target_scope: str = "全體"
    due_read_date: str = ""
    created_at: str = ""
    updated_at: str = ""
    active: bool = True

    def next_statuses(self) -> List[str]:
        flow = {
            "草稿": ["審核中"],
            "審核中": ["已發布", "草稿"],
            "已發布": ["已歸檔"],
            "已歸檔": ["已發布"],
        }
        return flow.get(self.publish_status, [])

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.next_statuses()

    def all_versions(self) -> List[AnnouncementVersion]:
        return [self.current_version] + self.version_history

    def get_version(self, version_label: str) -> Optional[AnnouncementVersion]:
        for version in self.all_versions():
            if version.version_label == version_label:
                return version
        return None

    def diff_with_version(self, older_version_label: str) -> str:
        older = self.get_version(older_version_label)
        if older is None:
            return "版本不存在。"
        before_lines = older.body.splitlines()
        after_lines = self.current_version.body.splitlines()
        diff_lines = difflib.unified_diff(
            before_lines, after_lines,
            fromfile=f"{older.version_label}",
            tofile=f"{self.current_version.version_label}",
            lineterm="",
        )
        return "\n".join(diff_lines) or "此版與當前版本無差異。"


class AnnouncementManager:
    def __init__(self):
        self._load_announcements()

    def _load_announcements(self):
        """從資料庫載入公告"""
        self._announcements = {}
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM announcements ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            self._announcements[row["id"]] = self._row_to_announcement(row)

    def _row_to_announcement(self, row) -> Announcement:
        """將資料庫資料轉換為 Announcement 物件"""
        return Announcement(
            id=row["id"],
            category=row["category"] or "法規更新",
            importance=row["importance"] or "中",
            current_version=AnnouncementVersion(
                title=row["title"] or "",
                body=row["content"] or "",
                version_label="V1.0",
                published_at=row["published_at"] or "",
            ),
            publish_status=row["publish_status"] or "草稿",
            target_scope=row["target_scope"] or "全體",
            due_read_date=row["due_read_date"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            active=(row["is_active"] == 1) if "is_active" in row.keys() else True,
        )

    def list_announcements(self, active_only: bool = True) -> List[Announcement]:
        announcements = sorted(self._announcements.values(), key=lambda x: x.id)
        if active_only:
            return [a for a in announcements if a.active]
        return announcements

    def get_announcement(self, announcement_id: int) -> Optional[Announcement]:
        return self._announcements.get(announcement_id)

    def create_announcement(self, title: str, content: str, category: str, 
                          importance: str, target_scope: str = "全體",
                          due_read_date: str = "", force_read: bool = False) -> int:
        """建立新公告"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO announcements (title, content, category, importance, 
                publish_status, target_scope, due_read_date, created_by, 
                created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, '草稿', ?, ?, 'system_admin', ?, ?, 1)
        """, (title, content, category, importance, target_scope, due_read_date, now, now))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        self._load_announcements()
        return new_id

    def update_announcement(self, announcement_id: int, **kwargs):
        """更新公告"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [now, announcement_id]
        
        cursor.execute("""
            UPDATE announcements SET {set_clause}, updated_at = ? 
            WHERE id = ?
        """, values)
        
        conn.commit()
        conn.close()
        self._load_announcements()

    def delete_announcement(self, announcement_id: int):
        """刪除公告"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
        conn.commit()
        conn.close()
        self._load_announcements()


announcement_manager = AnnouncementManager()
