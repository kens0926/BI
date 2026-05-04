"""
證據文件管理模組 (SQLite)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import hashlib
from datetime import datetime
from database import get_db_connection


# 證據類型 (EVD-04)
EVIDENCE_TYPES = ["修復證據", "驗證證據", "測試證據", "公告附件", "制度附件"]

# 來源模組
SOURCE_MODULES = ["公告中心", "制度資源庫", "Issue Tracker", "控制點矩陣", "系統"]


@dataclass
class Evidence:
    id: int
    source_module: str
    source_id: str
    evidence_type: str
    file_name: str
    file_hash: str = ""
    uploaded_by: str = ""
    uploaded_at: str = ""
    summary: str = ""
    valid_until: str = ""
    archive_flag: bool = False
    version: int = 1

    def calculate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def is_expired(self) -> bool:
        if not self.valid_until:
            return False
        try:
            valid_date = datetime.strptime(self.valid_until, "%Y-%m-%d")
            return valid_date.date() < datetime.now().date()
        except:
            return False


class EvidenceManager:
    def __init__(self):
        self._load_evidences()

    def _load_evidences(self):
        self._evidences = {}
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM evidences ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            self._evidences[row["id"]] = self._row_to_evidence(row)

    def _row_to_evidence(self, row) -> Evidence:
        return Evidence(
            id=row["id"],
            source_module=row["module"],
            source_id=row["record_id"],
            evidence_type=row["file_name"].split(".")[-1] if row["file_name"] else "",
            file_name=row["file_name"],
            file_hash=row["file_hash"] or "",
            uploaded_by=row["uploaded_by"] or "",
            uploaded_at=row["uploaded_at"] or "",
            summary=row["description"] or "",
            archive_flag=bool(row["is_read"] or 0),
        )

    def list_evidences(self, source_module: str = None, source_id: str = None) -> List[Evidence]:
        results = self._evidences.values()
        if source_module:
            results = [e for e in results if e.source_module == source_module]
        if source_id:
            results = [e for e in results if e.source_id == source_id]
        return sorted(results, key=lambda x: x.id, reverse=True)

    def get_evidence(self, evidence_id: int) -> Optional[Evidence]:
        return self._evidences.get(evidence_id)

    def create_evidence(
        self,
        source_module: str,
        source_id: str,
        evidence_type: str,
        file_name: str,
        file_content: bytes = None,
        uploaded_by: str = "",
        summary: str = "",
        valid_until: str = "",
    ) -> Evidence:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_hash = ""
        if file_content:
            file_hash = hashlib.sha256(file_content).hexdigest()
        else:
            file_hash = hashlib.sha256(
                f"{source_module}{source_id}{file_name}{now}".encode()
            ).hexdigest()[:16] + "..."
        
        cursor.execute("""
            INSERT INTO evidences (module, record_id, file_name, file_hash, 
                uploaded_by, uploaded_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source_module, source_id, file_name, file_hash, uploaded_by, now, summary))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        self._load_evidences()
        return self._evidences.get(new_id)

    def get_evidences_by_source(self, source_module: str, source_id: str) -> List[Evidence]:
        return self.list_evidences(source_module, source_id)

    def archive_evidence(self, evidence_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE evidences SET is_read = 1 WHERE id = ?", (evidence_id,))
        conn.commit()
        conn.close()
        self._load_evidences()
        return True

    def get_stats(self) -> Dict:
        """取得證據統計"""
        total = len(self._evidences)
        archived = sum(1 for e in self._evidences.values() if e.archive_flag)
        expired = sum(1 for e in self._evidences.values() if e.is_expired())
        
        type_counts = {}
        for e in self._evidences.values():
            type_counts[e.evidence_type] = type_counts.get(e.evidence_type, 0) + 1
        
        return {
            "total": total,
            "active": total - archived,
            "archived": archived,
            "expired": expired,
            "by_type": type_counts,
        }


evidence_manager = EvidenceManager()