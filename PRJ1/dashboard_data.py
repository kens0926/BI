"""
管理儀表板與報表模組 (SQLite)
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
from database import get_db_connection


class ExportLog:
    """匯出日誌"""
    
    def log_export(self, exporter: str, report_name: str, purpose: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO export_logs (exporter, report_name, purpose, exported_at)
            VALUES (?, ?, ?, ?)
        """, (exporter, report_name, purpose, now))
        conn.commit()
        conn.close()


export_log = ExportLog()


class DashboardManager:
    def __init__(self, issue_manager, control_manager):
        self.issue_manager = issue_manager
        self.control_manager = control_manager

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """取得儀表板指標 (7.7.1)"""
        issues = self.issue_manager.list_issues()
        controls = self.control_manager.list_controls()
        today = datetime.now().date()
        
        # RPT-01: 開啟中 Issue 數
        open_issues = [i for i in issues if i.status != "Closed"]
        
        # RPT-02: 高風險 Issue 占比
        high_risk_issues = [i for i in open_issues if i.risk_level == "H"]
        high_risk_ratio = len(high_risk_issues) / len(open_issues) * 100 if open_issues else 0
        
        # RPT-03: 逾期 Issue 數
        overdue_issues = [i for i in issues if i.is_overdue()]
        
        # RPT-04: 平均逾期天數
        avg_overdue_days = 0
        if overdue_issues:
            total_days = sum(
                (today - datetime.strptime(i.planned_due_date, "%Y-%m-%d").date()).days
                for i in overdue_issues if i.planned_due_date
            )
            avg_overdue_days = total_days / len(overdue_issues)
        
        # RPT-05: 部門準時完成率
        dept_stats = self._calculate_dept_completion_rate(issues)
        
        # RPT-06: 控制測試完成率
        total_controls = len(controls)
        tested_controls = len([c for c in controls if c.last_test_date])
        test_completion_rate = tested_controls / total_controls * 100 if total_controls else 0
        
        # RPT-07: 控制測試逾期率
        overdue_controls = [c for c in controls if c.is_overdue()]
        test_overdue_rate = len(overdue_controls) / total_controls * 100 if total_controls else 0
        
        # RPT-08: 重複發生 Issue 比率
        recurring_issues = [i for i in issues if i.recurring_flag]
        recurring_ratio = len(recurring_issues) / len(issues) * 100 if issues else 0
        
        # RPT-09: 高風險 Issue 平均結案天數
        avg_close_days = self._calculate_avg_close_days(issues)
        
        # RPT-10: 各流程控制覆蓋率
        process_coverage = self._calculate_process_coverage(controls)
        
        # RPT-11: 無控制覆蓋高風險流程數量
        uncovered_risky_processes = self._count_uncovered_risky_processes(controls)
        
        return {
            "RPT-01": {
                "name": "開啟中 Issue 數",
                "value": len(open_issues),
                "detail": f"總 Issue: {len(issues)}, 開啟中: {len(open_issues)}",
            },
            "RPT-02": {
                "name": "高風險 Issue 占比",
                "value": round(high_risk_ratio, 1),
                "unit": "%",
                "detail": f"高風險: {len(high_risk_issues)} / {len(open_issues)}",
            },
            "RPT-03": {
                "name": "逾期 Issue 數",
                "value": len(overdue_issues),
                "detail": "需要立即處理" if overdue_issues else "無逾期",
            },
            "RPT-04": {
                "name": "平均逾期天數",
                "value": round(avg_overdue_days, 1),
                "unit": "天",
            },
            "RPT-05": {
                "name": "部門準時完成率",
                "value": dept_stats,
                "type": "dict",
            },
            "RPT-06": {
                "name": "控制測試完成率",
                "value": round(test_completion_rate, 1),
                "unit": "%",
                "detail": f"已測試: {tested_controls} / {total_controls}",
            },
            "RPT-07": {
                "name": "控制測試逾期率",
                "value": round(test_overdue_rate, 1),
                "unit": "%",
                "detail": f"逾期: {len(overdue_controls)} / {total_controls}",
            },
            "RPT-08": {
                "name": "重複發生 Issue 比率",
                "value": round(recurring_ratio, 1),
                "unit": "%",
                "detail": f"重複發生: {len(recurring_issues)} / {len(issues)}",
            },
            "RPT-09": {
                "name": "高風險 Issue 平均結案天數",
                "value": round(avg_close_days, 1) if avg_close_days else 0,
                "unit": "天",
            },
            "RPT-10": {
                "name": "各流程控制覆蓋率",
                "value": process_coverage,
                "type": "dict",
            },
            "RPT-11": {
                "name": "無控制覆蓋高風險流程數量",
                "value": uncovered_risky_processes,
                "detail": "需要評估新增控制點" if uncovered_risky_processes else "所有高風險流程均有控制",
            },
        }

    def _calculate_dept_completion_rate(self, issues: List) -> Dict:
        """計算部門準時完成率 (RPT-05)"""
        dept_stats = {}
        for issue in issues:
            if issue.status == "Closed" and issue.planned_due_date:
                dept = issue.owner.split()[0] if issue.owner else "未知"
                if dept not in dept_stats:
                    dept_stats[dept] = {"total": 0, "on_time": 0}
                dept_stats[dept]["total"] += 1
                # 簡單判斷：結案日在預計日前視為準時
                try:
                    close_date = datetime.strptime(issue.closed_at, "%Y-%m-%d").date()
                    due_date = datetime.strptime(issue.planned_due_date, "%Y-%m-%d").date()
                    if close_date <= due_date:
                        dept_stats[dept]["on_time"] += 1
                except:
                    pass
        
        # 計算比率
        for dept in dept_stats:
            total = dept_stats[dept]["total"]
            on_time = dept_stats[dept]["on_time"]
            dept_stats[dept]["rate"] = round(on_time / total * 100, 1) if total else 0
        
        return dept_stats

    def _calculate_avg_close_days(self, issues: List) -> float:
        """計算高風險 Issue 平均結案天數 (RPT-09)"""
        high_risk_closed = [
            i for i in issues 
            if i.risk_level == "H" and i.status == "Closed" and i.closed_at
        ]
        
        if not high_risk_closed:
            return 0
        
        total_days = 0
        for issue in high_risk_closed:
            try:
                created = datetime.strptime(issue.created_at, "%Y-%m-%d")
                closed = datetime.strptime(issue.closed_at, "%Y-%m-%d")
                total_days += (closed - created).days
            except:
                pass
        
        return total_days / len(high_risk_closed)

    def _calculate_process_coverage(self, controls: List) -> Dict:
        """計算各流程控制覆蓋率 (RPT-10)"""
        from control_data import PROCESSES
        
        process_stats = {p: {"total": 0, "active": 0} for p in PROCESSES}
        
        for ctrl in controls:
            if ctrl.process in process_stats:
                process_stats[ctrl.process]["total"] += 1
                if ctrl.status == "有效":
                    process_stats[ctrl.process]["active"] += 1
        
        coverage = {}
        for process, stats in process_stats.items():
            if stats["total"] > 0:
                coverage[process] = round(stats["active"] / stats["total"] * 100, 1)
            else:
                coverage[process] = 0
        
        return coverage

    def _count_uncovered_risky_processes(self, controls: List) -> int:
        """計算無控制覆蓋高風險流程數量 (RPT-11)"""
        from control_data import PROCESSES
        
        # 找出高風險控制點的流程
        risky_processes = set()
        for ctrl in controls:
            if ctrl.risk_level == "H" and ctrl.status == "有效":
                risky_processes.add(ctrl.process)
        
        # 找出沒有高風險控制的流程
        all_processes = set(PROCESSES)
        uncovered = all_processes - risky_processes
        
        return len(uncovered)

    def generate_report_data(self, report_type: str) -> Dict:
        """產生報表資料 (7.7.2)"""
        if report_type == "issue_tracker":
            return self._generate_issue_report()
        elif report_type == "control_test":
            return self._generate_control_test_report()
        elif report_type == "overdue":
            return self._generate_overdue_report()
        elif report_type == "coverage":
            return self._generate_coverage_report()
        return {}

    def _generate_issue_report(self) -> Dict:
        """產生 Issue 追蹤明細報表 (RPT-13)"""
        issues = self.issue_manager.list_issues()
        return {
            "total": len(issues),
            "by_status": self._count_by_status(issues),
            "by_risk": self._count_by_risk(issues),
            "by_type": self._count_by_type(issues),
        }

    def _generate_control_test_report(self) -> Dict:
        """產生控制測試執行情形報表 (RPT-14)"""
        controls = self.control_manager.list_controls()
        return {
            "total": len(controls),
            "by_status": self._count_control_by_status(controls),
            "by_risk": self._count_by_risk(controls),
            "upcoming": self.control_manager.get_upcoming_tests(30),
            "overdue": self.control_manager.get_overdue_controls(),
        }

    def _generate_overdue_report(self) -> Dict:
        """產生逾期事項分層報表 (RPT-15)"""
        issues = self.issue_manager.list_issues()
        controls = self.control_manager.list_controls()
        
        overdue_issues = [i for i in issues if i.is_overdue()]
        overdue_controls = [c for c in controls if c.is_overdue()]
        
        # 分層
        layers = {"1-7天": 0, "8-30天": 0, "30天以上": 0}
        for issue in overdue_issues:
            days = abs(issue.days_until_due())
            if days <= 7:
                layers["1-7天"] += 1
            elif days <= 30:
                layers["8-30天"] += 1
            else:
                layers["30天以上"] += 1
        
        return {
            "issue_overdue": len(overdue_issues),
            "control_overdue": len(overdue_controls),
            "layers": layers,
        }

    def _generate_coverage_report(self) -> Dict:
        """產生控制覆蓋率報表 (RPT-16)"""
        controls = self.control_manager.list_controls()
        return {
            "process_coverage": self._calculate_process_coverage(controls),
            "risk_coverage": self._count_by_risk(controls),
            "total_controls": len(controls),
            "active_controls": len([c for c in controls if c.status == "有效"]),
        }

    def _count_by_status(self, items: List) -> Dict:
        counts = {}
        for item in items:
            counts[item.status] = counts.get(item.status, 0) + 1
        return counts

    def _count_by_risk(self, items: List) -> Dict:
        counts = {"H": 0, "M": 0, "L": 0}
        for item in items:
            if item.risk_level in counts:
                counts[item.risk_level] += 1
        return counts

    def _count_by_type(self, items: List) -> Dict:
        counts = {}
        for item in items:
            itype = getattr(item, "issue_type", "未知") or "未知"
            counts[itype] = counts.get(itype, 0) + 1
        return counts

    def _count_control_by_status(self, controls: List) -> Dict:
        counts = {}
        for ctrl in controls:
            counts[ctrl.status] = counts.get(ctrl.status, 0) + 1
        return counts


# 匯出記錄 (RPT-17)
class ExportLog:
    def __init__(self):
        self._logs = []
    
    def log_export(
        self,
        exporter: str,
        report_name: str,
        purpose: str,
        filters: Dict = None,
    ):
        self._logs.append({
            "exporter": exporter,
            "report_name": report_name,
            "purpose": purpose,
            "filters": filters or {},
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        return self._logs[-limit:]


export_log = ExportLog()