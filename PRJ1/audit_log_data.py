"""
稽核日誌資料模組 (SQLite)
"""
from dataclasses import dataclass
from typing import List
from datetime import datetime
from database import get_db_connection


@dataclass
class AuditLogEntry:
    id: int
    timestamp: str
    user: str
    action: str
    resource: str
    details: str


class AuditLogManager:
    def __init__(self):
        self._load_logs()

    def _load_logs(self):
        self._logs = []
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            self._logs.append(AuditLogEntry(
                id=row["id"],
                timestamp=row["created_at"],
                user=row["actor"],
                action=row["action"],
                resource=row["target"],
                details=row["detail"],
            ))

    def add_log(self, user: str, action: str, resource: str, details: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO audit_logs (actor, action, target, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user, action, resource, details, now))
        
        conn.commit()
        conn.close()
        self._load_logs()

    def get_logs(self, limit: int = 50) -> List[AuditLogEntry]:
        return sorted(self._logs, key=lambda x: x.timestamp, reverse=True)[:limit]


audit_log_manager = AuditLogManager()
