"""
Issue 資料模組 (SQLite)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from database import get_db_connection


# Issue 狀態流轉 (6.3)
WORKFLOW_STATES = ["Open", "Assigned", "Plan Submitted", "In Progress", "Pending Verification", "Closed"]
EXTENSION_STATES = ["延期申請中", "已核准延期", "已駁回延期"]
PRIORITY_LABELS = {"H": "高", "M": "中", "L": "低"}

# Issue 類型 (ISS-03)
ISSUE_TYPES = ["設計缺陷", "執行缺陷", "文件缺陷", "系統權限缺陷", "法遵缺陷"]

# 根因分類 (ISS-03)
ROOT_CAUSE_TYPES = ["人員疏失", "流程不完善", "系統缺失", "文件缺失", "其他"]


@dataclass
class Issue:
    id: int
    title: str
    finding: str
    risk_level: str
    control_id: str
    recommendation: str
    status: str
    owner: str
    issue_type: str = ""
    root_cause: str = ""
    impact_scope: str = ""
    planned_due_date: str = ""
    compensating_control: str = ""
    recurring_flag: bool = False
    verified_by: str = ""
    closed_at: str = ""
    extension_status: str = ""
    extension_reason: str = ""
    extension_new_date: str = ""
    evidence: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def next_statuses(self) -> List[str]:
        flow = {
            "Open": ["Assigned"],
            "Assigned": ["Plan Submitted"],
            "Plan Submitted": ["In Progress"],
            "In Progress": ["Pending Verification"],
            "Pending Verification": ["Closed"],
            "Closed": [],
        }
        if self.status in ["Assigned", "Plan Submitted", "In Progress"]:
            flow[self.status].append("延期申請中")
        if self.extension_status == "延期申請中":
            flow["延期申請中"] = ["已核准延期", "已駁回延期"]
        return flow.get(self.status, [])

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.next_statuses()

    def is_overdue(self) -> bool:
        if not self.planned_due_date or self.status == "Closed":
            return False
        try:
            due_date = datetime.strptime(self.planned_due_date, "%Y-%m-%d")
            return due_date.date() < datetime.now().date()
        except:
            return False

    def days_until_due(self) -> int:
        if not self.planned_due_date:
            return 999
        try:
            due_date = datetime.strptime(self.planned_due_date, "%Y-%m-%d")
            delta = due_date - datetime.now()
            return delta.days
        except:
            return 999


class IssueManager:
    def __init__(self):
        self._load_issues()

    def _load_issues(self):
        """從資料庫載入 Issue"""
        self._issues = {}
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM issues ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            self._issues[row["id"]] = self._row_to_issue(row)

    def _row_to_issue(self, row) -> Issue:
        """將資料庫資料轉換為 Issue 物件"""
        evidence_list = []
        if row["evidence"]:
            import json
            try:
                evidence_list = json.loads(row["evidence"])
            except:
                evidence_list = []
        
        return Issue(
            id=row["id"],
            title=row["title"],
            finding=row["finding"],
            risk_level=row["risk_level"] or "M",
            control_id=row["control_id"] or "",
            recommendation=row["recommendation"] or "",
            status=row["status"] or "Open",
            owner=row["owner"] or "未指定",
            issue_type=row["issue_type"] or "",
            root_cause=row["root_cause"] or "",
            impact_scope=row["impact_scope"] or "",
            planned_due_date=row["planned_due_date"] or "",
            compensating_control=row["compensating_control"] or "",
            recurring_flag=bool(row["recurring_flag"] or 0),
            closed_at=row["closed_at"] or "",
            extension_status=row["extension_status"] or "",
            evidence=evidence_list,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )

    def list_issues(self) -> List[Issue]:
        return sorted(self._issues.values(), key=lambda x: x.id)

    def get_issue(self, issue_id: int) -> Optional[Issue]:
        return self._issues.get(issue_id)

    def create_issue(self, title: str, finding: str, risk_level: str, control_id: str, recommendation: str, owner: str, created_at: str) -> Issue:
        """建立新 Issue"""
        import json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = created_at or datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO issues (title, finding, risk_level, control_id, 
                recommendation, status, owner, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?)
        """, (title, finding, risk_level, control_id, recommendation, owner, now, now))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        self._load_issues()
        return self._issues.get(new_id)

    def transition_issue(self, issue_id: int, new_status: str, updated_at: str) -> bool:
        """轉換 Issue 狀態"""
        issue = self.get_issue(issue_id)
        if issue is None or new_status not in issue.next_statuses():
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = updated_at or datetime.now().strftime("%Y-%m-%d")
        if new_status == "Closed":
            cursor.execute("""
                UPDATE issues SET status = ?, closed_at = ?, updated_at = ?
                WHERE id = ?
            """, (new_status, now, now, issue_id))
        else:
            cursor.execute("""
                UPDATE issues SET status = ?, updated_at = ?
                WHERE id = ?
            """, (new_status, now, issue_id))
        
        conn.commit()
        conn.close()
        self._load_issues()
        return True


issue_manager = IssueManager()
