"""
通知、催辦與例外管理模組 (SQLite)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from database import get_db_connection


# 通知類型
NOTIFICATION_TYPES = [
    "公告未讀",
    "Issue 即將到期",
    "Issue 逾期",
    "控制測試到期",
    "控制測試逾期",
    "延期申請",
    "延期核准",
    "系統公告",
]

# 通知對象規則
NOTIFICATION_TARGETS = ["本人", "主管", "稽核主管", "法遵主管"]

# 逾期分層 (NTF-07)
OVERDUE_LEVELS = [
    (1, 7, "逾期 1-7 天"),
    (8, 30, "逾期 8-30 天"),
    (31, 999, "逾期 30 天以上"),
]


@dataclass
class Notification:
    id: int
    notification_type: str
    title: str
    message: str
    target_user: str
    target_role: str = ""
    source_module: str = ""
    source_id: str = ""
    is_read: bool = False
    created_at: str = ""
    read_at: str = ""


class NotificationManager:
    def __init__(self):
        self._load_notifications()

    def _load_notifications(self):
        self._notifications = {}
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM notifications ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            self._notifications[row["id"]] = self._row_to_notification(row)

    def _row_to_notification(self, row) -> Notification:
        return Notification(
            id=row["id"],
            notification_type=row["notification_type"],
            title=row["title"],
            message=row["content"] or "",
            target_user=row["target_user"],
            is_read=bool(row["is_read"] or 0),
            created_at=row["created_at"] or "",
            read_at=row["read_at"] or "",
        )

    def create_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        target_user: str,
        target_role: str = "",
        source_module: str = "",
        source_id: str = "",
    ) -> Notification:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO notifications (notification_type, title, content, 
                target_user, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (notification_type, title, message, target_user, now))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        self._load_notifications()
        return self._notifications.get(new_id)

    def get_user_notifications(self, target_user: str, unread_only: bool = False) -> List[Notification]:
        results = [n for n in self._notifications.values() if n.target_user == target_user]
        if unread_only:
            results = [n for n in results if not n.is_read]
        return sorted(results, key=lambda x: x.id, reverse=True)

    def mark_as_read(self, notification_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE notifications SET is_read = 1, read_at = ? 
            WHERE id = ?
        """, (now, notification_id))
        conn.commit()
        conn.close()
        self._load_notifications()
        return True

    def get_unread_count(self, target_user: str) -> int:
        return len(self.get_user_notifications(target_user, unread_only=True))

    def generate_reminders(
        self,
        issues: List,
        controls: List,
    ) -> List[Notification]:
        """產生到期提醒 (NTF-02, NTF-04, NTF-05)"""
        reminders = []
        today = datetime.now().date()
        
        # Issue 到期提醒 (T-7, T-3)
        for issue in issues:
            if issue.status == "Closed" or not issue.planned_due_date:
                continue
            
            try:
                due_date = datetime.strptime(issue.planned_due_date, "%Y-%m-%d").date()
                days_until = (due_date - today).days
                
                if days_until < 0:
                    # 逾期
                    overdue_days = abs(days_until)
                    level = "逾期 30 天以上" if overdue_days > 30 else ("逾期 8-30 天" if overdue_days > 7 else "逾期 1-7 天")
                    reminders.append(self.create_notification(
                        "Issue 逾期",
                        f"Issue #{issue.id} 已逾期",
                        f"缺失「{issue.title}」已逾期 {overdue_days} 天，請立即處理。",
                        issue.owner,
                        source_module="Issue Tracker",
                        source_id=str(issue.id),
                    ))
                elif days_until <= 3:
                    # T-3 提醒
                    reminders.append(self.create_notification(
                        "Issue 即將到期",
                        f"Issue #{issue.id} 將於 {days_until} 天後到期",
                        f"缺失「{issue.title}」預計於 {issue.planned_due_date} 到期，請抓緊處理。",
                        issue.owner,
                        source_module="Issue Tracker",
                        source_id=str(issue.id),
                    ))
                elif days_until <= 7:
                    # T-7 提醒
                    reminders.append(self.create_notification(
                        "Issue 即將到期",
                        f"Issue #{issue.id} 將於 {days_until} 天後到期",
                        f"缺失「{issue.title}」預計於 {issue.planned_due_date} 到期。",
                        issue.owner,
                        source_module="Issue Tracker",
                        source_id=str(issue.id),
                    ))
            except:
                pass
        
        # 控制測試到期提醒 (T-14, T-7)
        for ctrl in controls:
            if ctrl.status == "停用" or not ctrl.next_test_date:
                continue
            
            try:
                test_date = datetime.strptime(ctrl.next_test_date, "%Y-%m-%d").date()
                days_until = (test_date - today).days
                
                if days_until < 0:
                    # 逾期
                    reminders.append(self.create_notification(
                        "控制測試逾期",
                        f"控制點 {ctrl.id} 測試已逾期",
                        f"控制點「{ctrl.name}」測試已逾期，請儘速安排測試。",
                        ctrl.owner_user,
                        source_module="控制點矩陣",
                        source_id=ctrl.id,
                    ))
                elif days_until <= 7:
                    # T-7 提醒
                    reminders.append(self.create_notification(
                        "控制測試到期",
                        f"控制點 {ctrl.id} 將於 {days_until} 天後到期",
                        f"控制點「{ctrl.name}」預計於 {ctrl.next_test_date} 進行測試。",
                        ctrl.owner_user,
                        source_module="控制點矩陣",
                        source_id=ctrl.id,
                    ))
                elif days_until <= 14:
                    # T-14 提醒
                    reminders.append(self.create_notification(
                        "控制測試到期",
                        f"控制點 {ctrl.id} 將於 {days_until} 天後到期",
                        f"控制點「{ctrl.name}」預計於 {ctrl.next_test_date} 進行測試。",
                        ctrl.owner_user,
                        source_module="控制點矩陣",
                        source_id=ctrl.id,
                    ))
            except:
                pass
        
        return reminders

    def get_stats(self, target_user: str = None) -> Dict:
        """取得通知統計"""
        notifications = self._notifications.values() if not target_user else [
            n for n in self._notifications.values() if n.target_user == target_user
        ]
        
        total = len(notifications)
        unread = sum(1 for n in notifications if not n.is_read)
        
        type_counts = {}
        for n in notifications:
            type_counts[n.notification_type] = type_counts.get(n.notification_type, 0) + 1
        
        return {
            "total": total,
            "unread": unread,
            "by_type": type_counts,
        }


notification_manager = NotificationManager()