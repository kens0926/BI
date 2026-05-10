from flask import Flask, render_template_string, redirect, url_for, session, request, flash, jsonify, send_file
from werkzeug.routing import BuildError
from datetime import datetime
from announcement_data import announcement_manager, PUBLISH_STATUS, ANNOUNCEMENT_CATEGORIES, IMPORTANCE_LEVELS
from issue_data import issue_manager, WORKFLOW_STATES, EXTENSION_STATES, PRIORITY_LABELS, ISSUE_TYPES, ROOT_CAUSE_TYPES
from resource_data import resource_manager
from audit_log_data import audit_log_manager
from control_data import control_manager, CONTROL_CATEGORIES, PROCESSES, RISK_LEVELS, TEST_FREQUENCIES, TEST_RESULTS, CONTROL_STATUS, TEST_WORKFLOW_STATES, CONTROL_TYPES, CONTROL_MODES, TEST_METHODS, SAMPLE_METHODS
from evidence_data import evidence_manager, EVIDENCE_TYPES, SOURCE_MODULES
from notification_data import notification_manager, NOTIFICATION_TYPES
from dashboard_data import DashboardManager, export_log
from user_data import user_manager, User

app = Flask(__name__)
app.secret_key = "change-this-secret-key"


# ==================== RBAC 角色權限系統 (7 角色) ====================
class Role:
    # R01 系統管理員
    SYSTEM_ADMIN = "system_admin"
    # R02 稽核主管
    AUDIT_MANAGER = "audit_manager"
    # R03 控制點負責人
    CONTROL_OWNER = "control_owner"
    # R04 控制測試執行者
    TESTER = "tester"
    # R05 缺失改善負責人
    PROCESS_OWNER = "process_owner"
    # R06 驗證或延期核准角色
    APPROVER = "approver"
    # R07 高階管理層或法遵單位
    REVIEWER = "reviewer"

# 角色顯示名稱
ROLE_LABELS = {
    Role.SYSTEM_ADMIN: "系統管理員",
    Role.AUDIT_MANAGER: "稽核主管",
    Role.CONTROL_OWNER: "控制點負責人",
    Role.TESTER: "測試人員",
    Role.PROCESS_OWNER: "改善負責人",
    Role.APPROVER: "核准者",
    Role.REVIEWER: "審閱者",
}

# 完整權限矩陣 (對應 ICP.MD 5.2 權限矩陣)
ROLE_PERMISSIONS = {
    Role.SYSTEM_ADMIN: {
        # 公告
        "can_create_announcement": True,
        "can_edit_announcement": True,
        "can_publish_announcement": True,
        "can_delete_announcement": True,
        # 制度資源
        "can_manage_resources": True,
        # 控制點
        "can_create_control": True,
        "can_edit_control": True,
        "can_disable_control": True,
        "can_manage_test_schedule": True,
        # Issue
        "can_create_issue": True,
        "can_transition_issue": True,
        "can_close_issue": True,  # 高風險結案
        # 測試結果
        "can_record_test_result": False,
        # 稽核日誌
        "can_view_audit_logs": True,
        "can_view_all_audit_logs": True,
        # 報表
        "can_export_data": True,
        "can_export_sensitive": True,
        # 用戶管理
        "can_manage_users": True,
    },
    Role.AUDIT_MANAGER: {
        "can_create_announcement": True,
        "can_edit_announcement": True,
        "can_publish_announcement": True,
        "can_delete_announcement": False,
        "can_manage_resources": True,
        "can_create_control": True,
        "can_edit_control": True,
        "can_disable_control": True,
        "can_manage_test_schedule": True,
        "can_create_issue": True,
        "can_transition_issue": True,
        "can_close_issue": True,
        "can_record_test_result": False,
        "can_view_audit_logs": True,
        "can_view_all_audit_logs": True,
        "can_export_data": True,
        "can_export_sensitive": True,
        "can_manage_users": True,
    },
    Role.CONTROL_OWNER: {
        "can_create_announcement": False,
        "can_edit_announcement": False,
        "can_publish_announcement": False,
        "can_delete_announcement": False,
        "can_manage_resources": False,
        "can_create_control": True,
        "can_edit_control": True,
        "can_disable_control": False,
        "can_manage_test_schedule": True,
        "can_create_issue": True,
        "can_transition_issue": False,
        "can_close_issue": False,
        "can_record_test_result": True,
        "can_view_audit_logs": True,
        "can_view_all_audit_logs": False,
        "can_export_data": False,
        "can_export_sensitive": False,
    },
    Role.TESTER: {
        "can_create_announcement": False,
        "can_edit_announcement": False,
        "can_publish_announcement": False,
        "can_delete_announcement": False,
        "can_manage_resources": False,
        "can_create_control": False,
        "can_edit_control": False,
        "can_disable_control": False,
        "can_manage_test_schedule": False,
        "can_create_issue": True,
        "can_transition_issue": False,
        "can_close_issue": False,
        "can_record_test_result": True,
        "can_view_audit_logs": True,
        "can_view_all_audit_logs": False,
        "can_export_data": False,
        "can_export_sensitive": False,
    },
    Role.PROCESS_OWNER: {
        "can_create_announcement": False,
        "can_edit_announcement": False,
        "can_publish_announcement": False,
        "can_delete_announcement": False,
        "can_manage_resources": False,
        "can_create_control": False,
        "can_edit_control": False,
        "can_disable_control": False,
        "can_manage_test_schedule": False,
        "can_create_issue": True,
        "can_transition_issue": True,
        "can_close_issue": False,
        "can_record_test_result": False,
        "can_view_audit_logs": True,
        "can_view_all_audit_logs": False,
        "can_export_data": False,
        "can_export_sensitive": False,
    },
    Role.APPROVER: {
        "can_create_announcement": False,
        "can_edit_announcement": False,
        "can_publish_announcement": False,
        "can_delete_announcement": False,
        "can_manage_resources": False,
        "can_create_control": False,
        "can_edit_control": False,
        "can_disable_control": False,
        "can_manage_test_schedule": False,
        "can_create_issue": False,
        "can_transition_issue": False,
        "can_close_issue": True,
        "can_record_test_result": False,
        "can_view_audit_logs": True,
        "can_view_all_audit_logs": False,
        "can_export_data": True,
        "can_export_sensitive": False,
    },
    Role.REVIEWER: {
        "can_create_announcement": False,
        "can_edit_announcement": False,
        "can_publish_announcement": False,
        "can_delete_announcement": False,
        "can_manage_resources": False,
        "can_create_control": False,
        "can_edit_control": False,
        "can_disable_control": False,
        "can_manage_test_schedule": False,
        "can_create_issue": False,
        "can_transition_issue": False,
        "can_close_issue": False,
        "can_record_test_result": False,
        "can_view_audit_logs": True,
        "can_view_all_audit_logs": False,
        "can_export_data": True,
        "can_export_sensitive": False,
    },
}


def get_current_role() -> str:
    """取得目前登入者的角色，預設為 R05 Process Owner"""
    role = session.get("user_role", Role.PROCESS_OWNER)
    print(f"DEBUG: get_current_role() - session user_role: {session.get('user_role')}, returning: {role}")
    return role


def get_current_role_label() -> str:
    """取得目前角色的顯示名稱"""
    role = get_current_role()
    return ROLE_LABELS.get(role, "未知角色")


def has_permission(permission: str) -> bool:
    """檢查目前使用者是否具有特定權限"""
    role = get_current_role()
    return ROLE_PERMISSIONS.get(role, {}).get(permission, False)


def require_permission(permission: str):
    """裝飾器：用於需要特定權限的路由"""
    from functools import wraps

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            role = get_current_role()
            has_perm = has_permission(permission)
            print(f"DEBUG: User role: {role}, Permission: {permission}, Has permission: {has_perm}")  # 調試信息
            if not has_perm:
                flash(f"您沒有權限執行此操作。您的角色：{role}", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ==================== 登入系統 ====================
def is_logged_in() -> bool:
    """檢查用戶是否已登入"""
    return session.get("logged_in", False)


def safe_url_for(endpoint, **values):
    try:
        return url_for(endpoint, **values)
    except BuildError:
        return "#"

app.jinja_env.globals['safe_url_for'] = safe_url_for


def require_login():
    """裝飾器：用於需要登入的路由"""
    from functools import wraps

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logged_in = is_logged_in()
            print(f"DEBUG: require_login - is_logged_in: {logged_in}")
            if not logged_in:
                return redirect(url_for("login"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_current_user() -> dict:
    """取得目前登入用戶資訊"""
    if not is_logged_in():
        return {}
    return {
        "username": session.get("username", ""),
        "role": session.get("user_role", Role.PROCESS_OWNER),
        "role_label": get_current_role_label(),
        "login_time": session.get("login_time", ""),
    }


# ==================== 強制閱讀機制增強 ====================
def check_unread_force_announcements():
    """檢查是否有未確認的高重要性公告"""
    announcements = announcement_manager.list_announcements()
    read_ids = set(session.get("read_announcements", []))
    forced_items = [a for a in announcements if a.force_read and a.id not in read_ids]
    return forced_items


def must_confirm_before_access():
    """檢查是否需要強制確認閱讀"""
    return len(check_unread_force_announcements()) > 0


# ==================== Issue 證據強制化 ====================
def can_transition_to_verification(issue_id: int) -> tuple[bool, str]:
    """
    檢查 Issue 是否可以轉換到 Verification 狀態
    返回: (允許與否, 原因訊息)
    """
    issue = issue_manager.get_issue(issue_id)
    if issue is None:
        return False, "Issue 不存在"

    # 檢查是否即將進入 Verification 狀態
    if "Verification" in issue.next_statuses():
        if not issue.evidence or len(issue.evidence) == 0:
            return False, "進入「驗證」狀態前必須上傳證明文件"
        return True, "允許轉換"

    return True, "允許轉換"


TEMPLATE_BASE = """
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <title>合規公告中心</title>
  <script>
    // Theme management
    (function() {
      const theme = localStorage.getItem('theme') || 'system';
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (theme === 'dark' || (theme === 'system' && prefersDark)) {
        document.documentElement.setAttribute('data-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
      }
    })();
  </script>
  <style>
    :root {
      --bg-primary: #f4f7fb;
      --bg-card: #ffffff;
      --bg-card-hover: #fafbfc;
      --text-primary: #1a1a2e;
      --text-secondary: #64748b;
      --text-muted: #94a3b8;
      --accent-primary: #0b2a5f;
      --accent-secondary: #1e40af;
      --accent-glow: rgba(11, 42, 95, 0.15);
      --border-color: rgba(226, 232, 240, 0.8);
      --border-light: rgba(255, 255, 255, 0.5);
      --shadow-sm: 0 1px 3px rgba(16, 24, 40, 0.06);
      --shadow-md: 0 4px 16px rgba(16, 24, 40, 0.08);
      --shadow-lg: 0 10px 40px rgba(16, 24, 40, 0.12);
      --shadow-glass: 0 8px 32px rgba(255, 255, 255, 0.15);
      --badge-high: #fef2f2;
      --badge-high-text: #dc2626;
      --badge-medium: #fffbeb;
      --badge-medium-text: #d97706;
      --badge-low: #f0fdf4;
      --badge-low-text: #16a34a;
      --category-color: #3b82f6;
      --transition-fast: 0.15s ease;
      --transition-normal: 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      --transition-smooth: 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }

    [data-theme="dark"] {
      --bg-primary: #0f172a;
      --bg-card: #1e293b;
      --bg-card-hover: #334155;
      --text-primary: #f1f5f9;
      --text-secondary: #cbd5e1;
      --text-muted: #64748b;
      --accent-primary: #3b82f6;
      --accent-secondary: #60a5fa;
      --accent-glow: rgba(59, 130, 246, 0.2);
      --border-color: rgba(51, 65, 85, 0.8);
      --border-light: rgba(255, 255, 255, 0.05);
      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
      --shadow-lg: 0 10px 40px rgba(0, 0, 0, 0.5);
      --shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.3);
      --badge-high: #450a0a;
      --badge-high-text: #fca5a5;
      --badge-medium: #451a03;
      --badge-medium-text: #fcd34d;
      --badge-low: #052e16;
      --badge-low-text: #86efac;
      --category-color: #60a5fa;
    }

    [data-theme="dark"] .button-secondary {
      background: rgba(255, 255, 255, 0.22);
      color: #e2e8f0;
      border-color: rgba(148, 163, 184, 0.85);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif; 
      margin: 0; padding: 0; 
      background: radial-gradient(circle at top left, rgba(59, 130, 246, 0.14), transparent 25%),
                  radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.10), transparent 20%),
                  var(--bg-primary); 
      color: var(--text-primary);
      transition: background var(--transition-normal), color var(--transition-normal);
      min-height: 100vh;
    }

    /* Premium Header */
    header {
      background: linear-gradient(135deg, var(--accent-primary) 0%, #1e3a8a 100%); 
      color: white; 
      padding: 28px 32px; 
      position: relative;
      overflow: hidden;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    header::before {
      content: '';
      position: absolute;
      top: -50%;
      right: -10%;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
      animation: float 6s ease-in-out infinite;
    }
    header::after {
      content: '';
      position: absolute;
      bottom: -30%;
      left: 10%;
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
      animation: float 8s ease-in-out infinite reverse;
    }
    @keyframes float {
      0%, 100% { transform: translateY(0) rotate(0deg); }
      50% { transform: translateY(-20px) rotate(5deg); }
    }

    .header-content {
      position: relative;
      z-index: 1;
      display: flex;
      justify-content: space-between;
      align-items: center;
      max-width: 1200px;
      margin: 0 auto;
    }

    header h1 {
      font-size: 1.75rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 4px;
    }

    header p {
      opacity: 0.9;
      font-size: 0.95rem;
    }

    /* Theme Toggle */
    .theme-toggle {
      display: flex;
      gap: 4px;
      background: rgba(255,255,255,0.15);
      padding: 4px;
      border-radius: 12px;
      backdrop-filter: blur(10px);
    }

    .theme-btn {
      padding: 8px 16px;
      border: none;
      background: transparent;
      color: rgba(255,255,255,0.7);
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 500;
      transition: all var(--transition-fast);
    }

    .theme-btn.active {
      background: rgba(255,255,255,0.25);
      color: white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    .theme-btn:hover:not(.active) {
      color: white;
    }

    .theme-toggle {
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
    }

    /* Container */
    .container { 
      max-width: 1200px; 
      margin: 32px auto; 
      padding: 0 24px; 
      min-height: calc(100vh - 160px);
    }

    /* Premium Card */
    .card { 
      background: var(--bg-card); 
      border-radius: 20px; 
      box-shadow: var(--shadow-md); 
      padding: 24px; 
      margin-bottom: 24px; 
      border: 1px solid var(--border-color);
      transition: all var(--transition-normal);
      position: relative;
      overflow: hidden;
    }

    .card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
      opacity: 0;
      transition: opacity var(--transition-normal);
    }

    .card:hover {
      transform: translateY(-4px);
      box-shadow: var(--shadow-lg);
    }

    .card:hover::before {
      opacity: 1;
    }

    /* Summary Cards */
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px;
      margin-bottom: 28px;
    }

    .summary-card {
      background: var(--bg-card);
      border-radius: 20px;
      padding: 28px 26px;
      border: 1px solid rgba(148, 163, 184, 0.18);
      box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
      transition: transform var(--transition-normal), box-shadow var(--transition-normal), border-color var(--transition-normal);
      position: relative;
      overflow: hidden;
      min-height: 180px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .summary-card::after {
      content: '';
      position: absolute;
      top: -14px;
      right: -14px;
      width: 120px;
      height: 120px;
      background: radial-gradient(circle at top right, var(--accent-glow), transparent 72%);
      pointer-events: none;
    }

    .summary-card:hover {
      transform: translateY(-8px);
      box-shadow: var(--shadow-lg);
      border-color: rgba(59, 130, 246, 0.4);
    }

    .summary-card::before {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, rgba(59,130,246,0.02), transparent 65%);
      pointer-events: none;
      border-radius: 20px;
    }

    .summary-card strong {
      display: block;
      font-size: 0.78rem;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }

    .summary-card p {
      font-size: 2.3rem;
      font-weight: 800;
      color: var(--text-primary);
      margin: 0;
      line-height: 1.05;
    }

    .summary-card small {
      display: block;
      margin-top: 14px;
      font-size: 0.89rem;
      color: var(--text-muted);
      line-height: 1.6;
    }

    .card-grid {
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }

    .card-grid .card {
      margin-bottom: 0;
    }

    .report-export-section {
      display: flex;
      justify-content: center;
      margin: 32px auto 28px;
      width: 100%;
    }

    .report-export-card {
      width: min(100%, 720px);
      margin-bottom: 0;
      text-align: left;
    }

    .report-export-card h3,
    .report-export-card > p {
      text-align: center;
    }

    .report-export-form {
      max-width: 560px;
      margin: 24px auto 0;
    }

    .report-export-form .button {
      display: flex;
      justify-content: center;
      width: 100%;
    }

    .dashboard-actions {
      display: flex;
      justify-content: center;
      margin-top: 8px;
    }

    /* Badge Styles */
    .badge { 
      display: inline-block; 
      padding: 6px 14px; 
      border-radius: 999px; 
      font-size: 0.8rem; 
      font-weight: 600;
      letter-spacing: 0.02em;
    }
    .badge-high { background: var(--badge-high); color: var(--badge-high-text); }
    .badge-medium { background: var(--badge-medium); color: var(--badge-medium-text); }
    .badge-low { background: var(--badge-low); color: var(--badge-low-text); }

    /* 用戶資訊區域 */
    .user-info-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 18px 24px;
      border-radius: 16px;
      margin-bottom: 24px;
      box-shadow: 0 10px 40px rgba(102, 126, 234, 0.18);
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .welcome-text {
      font-size: 18px;
      font-weight: 600;
    }

    .role-badge {
      background: rgba(255, 255, 255, 0.2);
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 14px;
      font-weight: 500;
    }

    .login-time {
      font-size: 14px;
      opacity: 0.9;
    }

    .user-actions {
      display: flex;
      gap: 12px;
    }

    .user-actions .button {
      background: rgba(255, 255, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.3);
      color: white;
      padding: 8px 16px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 500;
      transition: all 0.3s;
    }

    .user-actions .button:hover {
      background: rgba(255, 255, 255, 0.3);
      transform: translateY(-1px);
    }

    .category { 
      color: var(--category-color); 
      font-weight: 600; 
      font-size: 0.85rem;
    }

    /* Announcement Items */
    .announcement-item { 
      border-top: 1px solid var(--border-color); 
      padding: 20px 0; 
      transition: all var(--transition-normal);
    }
    .announcement-item:first-child { border-top: none; }
    .announcement-item:hover {
      background: var(--bg-card-hover);
      margin: 0 -12px;
      padding: 20px 12px;
      border-radius: 12px;
    }

    .announcement-meta { 
      display: flex; 
      flex-wrap: wrap; 
      gap: 12px; 
      align-items: center; 
      margin-bottom: 12px; 
      font-size: 0.9rem; 
      color: var(--text-secondary); 
    }

    .announcement-item h3 {
      margin: 0 0 8px;
      font-size: 1.15rem;
      font-weight: 600;
    }

    .announcement-item h3 a {
      color: var(--text-primary);
      text-decoration: none;
      transition: color var(--transition-fast);
    }

    .announcement-item h3 a:hover {
      color: var(--accent-primary);
    }

    .announcement-item p {
      color: var(--text-secondary);
      line-height: 1.6;
      margin: 0;
    }

    /* Resource Grid */
    .resource-grid { 
      display: grid; 
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
      gap: 16px; 
      margin-top: 20px; 
    }

    .resource-item { 
      background: var(--bg-card-hover); 
      border: 1px solid var(--border-color); 
      border-radius: 16px; 
      padding: 20px; 
      transition: all var(--transition-normal);
    }

    .resource-item:hover {
      transform: translateY(-4px);
      box-shadow: var(--shadow-md);
      border-color: var(--accent-primary);
    }

    .resource-item h4 { 
      margin: 0 0 10px; 
      font-size: 1.05rem;
    }

    .resource-item h4 a {
      color: var(--text-primary);
      text-decoration: none;
      transition: color var(--transition-fast);
    }

    .resource-item h4 a:hover {
      color: var(--accent-primary);
    }

    .resource-meta { 
      display: flex; 
      flex-wrap: wrap; 
      gap: 8px; 
      font-size: 0.85rem; 
      color: var(--text-muted); 
      margin-bottom: 0;
    }

    /* Issue Table */
    .issue-table { 
      width: 100%; 
      border-collapse: collapse; 
      margin-top: 20px; 
      font-size: 0.9rem;
    }
    .issue-table th, .issue-table td { 
      border: 1px solid var(--border-color); 
      padding: 14px 16px; 
      text-align: left; 
    }
    .issue-table th { 
      background: var(--bg-card-hover); 
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      font-size: 0.8rem;
      letter-spacing: 0.05em;
    }
    .issue-table tr:hover td {
      background: var(--bg-card-hover);
    }

    /* General Table */
    .table { 
      width: 100%; 
      border-collapse: collapse; 
      margin-top: 20px; 
      font-size: 0.95rem;
      line-height: 1.6;
    }
    .table th, .table td { 
      border: 1px solid var(--border-color); 
      padding: 16px 20px; 
      text-align: left; 
      vertical-align: middle;
    }
    .table th { 
      background: var(--bg-card-hover); 
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      font-size: 0.85rem;
      letter-spacing: 0.05em;
      padding: 18px 20px;
    }
    .table tr:hover td {
      background: var(--bg-card-hover);
    }
    .table td {
      word-wrap: break-word;
      max-width: 200px;
    }

    /* Action buttons in table cells */
    .table .action-buttons {
      display: flex;
      flex-direction: column;
      gap: 4px;
      align-items: flex-start;
    }

    .table .action-buttons .button {
      padding: 6px 12px;
      font-size: 0.8rem;
      min-width: auto;
    }

    /* Buttons */
    .button { 
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 12px 20px; 
      border-radius: 12px; 
      background: var(--accent-primary); 
      color: white; 
      text-decoration: none; 
      font-weight: 500;
      font-size: 0.9rem;
      transition: all var(--transition-normal);
      border: none;
      cursor: pointer;
    }

    .button:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 25px rgba(11, 42, 95, 0.16);
      text-decoration: none;
    }

    .button:focus-visible {
      outline: 2px solid rgba(59, 130, 246, 0.6);
      outline-offset: 2px;
    }

    .button-secondary { 
      background: rgba(255,255,255,0.85);
      color: var(--text-primary);
      border: 1px solid var(--border-color);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.5);
    }

    .button-secondary:hover {
      background: var(--accent-primary);
      color: white;
      border-color: var(--accent-primary);
    }

    /* Navigation */
    .nav-buttons {
      display: flex;
      flex-wrap: nowrap;
      gap: 12px;
      margin-bottom: 24px;
      overflow-x: auto;
      padding-bottom: 8px;
      scrollbar-width: thin;
      scrollbar-color: rgba(59,130,246,0.4) transparent;
    }

    .nav-buttons::-webkit-scrollbar {
      height: 8px;
    }
    .nav-buttons::-webkit-scrollbar-track {
      background: transparent;
    }
    .nav-buttons::-webkit-scrollbar-thumb {
      background: rgba(59,130,246,0.35);
      border-radius: 999px;
    }
    .nav-buttons a {
      flex: 0 0 auto;
    }

    /* Form Elements */
    .form-group { 
      margin-bottom: 16px; 
    }
    .form-group label { 
      display: block; 
      margin-bottom: 8px; 
      font-weight: 600; 
      color: var(--text-primary);
    }
    .form-group input, .form-group textarea, .form-group select { 
      width: 100%; 
      padding: 14px 16px; 
      border: 1px solid var(--border-color); 
      border-radius: 12px; 
      background: var(--bg-card);
      color: var(--text-primary);
      font-size: 0.95rem;
      transition: all var(--transition-fast);
    }

    .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
      outline: none;
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    /* Alert */
    .alert { 
      padding: 16px 20px; 
      background: var(--badge-medium); 
      border-radius: 14px; 
      margin-bottom: 24px; 
      color: var(--badge-medium-text);
      border: 1px solid rgba(249, 205, 116, 0.35);
      box-shadow: 0 8px 24px rgba(249, 205, 116, 0.08);
      transition: all var(--transition-normal);
    }

    .alert:hover {
      transform: scale(1.01);
    }

    /* Pre */
    pre { 
      background: var(--bg-card-hover); 
      padding: 20px; 
      border-radius: 12px; 
      overflow-x: auto; 
      font-size: 0.85rem;
      border: 1px solid var(--border-color);
    }

    /* Section Headers */
    h2 {
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 8px;
      color: var(--text-primary);
    }

    h3 {
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 12px;
      color: var(--text-primary);
    }

    /* Status indicator */
    .status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 8px;
    }

    .status-open { background: #ef4444; }
    .status-assigned { background: #f59e0b; }
    .status-plan { background: #3b82f6; }
    .status-progress { background: #8b5cf6; }
    .status-verification { background: #06b6d4; }
    .status-closed { background: #22c55e; }

    /* Animations */
    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .card, .summary-card, .announcement-item, .resource-item {
      animation: fadeInUp 0.5s ease-out forwards;
    }

    .summary-card:nth-child(1) { animation-delay: 0.1s; }
    .summary-card:nth-child(2) { animation-delay: 0.2s; }
    .summary-card:nth-child(3) { animation-delay: 0.3s; }
    .summary-card:nth-child(4) { animation-delay: 0.4s; }

    /* Responsive */
    @media (max-width: 768px) {
      .header-content {
        flex-direction: column;
        gap: 16px;
        text-align: center;
      }
      
      .container {
        padding: 0 16px;
      }

      .summary-grid {
        grid-template-columns: 1fr;
      }

      .announcement-meta {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }

      .table th, .table td {
        padding: 12px 8px;
        font-size: 0.85rem;
      }

      .table {
        font-size: 0.85rem;
      }

      .issue-table th, .issue-table td {
        padding: 10px 8px;
        font-size: 0.8rem;
      }
    }
  </style>
</head>
<body>
<header>
  <div class="header-content">
    <div>
      <h1>內控治理入口網站</h1>
      <p>展示公告分類、版本控制、強制閱讀與稽核追蹤可視化。</p>
    </div>
    <div style="display: flex; gap: 16px; align-items: center;">
      <div class="theme-toggle">
        <button class="theme-btn" onclick="setTheme('light')">☀️</button>
        <button class="theme-btn" onclick="setTheme('dark')">🌙</button>
        <button class="theme-btn" onclick="setTheme('system')">💻</button>
      </div>
    </div>
  </div>
</header>
<div class="container">
  <div class="nav-buttons">
    <a class="button" href="{{ url_for('index') }}">🏠 公告中心</a>
    <a class="button button-secondary" href="{{ url_for('resources') }}">📚 資源庫</a>
    <a class="button button-secondary" href="{{ url_for('issues') }}">🔧 Issue Tracker</a>
    <a class="button button-secondary" href="{{ url_for('dashboard') }}">📊 儀表板</a>
    <a class="button button-secondary" href="{{ url_for('controls') }}">控制點矩陣</a>
    {% if session.get('user_role') in ['audit_manager', 'system_admin', 'control_owner'] %}
    <a class="button button-secondary" href="{{ safe_url_for('manage_controls') }}">⚙️ 控制點維護</a>
    {% endif %}
    {% if session.get('user_role') in ['audit_manager', 'system_admin'] %}
    <a class="button button-secondary" href="{{ safe_url_for('manage_resources') }}">🔧 資源維護</a>
    {% endif %}
    {% if session.get('user_role') == 'system_admin' %}
    <a class="button button-secondary" href="{{ safe_url_for('audit_logs') }}">📋 稽核日誌</a>
    <a class="button button-secondary" href="{{ safe_url_for('manage_users') }}">👥 用戶管理</a>
    <a class="button button-secondary" href="{{ safe_url_for('manage_announcements') }}">📣 公告維護</a>
    {% endif %}
  </div>
  {% for message in get_flashed_messages() %}
  <div class="alert">{{ message }}</div>
  {% endfor %}
  {{ body | safe }}
</div>
<script>
  function setTheme(theme) {
    localStorage.setItem('theme', theme);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (theme === 'dark' || (theme === 'system' && prefersDark)) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
    // Update button states
    document.querySelectorAll('.theme-btn').forEach(btn => {
      btn.classList.remove('active');
      if (btn.textContent.toLowerCase().includes(theme) || 
          (theme === 'system' && btn.textContent.includes('系統')) ||
          (theme === 'light' && btn.textContent.includes('淺色')) ||
          (theme === 'dark' && btn.textContent.includes('深色'))) {
        btn.classList.add('active');
      }
    });
  }

  // Initialize theme buttons
  (function() {
    const savedTheme = localStorage.getItem('theme') || 'system';
    document.querySelectorAll('.theme-btn').forEach(btn => {
      btn.classList.remove('active');
      if (savedTheme === 'light' && btn.textContent.includes('淺色')) btn.classList.add('active');
      else if (savedTheme === 'dark' && btn.textContent.includes('深色')) btn.classList.add('active');
      else if (savedTheme === 'system' && btn.textContent.includes('系統')) btn.classList.add('active');
    });
  })();
</script>
</body>
</html>
"""


def get_importance_badge(importance: str) -> str:
    if importance == "高":
        return "badge badge-high"
    if importance == "中":
        return "badge badge-medium"
    return "badge badge-low"


# ==================== 登入系統路由 ====================
@app.route("/login", methods=["GET", "POST"])
def login():
    """登入頁面"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username and password:
            user = user_manager.authenticate(username, password)
            if user:
                session["logged_in"] = True
                session["username"] = user.username
                session["user_role"] = user.role
                session["login_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                audit_log_manager.add_log(
                    username,
                    "登入",
                    "系統",
                    f"用戶 {username} 以 {ROLE_LABELS.get(user.role, user.role)} 角色登入系統"
                )

                # 檢查是否需要強制修改密碼
                if user.force_password_change:
                    flash("您的密碼已重置，請設定新密碼。", "warning")
                    return redirect(url_for("change_password"))

                flash(f"歡迎登入，{username}！您的角色是：{ROLE_LABELS.get(user.role, user.role)}", "success")
                return redirect(url_for("index"))
            else:
                flash("用戶名或密碼錯誤，請重新輸入。", "error")
        else:
            flash("請輸入有效的用戶名和密碼。", "error")

    # 登入頁面
    login_body = f"""
    <div class="login-container">
      <div class="login-card">
        <h1>內控治理入口網站</h1>
        <h2>登入系統</h2>

        <form method="post" class="login-form">
          <div class="form-group">
            <label for="username">用戶名</label>
            <input type="text" id="username" name="username" required placeholder="輸入您的用戶名"/>
          </div>

          <div class="form-group">
            <label for="password">密碼</label>
            <input type="password" id="password" name="password" required placeholder="輸入您的密碼"/>
          </div>


          <button type="submit" class="button button-primary login-btn">登入系統</button>
        </form>

        <div class="forgot-password">
          <a href="{safe_url_for('forgot_password')}">忘記密碼？</a>
        </div>

        <div class="login-info">
          <p><strong>系統說明：</strong></p>
          <ul>
            <li>請使用有效的用戶名和密碼登入</li>
            <li>系統將依據您帳號設定的角色授予相應權限</li>
            <li>不同角色具有不同的系統操作權限</li>
          </ul>
        </div>
      </div>
    </div>

    <style>
    .login-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 84vh;
      padding: 20px;
      background: radial-gradient(circle at top left, rgba(52, 152, 219, 0.16), transparent 24%),
                  radial-gradient(circle at bottom right, rgba(46, 204, 113, 0.10), transparent 18%);
    }}

    .login-card {{
      position: relative;
      background: linear-gradient(180deg, #ffffff 0%, #eef7ff 100%);
      border-radius: 24px;
      box-shadow: 0 24px 60px rgba(15, 64, 107, 0.12);
      padding: 44px 36px;
      width: 100%;
      max-width: 520px;
      border: 1px solid rgba(52, 152, 219, 0.14);
      overflow: hidden;
    }}

    .login-card::before {{
      content: '';
      position: absolute;
      top: -40px;
      right: -40px;
      width: 150px;
      height: 150px;
      background: rgba(52, 152, 219, 0.12);
      border-radius: 50%;
      filter: blur(20px);
    }}

    .login-card h1 {{
      text-align: center;
      color: #1f3a60;
      margin-bottom: 10px;
      font-size: 26px;
      letter-spacing: -0.02em;
    }}

    .login-card h2 {{
      text-align: center;
      color: #506b8a;
      margin-bottom: 32px;
      font-size: 18px;
      font-weight: 500;
    }}

    .login-form {{
      margin-bottom: 32px;
    }}

    .form-group {{
      margin-bottom: 20px;
    }}

    .form-group label {{
      display: block;
      margin-bottom: 8px;
      font-weight: 700;
      color: #1f3a60;
    }}

    .form-group input,
    .form-group select {{
      width: 100%;
      padding: 14px 16px;
      border: 1px solid rgba(144, 164, 174, 0.28);
      border-radius: 12px;
      font-size: 15px;
      color: #1f3a60;
      background: #fbfdff;
      box-shadow: inset 0 1px 2px rgba(255,255,255,0.8);
      transition: border-color 0.25s, box-shadow 0.25s;
    }}

    .form-group input:focus,
    .form-group select:focus {{
      outline: none;
      border-color: #3d95d7;
      box-shadow: 0 0 0 4px rgba(52, 152, 219, 0.12);
    }}

    .login-btn {{
      width: 100%;
      padding: 14px;
      background: linear-gradient(135deg, #2d8ce9, #1768c9);
      color: white;
      border: none;
      border-radius: 12px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}

    .login-btn:hover {{
      transform: translateY(-2px);
      box-shadow: 0 10px 24px rgba(23, 104, 201, 0.24);
    }}

    .forgot-password {{
      text-align: center;
      margin: 22px 0;
    }}

    .forgot-password a {{
      color: #1768c9;
      text-decoration: none;
      font-size: 14px;
      font-weight: 600;
      transition: color 0.25s;
    }}

    .forgot-password a:hover {{
      color: #0f4ea7;
      text-decoration: underline;
    }}

    .login-info {{
      background: #f0f7ff;
      padding: 22px;
      border-radius: 16px;
      border-left: 4px solid #3d95d7;
      color: #3b4b66;
      line-height: 1.7;
    }}

    .login-info p {{
      margin-bottom: 12px;
      font-weight: 700;
      color: #1f3a60;
    }}

    .login-info ul {{
      margin: 0;
      padding-left: 20px;
    }}

    .login-info li {{
      margin-bottom: 10px;
      color: #4f667a;
    }}
    </style>
    """

    return render_template_string(TEMPLATE_BASE, body=login_body)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """忘記密碼頁面"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()

        if username and email:
            user = user_manager.get_user_by_username(username)
            if user and user.email == email:
                # 生成臨時密碼
                import secrets
                import string
                temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
                
                # 更新用戶密碼
                user_manager.update_password_by_username(username, temp_password)
                
                # 設置強制修改密碼標記
                user_manager.set_force_password_change(username, True)
                
                # 記錄稽核日誌
                audit_log_manager.add_log(
                    "system",
                    "密碼重置",
                    "系統",
                    f"用戶 {username} 請求密碼重置，生成臨時密碼"
                )
                
                flash(f"臨時密碼已生成並發送。您的臨時密碼是：{temp_password}。請使用此密碼登入後立即修改密碼。", "success")
                return redirect(url_for("login"))
            else:
                flash("用戶名或Email地址不正確。", "error")
        else:
            flash("請輸入有效的用戶名和Email地址。", "error")

    # 忘記密碼頁面
    forgot_body = f"""
    <div class="login-container">
      <div class="login-card">
        <h1>內控治理入口網站</h1>
        <h2>忘記密碼</h2>

        <form method="post" class="login-form">
          <div class="form-group">
            <label for="username">用戶名</label>
            <input type="text" id="username" name="username" required placeholder="輸入您的用戶名"/>
          </div>

          <div class="form-group">
            <label for="email">Email地址</label>
            <input type="email" id="email" name="email" required placeholder="輸入您的註冊Email地址"/>
          </div>

          <button type="submit" class="button button-primary login-btn">重置密碼</button>
        </form>

        <div class="forgot-password">
          <a href="{safe_url_for('login')}">回到登入頁面</a>
        </div>

        <div class="login-info">
          <p><strong>密碼重置說明：</strong></p>
          <ul>
            <li>請輸入您的用戶名和註冊時使用的Email地址</li>
            <li>系統將生成臨時密碼並顯示在畫面上</li>
            <li>請使用臨時密碼登入後立即修改密碼</li>
          </ul>
        </div>
      </div>
    </div>

    <style>
    .login-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 84vh;
      padding: 20px;
      background: radial-gradient(circle at top left, rgba(52, 152, 219, 0.16), transparent 24%),
                  radial-gradient(circle at bottom right, rgba(46, 204, 113, 0.10), transparent 18%);
    }}

    .login-card {{
      position: relative;
      background: linear-gradient(180deg, #ffffff 0%, #eef7ff 100%);
      border-radius: 24px;
      box-shadow: 0 24px 60px rgba(15, 64, 107, 0.12);
      padding: 44px 36px;
      width: 100%;
      max-width: 520px;
      border: 1px solid rgba(52, 152, 219, 0.14);
      overflow: hidden;
    }}

    .login-card::before {{
      content: '';
      position: absolute;
      top: -40px;
      right: -40px;
      width: 150px;
      height: 150px;
      background: rgba(52, 152, 219, 0.12);
      border-radius: 50%;
      filter: blur(20px);
    }}

    .login-card h1 {{
      text-align: center;
      color: #1f3a60;
      margin-bottom: 10px;
      font-size: 26px;
      letter-spacing: -0.02em;
    }}

    .login-card h2 {{
      text-align: center;
      color: #506b8a;
      margin-bottom: 32px;
      font-size: 18px;
      font-weight: 500;
    }}

    .login-form {{
      margin-bottom: 32px;
    }}

    .form-group {{
      margin-bottom: 20px;
    }}

    .form-group label {{
      display: block;
      margin-bottom: 8px;
      font-weight: 700;
      color: #1f3a60;
    }}

    .form-group input,
    .form-group select {{
      width: 100%;
      padding: 14px 16px;
      border: 1px solid rgba(144, 164, 174, 0.28);
      border-radius: 12px;
      font-size: 15px;
      color: #1f3a60;
      background: #fbfdff;
      box-shadow: inset 0 1px 2px rgba(255,255,255,0.8);
      transition: border-color 0.25s, box-shadow 0.25s;
    }}

    .form-group input:focus,
    .form-group select:focus {{
      outline: none;
      border-color: #3d95d7;
      box-shadow: 0 0 0 4px rgba(52, 152, 219, 0.12);
    }}

    .login-btn {{
      width: 100%;
      padding: 14px;
      background: linear-gradient(135deg, #2d8ce9, #1768c9);
      color: white;
      border: none;
      border-radius: 12px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}

    .login-btn:hover {{
      transform: translateY(-2px);
      box-shadow: 0 10px 24px rgba(23, 104, 201, 0.24);
    }}

    .forgot-password {{
      text-align: center;
      margin: 22px 0;
    }}

    .forgot-password a {{
      color: #1768c9;
      text-decoration: none;
      font-size: 14px;
      font-weight: 600;
      transition: color 0.25s;
    }}

    .forgot-password a:hover {{
      color: #0f4ea7;
      text-decoration: underline;
    }}

    .login-info {{
      background: #f0f7ff;
      padding: 22px;
      border-radius: 16px;
      border-left: 4px solid #3d95d7;
      color: #3b4b66;
      line-height: 1.7;
    }}

    .login-info p {{
      margin-bottom: 12px;
      font-weight: 700;
      color: #1f3a60;
    }}

    .login-info ul {{
      margin: 0;
      padding-left: 20px;
    }}

    .login-info li {{
      margin-bottom: 10px;
      color: #4f667a;
    }}
    </style>
    """

    return render_template_string(TEMPLATE_BASE, body=forgot_body)


@app.route("/change-password", methods=["GET", "POST"])
@require_login()
def change_password():
    """密碼修改頁面"""
    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        username = session.get("username")
        user = user_manager.authenticate(username, current_password)

        if not user:
            flash("目前密碼錯誤。", "error")
        elif not new_password or len(new_password) < 6:
            flash("新密碼長度至少需要6個字符。", "error")
        elif new_password != confirm_password:
            flash("新密碼與確認密碼不一致。", "error")
        else:
            # 更新密碼
            user_manager.update_password_by_username(username, new_password)
            
            # 清除強制修改密碼標記
            user_manager.set_force_password_change(username, False)
            
            # 記錄稽核日誌
            audit_log_manager.add_log(
                username,
                "密碼修改",
                "系統",
                f"用戶 {username} 修改密碼"
            )
            
            flash("密碼已成功修改。", "success")
            return redirect(url_for("index"))

    # 密碼修改頁面
    change_body = f"""
    <div class="login-container">
      <div class="login-card">
        <h1>內控治理入口網站</h1>
        <h2>修改密碼</h2>

        <form method="post" class="login-form">
          <div class="form-group">
            <label for="current_password">目前密碼</label>
            <input type="password" id="current_password" name="current_password" required placeholder="輸入目前密碼"/>
          </div>

          <div class="form-group">
            <label for="new_password">新密碼</label>
            <input type="password" id="new_password" name="new_password" required placeholder="輸入新密碼（至少6個字符）"/>
          </div>

          <div class="form-group">
            <label for="confirm_password">確認新密碼</label>
            <input type="password" id="confirm_password" name="confirm_password" required placeholder="再次輸入新密碼"/>
          </div>

          <button type="submit" class="button button-primary login-btn">修改密碼</button>
        </form>

        <div class="login-info">
          <p><strong>密碼修改說明：</strong></p>
          <ul>
            <li>新密碼長度至少需要6個字符</li>
            <li>請使用強密碼，包含字母和數字</li>
            <li>修改密碼後請妥善保管</li>
          </ul>
        </div>
      </div>
    </div>

    <style>
    .login-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 80vh;
      padding: 20px;
    }}

    .login-card {{
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.1);
      padding: 40px;
      width: 100%;
      max-width: 450px;
    }}

    .login-card h1 {{
      text-align: center;
      color: #2c3e50;
      margin-bottom: 10px;
      font-size: 24px;
    }}

    .login-card h2 {{
      text-align: center;
      color: #7f8c8d;
      margin-bottom: 30px;
      font-size: 18px;
    }}

    .login-form {{
      margin-bottom: 30px;
    }}

    .form-group {{
      margin-bottom: 20px;
    }}

    .form-group label {{
      display: block;
      margin-bottom: 5px;
      font-weight: 600;
      color: #2c3e50;
    }}

    .form-group input {{
      width: 100%;
      padding: 12px;
      border: 2px solid #e1e8ed;
      border-radius: 6px;
      font-size: 16px;
      transition: border-color 0.3s;
    }}

    .form-group input:focus {{
      outline: none;
      border-color: #3498db;
    }}

    .login-btn {{
      width: 100%;
      padding: 14px;
      background: linear-gradient(135deg, #3498db, #2980b9);
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s;
    }}

    .login-btn:hover {{
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
    }}

    .login-info {{
      background: #f8f9fa;
      padding: 20px;
      border-radius: 6px;
      border-left: 4px solid #3498db;
    }}

    .login-info ul {{
      margin: 0;
      padding-left: 20px;
    }}

    .login-info li {{
      margin-bottom: 8px;
      color: #555;
    }}
    </style>
    """

    return render_template_string(TEMPLATE_BASE, body=change_body)


@app.route("/logout")
def logout():
    """登出"""
    username = session.get("username", "unknown")
    role = session.get("user_role", "unknown")

    # 記錄登出日誌
    audit_log_manager.add_log(
        username,
        "登出",
        "系統",
        f"用戶 {username} ({ROLE_LABELS.get(role, role)}) 登出系統"
    )

    # 清除 session
    session.clear()
    flash("您已成功登出系統。", "info")
    return redirect(url_for("login"))


@app.route("/")
@require_login()
def index():
    announcements = announcement_manager.list_announcements(active_only=True)
    read_ids = set(session.get("read_announcements", []))
    forced_items = [a for a in announcements if a.force_read and a.id not in read_ids]
    total_count = len(announcements)
    unread_count = len(forced_items)
    issue_count = len(issue_manager.list_issues())
    open_issues = sum(1 for issue in issue_manager.list_issues() if issue.status != "Closed")
    log_count = len(audit_log_manager.get_logs(1000))  # Get total logs

    body = f"""
    <!-- 用戶資訊區域 -->
    <div class="user-info-bar">
      <div class="user-info">
        <span class="welcome-text">歡迎，{get_current_user()['username']}！</span>
        <span class="role-badge">{get_current_user()['role_label']}</span>
        <span class="login-time">登入時間：{get_current_user()['login_time']}</span>
      </div>
      <div class="user-actions">
        <a href="{url_for('logout')}" class="button button-secondary">登出</a>
      </div>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <strong>公告總數</strong>
        <p>{total_count} 則</p>
      </div>
      <div class="summary-card">
        <strong>待確認閱讀</strong>
        <p>{unread_count} 則</p>
      </div>
      <div class="summary-card">
        <strong>Issue Tracker</strong>
        <p>{issue_count} 件</p>
        <small>開啟中：{open_issues} 件</small>
      </div>
      <div class="summary-card">
        <strong>稽核日誌</strong>
        <p>{log_count} 筆</p>
      </div>
    </div>

    <div class="card">
      <h2>公告列表</h2>
      <p>目前共有 {total_count} 則公告，列出最新公告與高優先通知。</p>
    </div>
    """

    if forced_items:
        body += "<div class=\"card\"><h3>待強制閱讀公告</h3>"
        for item in forced_items:
            body += f"<div class=\"announcement-item\">"
            body += f"<div class=\"announcement-meta\"><span class=\"category\">{item.category}</span><span class=\"{get_importance_badge(item.importance)}\">重要級：{item.importance}</span><span>發布：{item.current_version.published_at}</span></div>"
            body += f"<h3><a href=\"{url_for('announcement_detail', announcement_id=item.id)}\">{item.current_version.title}</a></h3>"
            body += f"<p>{item.current_version.body.splitlines()[0]}...</p>"
            body += f"<a class=\"button\" href=\"{url_for('announcement_detail', announcement_id=item.id)}\">檢視並確認閱讀</a>"
            body += "</div>"
        body += "</div>"

    body += f"<div class=\"card\"><h3>制度資源庫</h3><p>已管理 {resource_manager.total_categories()} 個分類，包含 {resource_manager.total_links()} 個資源連結。</p><a class=\"button button-secondary\" href=\"{url_for('resources')}\">前往資源庫</a></div>"
    body += "<div class=\"card\"><h3>所有公告</h3>"
    for item in announcements:
        body += f"<div class=\"announcement-item\">"
        body += f"<div class=\"announcement-meta\"><span class=\"category\">{item.category}</span><span class=\"{get_importance_badge(item.importance)}\">重要級：{item.importance}</span><span>發布：{item.current_version.published_at}</span>"
        if item.force_read and item.id not in read_ids:
            body += f"<span style=\"color:#b02a37; font-weight:700;\">尚未確認閱讀</span>"
        body += "</div>"
        body += f"<h3><a href=\"{url_for('announcement_detail', announcement_id=item.id)}\">{item.current_version.title}</a></h3>"
        body += f"<p>{item.current_version.body.splitlines()[0]}...</p>"
        body += f"<a class=\"button button-secondary\" href=\"{url_for('announcement_detail', announcement_id=item.id)}\">閱讀詳細內容</a>"
        body += "</div>"
    body += "</div>"

    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/users", methods=["GET", "POST"])
@require_login()
@require_permission("can_manage_users")
def manage_users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", Role.PROCESS_OWNER)
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()

        if not username or not password or not role:
            flash("請填寫用戶名、密碼與角色。", "error")
        else:
            try:
                user_manager.create_user(username, password, role, full_name, email, department)
                audit_log_manager.add_log(
                    session.get("username", "system"),
                    "建立用戶",
                    "用戶管理",
                    f"新增用戶 {username} ({ROLE_LABELS.get(role, role)})"
                )
                flash(f"用戶 {username} 已建立。", "success")
            except ValueError as e:
                flash(str(e), "error")

    users = user_manager.list_users()
    body = ""
    body += "<div class=\"card\"><h2>用戶管理</h2>"
    body += "<p>系統管理員可以新增、啟用與停用用戶。</p></div>"
    body += "<div class=\"card\"><h3>新增用戶</h3>"
    body += "<form method=\"post\" class=\"form-grid\">"
    body += "<div class=\"form-group\"><label for=\"username\">用戶名</label><input type=\"text\" id=\"username\" name=\"username\" required placeholder=\"帳號名稱\"/></div>"
    body += "<div class=\"form-group\"><label for=\"password\">密碼</label><input type=\"password\" id=\"password\" name=\"password\" required placeholder=\"設定密碼\"/></div>"
    body += "<div class=\"form-group\"><label for=\"role\">角色</label><select id=\"role\" name=\"role\" required>"
    body += f"<option value=\"{Role.SYSTEM_ADMIN}\">{ROLE_LABELS[Role.SYSTEM_ADMIN]} (R01)</option>"
    body += f"<option value=\"{Role.AUDIT_MANAGER}\">{ROLE_LABELS[Role.AUDIT_MANAGER]} (R02)</option>"
    body += f"<option value=\"{Role.CONTROL_OWNER}\">{ROLE_LABELS[Role.CONTROL_OWNER]} (R03)</option>"
    body += f"<option value=\"{Role.TESTER}\">{ROLE_LABELS[Role.TESTER]} (R04)</option>"
    body += f"<option value=\"{Role.PROCESS_OWNER}\">{ROLE_LABELS[Role.PROCESS_OWNER]} (R05)</option>"
    body += f"<option value=\"{Role.APPROVER}\">{ROLE_LABELS[Role.APPROVER]} (R06)</option>"
    body += f"<option value=\"{Role.REVIEWER}\">{ROLE_LABELS[Role.REVIEWER]} (R07)</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"full_name\">姓名</label><input type=\"text\" id=\"full_name\" name=\"full_name\" placeholder=\"完整姓名\"/></div>"
    body += "<div class=\"form-group\"><label for=\"email\">Email</label><input type=\"email\" id=\"email\" name=\"email\" placeholder=\"電子郵件\"/></div>"
    body += "<div class=\"form-group\"><label for=\"department\">部門</label><input type=\"text\" id=\"department\" name=\"department\" placeholder=\"所屬部門\"/></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">建立用戶</button></div>"
    body += "</form></div>"
    body += "<div class=\"card\"><h3>用戶清單</h3><table class=\"table\"><thead><tr><th>ID</th><th>用戶名</th><th>角色</th><th>姓名</th><th>部門</th><th>Email</th><th>狀態</th><th>操作</th></tr></thead><tbody>"
    for user in users:
        action_label = "停用" if user.is_active() else "啟用"
        action_class = "button button-secondary" if user.is_active() else "button button-primary"
        body += f"<tr><td>{user.id}</td><td>{user.username}</td><td>{ROLE_LABELS.get(user.role, user.role)}</td><td>{user.full_name}</td><td>{user.department}</td><td>{user.email}</td><td>{user.status}</td><td class=\"action-buttons\">"
        body += f"<a class=\"button button-secondary\" href=\"{url_for('edit_user', user_id=user.id)}\">編輯</a> "
        if user.username != session.get("username"):
            body += f"<form method=\"post\" action=\"{url_for('toggle_user_status', user_id=user.id)}\" style=\"display:inline;\"><button class=\"{action_class}\" type=\"submit\">{action_label}</button></form>"
        else:
            body += f"<span style=\"color:#666; font-size:0.8rem;\">{action_label}目前登入帳號請改用編輯頁面</span>"
        body += "</td></tr>"
    body += "</tbody></table></div>"

    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/announcements/manage", methods=["GET", "POST"])
@require_login()
@require_permission("can_create_announcement")
def manage_announcements():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", ANNOUNCEMENT_CATEGORIES[0])
        importance = request.form.get("importance", IMPORTANCE_LEVELS[1])
        target_scope = request.form.get("target_scope", "全體").strip()
        due_read_date = request.form.get("due_read_date", "").strip()

        if not title or not content:
            flash("請填寫公告標題與內容。", "error")
        else:
            announcement_manager.create_announcement(title, content, category, importance, target_scope, due_read_date)
            audit_log_manager.add_log(
                session.get("username", "system"),
                "建立公告",
                "公告維護",
                f"新增公告：{title}"
            )
            flash("公告已建立，預設為草稿狀態。", "success")
            return redirect(url_for("manage_announcements"))

    announcements = announcement_manager.list_announcements(active_only=False)
    body = ""
    body += "<div class=\"card\"><h2>公告維護</h2>"
    body += "<p>系統管理員可以新增公告，並啟用/停用現有公告。</p></div>"
    body += "<div class=\"card\"><h3>新增公告</h3>"
    body += "<form method=\"post\" class=\"form-grid\">"
    body += "<div class=\"form-group\"><label for=\"title\">標題</label><input type=\"text\" id=\"title\" name=\"title\" required placeholder=\"公告標題\"/></div>"
    body += "<div class=\"form-group\"><label for=\"content\">內容</label><textarea id=\"content\" name=\"content\" rows=4 required placeholder=\"公告內容\"></textarea></div>"
    body += "<div class=\"form-group\"><label for=\"category\">分類</label><select id=\"category\" name=\"category\">"
    for category in ANNOUNCEMENT_CATEGORIES:
        body += f"<option value=\"{category}\">{category}</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"importance\">重要級</label><select id=\"importance\" name=\"importance\">"
    for importance in IMPORTANCE_LEVELS:
        body += f"<option value=\"{importance}\">{importance}</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"target_scope\">目標對象</label><input type=\"text\" id=\"target_scope\" name=\"target_scope\" value=\"全體\"/></div>"
    body += "<div class=\"form-group\"><label for=\"due_read_date\">閱讀截止日</label><input type=\"date\" id=\"due_read_date\" name=\"due_read_date\"/></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">建立公告</button></div>"
    body += "</form></div>"
    body += "<div class=\"card\"><h3>公告清單</h3><table class=\"table\"><thead><tr><th>ID</th><th>標題</th><th>分類</th><th>重要級</th><th>狀態</th><th>是否啟用</th><th>操作</th></tr></thead><tbody>"
    for item in announcements:
        status_badge = item.publish_status
        active_label = "啟用" if item.active else "停用"
        toggle_label = "停用" if item.active else "啟用"
        button_class = "button button-secondary" if item.active else "button button-primary"
        body += f"<tr><td>{item.id}</td><td>{item.current_version.title}</td><td>{item.category}</td><td>{item.importance}</td><td>{status_badge}</td><td>{active_label}</td><td class=\"action-buttons\">"
        body += f"<a class=\"button button-secondary\" href=\"{url_for('edit_announcement', announcement_id=item.id)}\">編輯</a> "
        body += f"<form method=\"post\" action=\"{url_for('toggle_announcement_active', announcement_id=item.id)}\" style=\"display:inline; margin-left:8px;\">"
        body += f"<button class=\"{button_class}\" type=\"submit\">{toggle_label}</button></form>"
        body += "</td></tr>"
    body += "</tbody></table></div>"
    body += f"<a class=\"button button-secondary\" href=\"{url_for('index')}\">回到公告中心</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/announcements/<int:announcement_id>/toggle_active", methods=["POST"])
@require_login()
@require_permission("can_delete_announcement")
def toggle_announcement_active(announcement_id):
    announcement = announcement_manager.get_announcement(announcement_id)
    if announcement is None:
        flash("找不到指定公告。", "error")
        return redirect(url_for("manage_announcements"))

    new_active = not announcement.active
    announcement_manager.update_announcement(announcement_id, is_active=1 if new_active else 0)
    action = "啟用" if new_active else "停用"
    audit_log_manager.add_log(
        get_current_role(),
        f"{action} 公告",
        "公告維護",
        f"公告 ID: {announcement_id} - {announcement.current_version.title}"
    )
    flash(f"公告已成功{action}。", "success")
    return redirect(url_for("manage_announcements"))


@app.route("/announcements/<int:announcement_id>/edit", methods=["GET", "POST"])
@require_login()
@require_permission("can_edit_announcement")
def edit_announcement(announcement_id):
    announcement = announcement_manager.get_announcement(announcement_id)
    if announcement is None:
        flash("找不到指定公告。", "error")
        return redirect(url_for("manage_announcements"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", ANNOUNCEMENT_CATEGORIES[0])
        importance = request.form.get("importance", IMPORTANCE_LEVELS[1])
        target_scope = request.form.get("target_scope", "全體").strip()
        due_read_date = request.form.get("due_read_date", "").strip()

        if not title or not content:
            flash("請填寫公告標題與內容。", "error")
        else:
            announcement_manager.update_announcement(
                announcement_id,
                title=title,
                content=content,
                category=category,
                importance=importance,
                target_scope=target_scope,
                due_read_date=due_read_date
            )
            audit_log_manager.add_log(
                session.get("username", "system"),
                "編輯公告",
                "公告維護",
                f"公告 ID: {announcement_id} - {title}"
            )
            flash("公告已更新。", "success")
            return redirect(url_for("manage_announcements"))

    body = ""
    body += f"<div class=\"card\"><h2>編輯公告：{announcement.current_version.title}</h2>"
    body += "<p>更新公告標題、內容與屬性。</p></div>"
    body += "<div class=\"card\"><form method=\"post\" class=\"form-grid\">"
    body += f"<div class=\"form-group\"><label for=\"title\">標題</label><input type=\"text\" id=\"title\" name=\"title\" value=\"{announcement.current_version.title}\" required/></div>"
    body += f"<div class=\"form-group\"><label for=\"content\">內容</label><textarea id=\"content\" name=\"content\" rows=4 required>{announcement.current_version.body}</textarea></div>"
    body += "<div class=\"form-group\"><label for=\"category\">分類</label><select id=\"category\" name=\"category\">"
    for category in ANNOUNCEMENT_CATEGORIES:
        selected = "selected" if announcement.category == category else ""
        body += f"<option value=\"{category}\" {selected}>{category}</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"importance\">重要級</label><select id=\"importance\" name=\"importance\">"
    for importance in IMPORTANCE_LEVELS:
        selected = "selected" if announcement.importance == importance else ""
        body += f"<option value=\"{importance}\" {selected}>{importance}</option>"
    body += "</select></div>"
    body += f"<div class=\"form-group\"><label for=\"target_scope\">目標對象</label><input type=\"text\" id=\"target_scope\" name=\"target_scope\" value=\"{announcement.target_scope}\"/></div>"
    body += f"<div class=\"form-group\"><label for=\"due_read_date\">閱讀截止日</label><input type=\"date\" id=\"due_read_date\" name=\"due_read_date\" value=\"{announcement.due_read_date}\"/></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">儲存變更</button>"
    body += f" <a class=\"button button-secondary\" href=\"{url_for('manage_announcements')}\">取消</a></div>"
    body += "</form></div>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/users/<int:user_id>/toggle_status", methods=["POST"])
@require_login()
@require_permission("can_manage_users")
def toggle_user_status(user_id):
    user = user_manager.get_user(user_id)
    if not user:
        flash("找不到指定用戶。", "error")
        return redirect(url_for("manage_users"))

    if user.username == session.get("username"):
        flash("無法停用目前登入帳號。", "error")
        return redirect(url_for("manage_users"))

    if user.is_active():
        user_manager.disable_user(user_id)
        action = "停用"
    else:
        user_manager.enable_user(user_id)
        action = "啟用"

    audit_log_manager.add_log(
        session.get("username", "system"),
        action,
        "用戶管理",
        f"{action} 用戶 {user.username}"
    )
    flash(f"已成功{action}用戶 {user.username}。", "success")
    return redirect(url_for("manage_users"))


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@require_login()
@require_permission("can_manage_users")
def edit_user(user_id):
    user = user_manager.get_user(user_id)
    if not user:
        flash("找不到指定用戶。", "error")
        return redirect(url_for("manage_users"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()
        role = request.form.get("role", user.role)
        status = request.form.get("status", user.status)

        if user.username == session.get("username") and status != "Active":
            flash("無法停用目前登入帳號。", "error")
            return redirect(url_for("edit_user", user_id=user_id))

        user_manager.update_user(user_id, full_name=full_name, email=email, department=department, role=role, status=status)
        audit_log_manager.add_log(
            session.get("username", "system"),
            "更新用戶",
            "用戶管理",
            f"更新用戶 {user.username} ({ROLE_LABELS.get(role, role)})"
        )
        flash(f"用戶 {user.username} 已更新。", "success")
        return redirect(url_for("manage_users"))

    body = ""
    body += f"<div class=\"card\"><h2>編輯用戶：{user.username}</h2>"
    body += "<p>可更新姓名、Email、角色與狀態。</p></div>"
    body += f"<div class=\"card\"><form method=\"post\" class=\"form-grid\">"
    body += f"<div class=\"form-group\"><label for=\"username\">用戶名</label><input type=\"text\" id=\"username\" name=\"username\" value=\"{user.username}\" disabled/></div>"
    body += f"<div class=\"form-group\"><label for=\"full_name\">姓名</label><input type=\"text\" id=\"full_name\" name=\"full_name\" value=\"{user.full_name}\"/></div>"
    body += f"<div class=\"form-group\"><label for=\"email\">Email</label><input type=\"email\" id=\"email\" name=\"email\" value=\"{user.email}\"/></div>"
    body += f"<div class=\"form-group\"><label for=\"department\">部門</label><input type=\"text\" id=\"department\" name=\"department\" value=\"{user.department}\"/></div>"
    body += f"<div class=\"form-group\"><label for=\"role\">角色</label><select id=\"role\" name=\"role\" required>"
    for role_key, role_label in ROLE_LABELS.items():
        selected = "selected" if user.role == role_key else ""
        body += f"<option value=\"{role_key}\" {selected}>{role_label}</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"status\">狀態</label><select id=\"status\" name=\"status\">"
    body += f"<option value=\"Active\" {'selected' if user.status == 'Active' else ''}>Active</option>"
    body += f"<option value=\"Inactive\" {'selected' if user.status == 'Inactive' else ''}>Inactive</option>"
    body += "</select></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">儲存變更</button>"
    body += f" <a class=\"button button-secondary\" href=\"{url_for('manage_users')}\">返回用戶管理</a></div>"
    body += "</form></div>"

    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/resources")
@require_login()
def resources():
    categories = resource_manager.list_categories()
    body = f"""
    <div class=\"card\">
      <h2>制度資源庫</h2>
      <p>目前管理 {resource_manager.total_categories()} 個分類、{resource_manager.total_links()} 個連結。</p>
    </div>
    """

    for category in categories:
        # 只顯示有啟用資源的分類
        active_links = [link for link in category.links if link.active]
        if not active_links:
            continue
            
        body += f"<div class=\"card\"><div class=\"category\">{category.name}</div><p>{category.description}</p>"
        body += "<div class=\"resource-grid\">"
        for link in active_links:
            status_text = "正常" if link.active else "失效"
            status_class = "badge badge-low" if link.active else "badge badge-medium"
            body += f"<div class=\"resource-item\">"
            body += f"<h4><a href=\"{link.url}\" target=\"_blank\">{link.title}</a></h4>"
            body += f"<div class=\"resource-meta\"><span>{link.description}</span><span class=\"{status_class}\">狀態：{status_text}</span><span>敏感度：{link.sensitivity}</span><span>檢查：{link.last_checked}</span></div>"
            body += f"</div>"
        body += "</div></div>"

    body += f"<a class=\"button button-secondary\" href=\"{url_for('index')}\">回到公告中心</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/resources/manage", methods=["GET", "POST"])
@require_login()
@require_permission("can_manage_resources")
def manage_resources():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        file_path = request.form.get("file_path", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not category or not file_path:
            flash("請填寫資源名稱、分類與檔案路徑。", "error")
        else:
            resource_manager.add_resource(name, category, file_path, description, session.get("username", "system"))
            audit_log_manager.add_log(
                session.get("username", "system"),
                "建立資源",
                "資源維護",
                f"新增資源：{name}"
            )
            flash("資源已建立。", "success")
            return redirect(url_for("manage_resources"))

    resources = resource_manager.list_all_resources()
    body = ""
    body += "<div class=\"card\"><h2>資源庫維護</h2>"
    body += "<p>稽核主管可以新增資源，並啟用/停用現有資源。</p></div>"
    body += "<div class=\"card\"><h3>新增資源</h3>"
    body += "<form method=\"post\" class=\"form-grid\">"
    body += "<div class=\"form-group\"><label for=\"name\">資源名稱</label><input type=\"text\" id=\"name\" name=\"name\" required placeholder=\"資源標題\"/></div>"
    body += "<div class=\"form-group\"><label for=\"category\">分類</label><input type=\"text\" id=\"category\" name=\"category\" required placeholder=\"例如：法規、政策、程序\"/></div>"
    body += "<div class=\"form-group\"><label for=\"file_path\">檔案路徑/URL</label><input type=\"text\" id=\"file_path\" name=\"file_path\" required placeholder=\"檔案路徑或外部連結\"/></div>"
    body += "<div class=\"form-group\"><label for=\"description\">描述</label><textarea id=\"description\" name=\"description\" rows=3 placeholder=\"資源簡要說明\"></textarea></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">建立資源</button></div>"
    body += "</form></div>"
    body += "<div class=\"card\"><h3>資源清單</h3><table class=\"table\"><thead><tr><th>ID</th><th>名稱</th><th>分類</th><th>路徑</th><th>狀態</th><th>操作</th></tr></thead><tbody>"
    for resource in resources:
        status_text = "啟用" if resource.active else "停用"
        toggle_label = "停用" if resource.active else "啟用"
        button_class = "button button-secondary" if resource.active else "button button-primary"
        body += f"<tr><td>{resource.id}</td><td>{resource.title}</td><td>{resource.category}</td><td>{resource.url}</td><td>{status_text}</td><td class=\"action-buttons\">"
        body += f"<a class=\"button button-secondary\" href=\"{url_for('edit_resource', resource_id=resource.id)}\">編輯</a> "
        body += f"<form method=\"post\" action=\"{url_for('toggle_resource_active', resource_id=resource.id)}\" style=\"display:inline; margin-left:8px;\">"
        body += f"<button class=\"{button_class}\" type=\"submit\">{toggle_label}</button></form>"
        body += "</td></tr>"
    body += "</tbody></table></div>"
    body += f"<a class=\"button button-secondary\" href=\"{url_for('resources')}\">回到資源庫</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/resources/<int:resource_id>/edit", methods=["GET", "POST"])
@require_login()
@require_permission("can_manage_resources")
def edit_resource(resource_id):
    try:
        resource = resource_manager.get_resource(resource_id)
    except KeyError:
        flash("找不到指定資源。", "error")
        return redirect(url_for("manage_resources"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        file_path = request.form.get("file_path", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not category or not file_path:
            flash("請填寫資源名稱、分類與檔案路徑。", "error")
        else:
            resource_manager.update_resource(
                resource_id,
                name=name,
                category=category,
                file_path=file_path,
                description=description
            )
            audit_log_manager.add_log(
                session.get("username", "system"),
                "編輯資源",
                "資源維護",
                f"資源 ID: {resource_id} - {name}"
            )
            flash("資源已更新。", "success")
            return redirect(url_for("manage_resources"))

    body = ""
    body += f"<div class=\"card\"><h2>編輯資源：{resource.title}</h2>"
    body += "<p>更新資源名稱、分類與路徑。</p></div>"
    body += "<div class=\"card\"><form method=\"post\" class=\"form-grid\">"
    body += f"<div class=\"form-group\"><label for=\"name\">資源名稱</label><input type=\"text\" id=\"name\" name=\"name\" value=\"{resource.title}\" required/></div>"
    body += f"<div class=\"form-group\"><label for=\"category\">分類</label><input type=\"text\" id=\"category\" name=\"category\" value=\"{resource.category}\" required/></div>"
    body += f"<div class=\"form-group\"><label for=\"file_path\">檔案路徑/URL</label><input type=\"text\" id=\"file_path\" name=\"file_path\" value=\"{resource.url}\" required/></div>"
    body += f"<div class=\"form-group\"><label for=\"description\">描述</label><textarea id=\"description\" name=\"description\" rows=3>{resource.description}</textarea></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">儲存變更</button>"
    body += f" <a class=\"button button-secondary\" href=\"{url_for('manage_resources')}\">取消</a></div>"
    body += "</form></div>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/resources/<int:resource_id>/toggle_active", methods=["POST"])
@require_login()
@require_permission("can_manage_resources")
def toggle_resource_active(resource_id):
    try:
        resource = resource_manager.get_resource(resource_id)
        resource_manager.toggle_active(resource_id)
        new_status = "停用" if resource.active else "啟用"
        audit_log_manager.add_log(
            get_current_role(),
            f"{new_status} 資源",
            "資源維護",
            f"資源 ID: {resource_id} - {resource.title}"
        )
        flash(f"資源已成功{new_status}。", "success")
    except KeyError:
        flash("找不到指定資源。", "error")
    
    return redirect(url_for("manage_resources"))


@app.route("/audit_logs")
@require_login()
def audit_logs():
    if get_current_role() != Role.SYSTEM_ADMIN:
        flash("您沒有權限檢視稽核日誌。", "error")
        return redirect(url_for("index"))

    logs = audit_log_manager.get_logs()
    body = f"""
    <div class=\"card\">
      <h2>稽核日誌</h2>
      <p>記錄所有系統操作軌跡，確保可追蹤與可驗證。</p>
    </div>
    <div class=\"card\">
      <h3>操作日誌</h3>
      <table class=\"issue-table\">
        <thead>
          <tr><th>時間</th><th>用戶</th><th>操作</th><th>資源</th><th>詳細內容</th></tr>
        </thead>
        <tbody>
    """
    for log in logs:
        body += f"<tr><td>{log.timestamp}</td><td>{log.user}</td><td>{log.action}</td><td>{log.resource}</td><td>{log.details}</td></tr>"
    body += "</tbody></table></div>"
    body += f"<a class=\"button button-secondary\" href=\"{url_for('index')}\">回到公告中心</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


# ==================== 管理儀表板 ====================
dashboard_manager = DashboardManager(issue_manager, control_manager)


@app.route("/dashboard")
@require_login()
def dashboard():
    """管理儀表板 (7.7)"""
    if not has_permission("can_view_audit_logs"):
        flash("您沒有權限檢視儀表板。")
        return redirect(url_for("index"))
    
    metrics = dashboard_manager.get_dashboard_metrics()
    
    body = f"""\
    <div class="card">
      <h2>管理儀表板</h2>
      <p>即時掌握內控治理狀況與關鍵指標。</p>
    </div>
    
    <div class="summary-grid">
      <div class="summary-card">
        <strong>RPT-01 開啟中 Issue</strong>
        <p>{metrics['RPT-01']['value']} 件</p>
        <small>{metrics['RPT-01']['detail']}</small>
      </div>
      <div class="summary-card">
        <strong>RPT-02 高風險占比</strong>
        <p>{metrics['RPT-02']['value']}%</p>
        <small>{metrics['RPT-02']['detail']}</small>
      </div>
      <div class="summary-card">
        <strong>RPT-03 逾期 Issue</strong>
        <p>{metrics['RPT-03']['value']} 件</p>
        <small>{metrics['RPT-03']['detail']}</small>
      </div>
      <div class="summary-card">
        <strong>RPT-04 平均逾期天數</strong>
        <p>{metrics['RPT-04']['value']} 天</p>
      </div>
    </div>
    
    <div class="summary-grid">
      <div class="summary-card">
        <strong>RPT-06 控制測試完成率</strong>
        <p>{metrics['RPT-06']['value']}%</p>
        <small>{metrics['RPT-06']['detail']}</small>
      </div>
      <div class="summary-card">
        <strong>RPT-07 控制測試逾期率</strong>
        <p>{metrics['RPT-07']['value']}%</p>
        <small>{metrics['RPT-07']['detail']}</small>
      </div>
      <div class="summary-card">
        <strong>RPT-08 重複發生比率</strong>
        <p>{metrics['RPT-08']['value']}%</p>
        <small>{metrics['RPT-08']['detail']}</small>
      </div>
      <div class="summary-card">
        <strong>RPT-11 無控制高風險流程</strong>
        <p>{metrics['RPT-11']['value']} 個</p>
        <small>{metrics['RPT-11']['detail']}</small>
      </div>
    </div>
    
    <div class="card">
      <h3>RPT-10 各流程控制覆蓋率</h3>
      <table class="issue-table">
        <thead>
          <tr><th>流程</th><th>覆蓋率</th><th>狀態</th></tr>
        </thead>
        <tbody>
"""
    for process, coverage in metrics['RPT-10']['value'].items():
        status_class = "badge-low" if coverage >= 80 else ("badge-medium" if coverage >= 50 else "badge-high")
        body += f"<tr><td>{process}</td><td>{coverage}%</td><td><span class=\"badge {status_class}\">{'良好' if coverage >= 80 else ('普通' if coverage >= 50 else '不足')}</span></td></tr>"
    body += """</tbody></table></div>
    </div>
    
    <div class="card-grid">
      <div class="card">
      <h3>報表匯出 (RPT-12 ~ RPT-17)</h3>
      <p>選擇報表類型並填寫匯出用途：</p>
      <form method="post" action="/export_report">
        <div class="form-group">
          <label>報表類型</label>
          <select name="report_type">
            <option value="issue_tracker">Issue 追蹤明細報表</option>
            <option value="control_test">控制測試執行情形報表</option>
            <option value="overdue">逾期事項分層報表</option>
            <option value="coverage">控制覆蓋率報表</option>
          </select>
        </div>
        <div class="form-group">
          <label>匯出用途 (必填)</label>
          <input type="text" name="purpose" placeholder="說明匯出此報表的用途" required/>
        </div>
        <button class="button" type="submit">匯出報表</button>
      </form>
    </div>
  </div>
    
    <a class="button button-secondary" href="/">回到公告中心</a>
"""
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/export_report", methods=["POST"])
def export_report():
    """匯出報表 (7.7.2, 7.7.3)"""
    from flask import Response
    import csv
    import io
    
    if not has_permission("can_export_data"):
        flash("您沒有權限匯出報表。")
        return redirect(url_for("dashboard"))
    
    report_type = request.form.get("report_type", "")
    purpose = request.form.get("purpose", "").strip()
    
    if not purpose:
        flash("請填寫匯出用途。")
        return redirect(url_for("dashboard"))
    
    # 記錄匯出 (RPT-17)
    export_log.log_export(
        exporter=get_current_role(),
        report_name=report_type,
        purpose=purpose,
    )
    
    # 產生報表資料
    report_data = dashboard_manager.generate_report_data(report_type)
    
    audit_log_manager.add_log(
        get_current_role(),
        "匯出報表",
        "儀表板",
        f"匯出 {report_type} 報表，用途：{purpose}"
    )
    
    # 產生 CSV 檔案
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 標題
    report_names = {
        "issue_tracker": "Issue 追蹤明細報表",
        "control_test": "控制測試執行情形報表",
        "overdue": "逾期事項分層報表",
        "coverage": "控制覆蓋率報表",
    }
    writer.writerow([report_names.get(report_type, report_type)])
    writer.writerow(["匯出用途:", purpose])
    writer.writerow(["匯出時間:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    
    # 根據報表類型寫入資料
    if report_type == "issue_tracker":
        writer.writerow(["狀態分布", "數量"])
        for status, count in report_data.get("by_status", {}).items():
            writer.writerow([status, count])
        writer.writerow([])
        writer.writerow(["風險分布", "數量"])
        for risk, count in report_data.get("by_risk", {}).items():
            writer.writerow([risk, count])
    elif report_type == "control_test":
        writer.writerow(["控制點總數", report_data.get("total", 0)])
        writer.writerow(["狀態分布", "數量"])
        for status, count in report_data.get("by_status", {}).items():
            writer.writerow([status, count])
    elif report_type == "overdue":
        writer.writerow(["逾期 Issue 數", report_data.get("issue_overdue", 0)])
        writer.writerow(["逾期控制點數", report_data.get("control_overdue", 0)])
        writer.writerow([])
        writer.writerow(["逾期天數分層", "數量"])
        for layer, count in report_data.get("layers", {}).items():
            writer.writerow([layer, count])
    elif report_type == "coverage":
        writer.writerow(["流程", "覆蓋率"])
        for process, coverage in report_data.get("process_coverage", {}).items():
            writer.writerow([process, f"{coverage}%"])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={report_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"}
    )


@app.route("/issues", methods=["GET", "POST"])
@require_login()
def issues():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        finding = request.form.get("finding", "").strip()
        risk_level = request.form.get("risk_level", "M")
        control_id = request.form.get("control_id", "").strip()
        recommendation = request.form.get("recommendation", "").strip()
        owner = request.form.get("owner", "未指定").strip()
        if title and finding and control_id and recommendation:
            issue_manager.create_issue(title, finding, risk_level, control_id, recommendation, owner, "2026-04-19")
            audit_log_manager.add_log("admin", "建立 Issue", "Issue Tracker", f"建立新 Issue：{title}")
            flash("已成功建立新的 Issue。")
            return redirect(url_for("issues"))
        flash("請填寫所有必要欄位。")

    issues = issue_manager.list_issues()
    body = f"""
    <div class=\"card\">
      <h2>Issue Tracker</h2>
      <p>追蹤缺陷修復工作流：Open -&gt; Assigned -&gt; Plan -&gt; In Progress -&gt; Verification -&gt; Closed。</p>
    </div>
    <div class=\"card\">
      <h3>建立新 Issue</h3>
      <form method=\"post\">
        <div class=\"form-group\"><label>標題</label><input name=\"title\" required/></div>
        <div class=\"form-group\"><label>發現點 (Finding)</label><textarea name=\"finding\" rows=3 required></textarea></div>
        <div class=\"form-group\"><label>風險等級</label><select name=\"risk_level\"><option value=\"H\">高</option><option value=\"M\" selected>中</option><option value=\"L\">低</option></select></div>
        <div class=\"form-group\"><label>控制 ID</label><input name=\"control_id\" required/></div>
        <div class=\"form-group\"><label>建議方案</label><textarea name=\"recommendation\" rows=3 required></textarea></div>
        <div class=\"form-group\"><label>負責人</label><input name=\"owner\" placeholder=\"例如 IT 運維\"/></div>
        <button class=\"button\" type=\"submit\">建立 Issue</button>
      </form>
    </div>
    <div class=\"card\">
      <h3>目前 Issue 列表</h3>
      <table class=\"issue-table\">
        <thead>
          <tr><th>ID</th><th>標題</th><th>風險</th><th>狀態</th><th>負責人</th><th>最後更新</th></tr>
        </thead>
        <tbody>
    """
    for issue in issues:
        body += f"<tr><td>{issue.id}</td><td><a href=\"{url_for('issue_detail', issue_id=issue.id)}\">{issue.title}</a></td><td>{PRIORITY_LABELS.get(issue.risk_level, issue.risk_level)}</td><td>{issue.status}</td><td>{issue.owner}</td><td>{issue.updated_at}</td></tr>"
    body += "</tbody></table></div>"
    body += f"<a class=\"button button-secondary\" href=\"{url_for('index')}\">回到公告中心</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/issues/<int:issue_id>", methods=["GET", "POST"])
@require_login()
def issue_detail(issue_id):
    issue = issue_manager.get_issue(issue_id)
    if issue is None:
        flash("找不到指定的 Issue。")
        return redirect(url_for("issues"))

    # 處理證據上傳
    if request.method == "POST" and "evidence" in request.form:
        evidence = request.form.get("evidence", "").strip()
        if evidence:
            issue.evidence.append(evidence)
            audit_log_manager.add_log(
                get_current_role(),
                "上傳證據",
                "Issue Tracker",
                f"Issue ID: {issue_id} - 新增證據: {evidence}"
            )
            flash("已成功上傳證明文件。")

    next_states = issue.next_statuses()
    finding_html = issue.finding.replace('\n', '<br>')
    recommendation_html = issue.recommendation.replace('\n', '<br>')
    
    # 權限檢查
    can_transition = has_permission("can_transition_issue")
    can_add_evidence = has_permission("can_transition_issue")
    
    # 逾期顯示
    overdue_warning = ""
    if issue.is_overdue():
        overdue_warning = f"<span class=\"badge badge-high\" style=\"margin-left: 8px;\">⚠️ 已逾期</span>"
    elif issue.days_until_due() <= 7 and issue.days_until_due() > 0:
        overdue_warning = f"<span class=\"badge badge-medium\" style=\"margin-left: 8px;\">🔶 將於 {issue.days_until_due()} 天後到期</span>"
    
    # 延期狀態顯示
    extension_display = ""
    if issue.extension_status:
        ext_class = "badge-low" if issue.extension_status == "已核准延期" else ("badge-high" if issue.extension_status == "已駁回延期" else "badge-medium")
        extension_display = f"<span class=\"badge {ext_class}\">{issue.extension_status}</span>"
    
    body = f"""
    <div class="card">
      <h2>Issue 詳細</h2>
      <div class="announcement-meta">
        <span><strong>控制 ID：</strong>{issue.control_id}</span>
        <span><strong>風險等級：</strong>{PRIORITY_LABELS.get(issue.risk_level, issue.risk_level)}</span>
        <span><strong>狀態：</strong>{issue.status}</span>
        {extension_display}
        {overdue_warning}
        <span><strong>負責人：</strong>{issue.owner}</span>
      </div>
      <h3>{issue.title}</h3>
      <p><strong>缺失類型：</strong>{issue.issue_type or '-'}</p>
      <p><strong>根因分類：</strong>{issue.root_cause or '-'}</p>
      <p><strong>影響範圍：</strong>{issue.impact_scope or '-'}</p>
      <p><strong>預計完成日：</strong>{issue.planned_due_date or '-'}</p>
      <p><strong>補償性控制：</strong>{issue.compensating_control or '-'}</p>
      <p><strong>重複發生：</strong>{'是' if issue.recurring_flag else '否'}</p>
      <p><strong>發現點：</strong><br>{finding_html}</p>
      <p><strong>建議方案：</strong><br>{recommendation_html}</p>
      <p><strong>建立：</strong>{issue.created_at}，<strong>更新：</strong>{issue.updated_at}</p>
    </div>
    """
    
    # 證據區塊
    if issue.evidence:
        evidence_html = "".join(f"<li>{item}</li>" for item in issue.evidence)
        body += f"<div class=\"card\"><h3>證據文件</h3><ul>{evidence_html}</ul></div>"
    
    # 證據上傳表單（僅有權限者可見）
    if can_add_evidence:
        body += f"""
        <div class="card">
          <h3>上傳證據</h3>
          <form method="post">
            <div class="form-group">
              <label>新增證明文件</label>
              <input type="text" name="evidence" placeholder="例如：截圖、修訂文件、報告等"/>
            </div>
            <button class="button" type="submit">上傳證據</button>
          </form>
        </div>
        """

    # 工作流轉換（僅有權限者可見）
    if next_states and can_transition:
        # 檢查是否需要強制上傳證據
        can_transition_check, message = can_transition_to_verification(issue_id)
        
        body += f"<div class=\"card\"><h3>工作流轉換</h3>"
        if not can_transition_check:
            body += f"<div class=\"alert\" style=\"background: var(--badge-high); color: var(--badge-high-text);\">{message}</div>"
        body += f"<form method=\"post\" action=\"{url_for('transition_issue', issue_id=issue.id)}\">"
        body += f"<div class=\"form-group\"><label>選擇下一個狀態</label><select name=\"new_status\" onchange=\"toggleExtensionFields(this.value)\">"
        for state in next_states:
            body += f"<option value=\"{state}\">{state}</option>"
        body += "</select></div>"
        
        # 延期申請欄位 (ISS-08)
        body += """
        <div id="extension_fields" style="display: none;">
          <div class="form-group">
            <label>延期原因</label>
            <textarea name="extension_reason" rows="3" placeholder="說明申請延期的原因..."></textarea>
          </div>
          <div class="form-group">
            <label>新的預計完成日</label>
            <input type="date" name="extension_new_date"/>
          </div>
        </div>
        """
        body += f"<button class=\"button\" type=\"submit\" {'disabled' if not can_transition_check else ''}>進行狀態轉換</button>"
        body += "</form>"
        body += """
        <script>
        function toggleExtensionFields(status) {
          var fields = document.getElementById('extension_fields');
          if (status === '延期申請中') {
            fields.style.display = 'block';
          } else {
            fields.style.display = 'none';
          }
        }
        </script>
        """
        body += "</div>"
    elif not can_transition:
        body += f"<div class=\"card\"><p style=\"color: var(--text-muted);\">您沒有權限進行狀態轉換。</p></div>"
    else:
        body += f"<div class=\"card\"><strong>此 Issue 已結案。</strong></div>"

    body += f"<a class=\"button button-secondary\" href=\"{url_for('issues')}\">返回 Issue 列表</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/issues/<int:issue_id>/transition", methods=["POST"])
def transition_issue(issue_id):
    new_status = request.form.get("new_status", "")
    
    issue = issue_manager.get_issue(issue_id)
    if issue is None:
        flash("找不到指定的 Issue。")
        return redirect(url_for("issues"))
    
    # 延期申請處理
    if new_status == "延期申請中":
        extension_reason = request.form.get("extension_reason", "").strip()
        extension_new_date = request.form.get("extension_new_date", "").strip()
        if not extension_reason or not extension_new_date:
            flash("請填寫延期原因與新的完成日。")
            return redirect(url_for("issue_detail", issue_id=issue_id))
        issue.extension_status = "延期申請中"
        issue.extension_reason = extension_reason
        issue.extension_new_date = extension_new_date
        audit_log_manager.add_log(
            get_current_role(),
            "申請延期",
            "Issue Tracker",
            f"Issue ID: {issue_id} 申請延期至 {extension_new_date}"
        )
        flash("延期申請已提交，等待核准。")
        return redirect(url_for("issue_detail", issue_id=issue_id))
    
    # 延期核准/駁回處理
    if issue.extension_status == "延期申請中" and new_status in ["已核准延期", "已駁回延期"]:
        issue.extension_status = new_status
        if new_status == "已核准延期":
            issue.planned_due_date = issue.extension_new_date
        audit_log_manager.add_log(
            get_current_role(),
            "延期審核",
            "Issue Tracker",
            f"Issue ID: {issue_id} 延期申請結果：{new_status}"
        )
        flash(f"延期申請已{new_status}。")
        return redirect(url_for("issue_detail", issue_id=issue_id))
    
    # 正常流程轉換 - 證據強制化檢查
    can_transition, message = can_transition_to_verification(issue_id)
    if not can_transition:
        flash(message, "error")
        return redirect(url_for("issue_detail", issue_id=issue_id))
    
    succeeded = issue_manager.transition_issue(issue_id, new_status, "2026-04-27")
    if succeeded:
        audit_log_manager.add_log(
            get_current_role(), 
            "狀態轉換", 
            "Issue Tracker", 
            f"將 Issue ID: {issue_id} 從目前狀態轉換到 {new_status}"
        )
        flash("已成功將 Issue 轉換到下一個狀態。")
    else:
        flash("狀態轉換失敗，請確認工作流順序。")
    return redirect(url_for("issue_detail", issue_id=issue_id))


@app.route("/announcement/<int:announcement_id>")
@require_login()
def announcement_detail(announcement_id):
    announcement = announcement_manager.get_announcement(announcement_id)
    if announcement is None:
        return redirect(url_for("index"))

    read_ids = set(session.get("read_announcements", []))
    unread_notice = announcement.force_read and announcement.id not in read_ids
    versions_html = ""
    for version in announcement.all_versions():
        versions_html += f"<li><strong>{version.version_label}</strong> - {version.published_at}</li>"

    diff_section = ""
    if announcement.version_history:
        diff_text = announcement.diff_with_version(announcement.version_history[0].version_label)
        diff_section = f"<h4>版本差異 ({announcement.version_history[0].version_label} -&gt; {announcement.current_version.version_label})</h4><pre>{diff_text}</pre>"

    body_html = announcement.current_version.body.replace('\n', '<br>')
    
    # 狀態顯示
    status_class = {
        "草稿": "badge-medium",
        "審核中": "badge-high",
        "已發布": "badge-low",
        "已歸檔": "",
    }.get(announcement.publish_status, "")
    
    body = f"""
    <div class="card">
      <div class="category">{announcement.category}</div>
      <h2>{announcement.current_version.title}</h2>
      <span class="{get_importance_badge(announcement.importance)}">重要級：{announcement.importance}</span>
      <span class="badge {status_class}">狀態：{announcement.publish_status}</span>
      <p>發布日期：{announcement.current_version.published_at}</p>
      <p>目標對象：{announcement.target_scope}</p>
      <p>{body_html}</p>
      <div>
        <h4>版本歷程</h4>
        <ul>{versions_html}</ul>
      </div>
      {diff_section}
    </div>
    """

    # 狀態轉換區塊 (僅有權限者可見)
    if has_permission("can_publish_announcement") and announcement.next_statuses():
        body += f"""
        <div class="card">
          <h3>公告狀態管理</h3>
          <form method="post" action="{url_for('transition_announcement', announcement_id=announcement.id)}">
            <div class="form-group">
              <label>轉換狀態</label>
              <select name="new_status">
                {"".join(f'<option value="{s}">{s}</option>' for s in announcement.next_statuses())}
              </select>
            </div>
            <button class="button" type="submit">更新狀態</button>
          </form>
        </div>
        """

    if unread_notice:
        body += f"<div class=\"card\"><strong>此公告為高重要級，請確認已閱讀以解除限制。</strong><br><a class=\"button\" href=\"{url_for('confirm_read', announcement_id=announcement.id)}\">確認已閱讀</a></div>"

    body += f"<a class=\"button button-secondary\" href=\"{url_for('index')}\">返回公告列表</a>"

    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/announcement/<int:announcement_id>/transition", methods=["POST"])
def transition_announcement(announcement_id):
    """公告狀態轉換"""
    if not has_permission("can_publish_announcement"):
        flash("您沒有權限執行此操作。", "error")
        return redirect(url_for("announcement_detail", announcement_id=announcement_id))
    
    announcement = announcement_manager.get_announcement(announcement_id)
    if announcement is None:
        flash("找不到指定的公告。")
        return redirect(url_for("index"))
    
    new_status = request.form.get("new_status", "")
    if new_status and announcement.can_transition_to(new_status):
        announcement.publish_status = new_status
        audit_log_manager.add_log(
            get_current_role(),
            "公告狀態轉換",
            "公告中心",
            f"公告 ID: {announcement_id} 狀態變更為 {new_status}"
        )
        flash(f"公告狀態已更新為：{new_status}")
    else:
        flash("無效的狀態轉換。")
    
    return redirect(url_for("announcement_detail", announcement_id=announcement_id))


@app.route("/confirm_read/<int:announcement_id>")
def confirm_read(announcement_id):
    announcement = announcement_manager.get_announcement(announcement_id)
    if announcement is None:
        return redirect(url_for("index"))

    read_ids = set(session.get("read_announcements", []))
    read_ids.add(announcement_id)
    session["read_announcements"] = list(read_ids)
    audit_log_manager.add_log(
        get_current_role(), 
        "確認閱讀", 
        "公告中心", 
        f"確認閱讀公告 ID: {announcement_id} - {announcement.current_version.title}"
    )
    flash("已成功確認閱讀，感謝您的配合。")
    return redirect(url_for("announcement_detail", announcement_id=announcement_id))




# ==================== 控制點矩陣管理路由 ====================

@app.route("/controls", methods=["GET", "POST"])
@require_login()
def controls():
    """控制點矩陣首頁"""
    # 處理篩選
    process_filter = request.args.get("process", "")
    risk_filter = request.args.get("risk", "")
    status_filter = request.args.get("status", "")
    keyword = request.args.get("keyword", "")
    
    # 搜尋控制點
    if process_filter or risk_filter or status_filter or keyword:
        controls = control_manager.search_controls(
            process=process_filter if process_filter else None,
            risk_level=risk_filter if risk_filter else None,
            status=status_filter if status_filter else None,
            keyword=keyword if keyword else None,
        )
    else:
        controls = control_manager.list_controls()
    
    # 取得統計資料
    stats = control_manager.get_coverage_stats()
    upcoming = control_manager.get_upcoming_tests(30)
    overdue = control_manager.get_overdue_controls()
    
    body = f"""
    <div class="summary-grid">
      <div class="summary-card">
        <strong>總控制點</strong>
        <p>{stats['total']} 點</p>
      </div>
      <div class="summary-card">
        <strong>有效控制</strong>
        <p>{stats['active']} 點</p>
        <small>覆蓋率：{stats['coverage']}%</small>
      </div>
      <div class="summary-card">
        <strong>即將到期</strong>
        <p>{len(upcoming)} 點</p>
        <small>30 天內</small>
      </div>
      <div class="summary-card">
        <strong>逾期未測</strong>
        <p>{len(overdue)} 點</p>
      </div>
    </div>
    
    <div class="card">
      <h2>控制點矩陣</h2>
      <p>管理內控控制點、追蹤測試排程與結果。</p>
    </div>
    
    <!-- 篩選表單 -->
    <div class="card">
      <h3>篩選控制點</h3>
      <form method="get" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end;">
        <div class="form-group" style="flex: 1; min-width: 150px; margin-bottom: 0;">
          <label>業務流程</label>
          <select name="process">
            <option value="">全部流程</option>
            {"".join(f'<option value="{p}" {"selected" if p == process_filter else ""}>{p}</option>' for p in PROCESSES)}
          </select>
        </div>
        <div class="form-group" style="flex: 1; min-width: 120px; margin-bottom: 0;">
          <label>風險等級</label>
          <select name="risk">
            <option value="">全部</option>
            <option value="H" {"selected" if risk_filter == "H" else ""}>高</option>
            <option value="M" {"selected" if risk_filter == "M" else ""}>中</option>
            <option value="L" {"selected" if risk_filter == "L" else ""}>低</option>
          </select>
        </div>
        <div class="form-group" style="flex: 1; min-width: 120px; margin-bottom: 0;">
          <label>狀態</label>
          <select name="status">
            <option value="">全部狀態</option>
            <option value="有效" {"selected" if status_filter == "有效" else ""}>有效</option>
            <option value="停用" {"selected" if status_filter == "停用" else ""}>停用</option>
            <option value="審查中" {"selected" if status_filter == "審查中" else ""}>審查中</option>
          </select>
        </div>
        <div class="form-group" style="flex: 2; min-width: 200px; margin-bottom: 0;">
          <label>關鍵字搜尋</label>
          <input type="text" name="keyword" placeholder="控制點名稱或描述..." value="{keyword}"/>
        </div>
        <button class="button" type="submit">篩選</button>
        <a class="button button-secondary" href="{url_for('controls')}">清除篩選</a>
      </form>
    </div>
    
    <!-- 控制點列表 -->
    <div class="card">
      <h3>控制點列表 ({len(controls)} 點)</h3>
      <table class="issue-table">
        <thead>
          <tr><th>控制點ID</th><th>控制點名稱</th><th>流程</th><th>分類</th><th>風險</th><th>最後測試</th><th>下次測試</th><th>狀態</th></tr>
        </thead>
        <tbody>
    """
    
    for ctrl in controls:
        risk_class = "badge-high" if ctrl.risk_level == "H" else ("badge-medium" if ctrl.risk_level == "M" else "badge-low")
        risk_label = RISK_LEVELS.get(ctrl.risk_level, ctrl.risk_level)
        status_class = "badge-low" if ctrl.status == "有效" else ("badge-medium" if ctrl.status == "審查中" else "")
        next_test_display = ctrl.next_test_date
        if ctrl.is_overdue():
            next_test_display = f"⚠️ {ctrl.next_test_date} (逾期)"
        elif ctrl.days_until_test() <= 14:
            next_test_display = f"🔶 {ctrl.next_test_date}"
        
        body += f"""<tr>
            <td><a href="{url_for('control_detail', control_id=ctrl.id)}">{ctrl.id}</a></td>
            <td>{ctrl.name}</td>
            <td>{ctrl.process}</td>
            <td>{ctrl.category}</td>
            <td><span class="badge {risk_class}">{risk_label}</span></td>
            <td>{ctrl.last_test_date or '-'}</td>
            <td>{next_test_display}</td>
            <td><span class="badge {status_class}">{ctrl.status}</span></td>
        </tr>"""
    
    body += """</tbody></table></div>"""
    body += f"<a class=\"button button-secondary\" href=\"{url_for('index')}\">回到公告中心</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/controls/<control_id>")
@require_login()
def control_detail(control_id):
    """控制點詳情頁面"""
    ctrl = control_manager.get_control(control_id)
    if ctrl is None:
        flash("找不到指定的控制點。")
        return redirect(url_for("controls"))
    
    tests = control_manager.get_control_tests(control_id)
    risk_class = "badge-high" if ctrl.risk_level == "H" else ("badge-medium" if ctrl.risk_level == "M" else "badge-low")
    risk_label = RISK_LEVELS.get(ctrl.risk_level, ctrl.risk_level)
    
    related_issues_html = ""
    if ctrl.related_issues:
        for issue_id in ctrl.related_issues:
            issue = issue_manager.get_issue(issue_id)
            if issue:
                related_issues_html += f"<li><a href=\"{url_for('issue_detail', issue_id=issue.id)}\">#{issue.id} {issue.title}</a> ({issue.status})</li>"
    
    # 狀態顯示
    status_class = {
        "排程建立": "badge-medium",
        "待執行": "badge-high",
        "測試中": "badge-high",
        "待覆核": "badge-medium",
        "已完成": "badge-low",
    }.get(ctrl.test_status, "")
    
    body = f"""
    <div class="card">
      <h2>控制點詳情</h2>
      <div class="announcement-meta">
        <span><strong>控制點ID：</strong>{ctrl.id}</span>
        <span><strong>版本：</strong>{ctrl.version_no}</span>
        <span><strong>風險等級：</strong><span class="badge {risk_class}">{risk_label}</span></span>
        <span><strong>控制狀態：</strong>{ctrl.status}</span>
        <span><strong>測試流程：</strong><span class="badge {status_class}">{ctrl.test_status}</span></span>
      </div>
      <h3>{ctrl.name}</h3>
    </div>
    
    <div class="card">
      <h3>基本資訊</h3>
      <p><strong>控制目標：</strong>{ctrl.control_objective or '-'}</p>
      <p><strong>所屬流程：</strong>{ctrl.process}</p>
      <p><strong>控制分類：</strong>{ctrl.category}</p>
      <p><strong>控制類型：</strong>{ctrl.control_type or '-'}</p>
      <p><strong>控制模式：</strong>{ctrl.control_mode or '-'}</p>
      <p><strong>關鍵控制：</strong>{'是' if ctrl.key_control_flag else '否'}</p>
      <p><strong>負責部門：</strong>{ctrl.owner_dept}</p>
      <p><strong>負責人：</strong>{ctrl.owner_user}</p>
      <p><strong>控制描述：</strong><br>{ctrl.description}</p>
      <p><strong>生效日：</strong>{ctrl.effective_from or '-'} | <strong>失效日：</strong>{ctrl.effective_to or '-'}</p>
    </div>
    
    <div class="card">
      <h3>測試排程</h3>
      <p><strong>測試頻率：</strong>{ctrl.test_frequency}</p>
      <p><strong>最後測試：</strong>{ctrl.last_test_date or '尚未測試'}</p>
      <p><strong>最後結果：</strong>{ctrl.last_test_result}</p>
      <p><strong>下次測試：</strong>{ctrl.next_test_date or '待計算'}</p>
    </div>
    
    <div class="card">
      <h3>測試歷史記錄</h3>
    """
    if tests:
        body += "<table class=\"issue-table\"><thead><tr><th>測試日期</th><th>流程狀態</th><th>結果</th><th>測試人</th><th>覆核人</th><th>發現事項</th></tr></thead><tbody>"
        for test in sorted(tests, key=lambda x: x.test_date, reverse=True):
            test_status_class = "badge-low" if test.test_status == "已完成" else ("badge-medium" if test.test_status == "待覆核" else "")
            body += f"""<tr>
                <td>{test.test_date}</td>
                <td><span class="badge {test_status_class}">{test.test_status}</span></td>
                <td><span class="badge {'badge-low' if test.test_result == '通過' else ('badge-high' if test.test_result == '不通過' else 'badge-medium')}">{test.test_result}</span></td>
                <td>{test.tester}</td>
                <td>{test.reviewer or '-'}</td>
                <td>{test.findings or '-'}</td>
            </tr>"""
        body += "</tbody></table>"
    else:
        body += "<p>尚無測試記錄。</p>"
    
    body += "</div>"
    
    # 測試狀態轉換 (僅有權限者可見)
    if has_permission("can_record_test_result") and ctrl.next_test_statuses():
        body += f"""
        <div class="card">
          <h3>測試流程管理</h3>
          <form method="post" action="{url_for('transition_control_test', control_id=ctrl.id)}">
            <div class="form-group">
              <label>更新測試狀態</label>
              <select name="new_status">
                {"".join(f'<option value="{s}">{s}</option>' for s in ctrl.next_test_statuses())}
              </select>
            </div>
            <button class="button" type="submit">更新狀態</button>
          </form>
        </div>
        """
    
    if related_issues_html:
        body += f"<div class=\"card\"><h3>關聯 Issue</h3><ul>{related_issues_html}</ul></div>"
    
    if ctrl.evidence_files:
        evidence_html = "".join(f"<li>{f}</li>" for f in ctrl.evidence_files)
        body += f"<div class=\"card\"><h3>關聯證據</h3><ul>{evidence_html}</ul></div>"
    
    body += f"<a class=\"button button-secondary\" href=\"{url_for('controls')}\">返回控制點矩陣</a>"
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/controls/<control_id>/transition", methods=["POST"])
@require_login()
def transition_control_test(control_id):
    """控制測試狀態轉換"""
    if not has_permission("can_record_test_result"):
        flash("您沒有權限執行此操作。", "error")
        return redirect(url_for("control_detail", control_id=control_id))
    
    ctrl = control_manager.get_control(control_id)
    if ctrl is None:
        flash("找不到指定的控制點。")
        return redirect(url_for("controls"))
    
    new_status = request.form.get("new_status", "")
    if new_status and ctrl.can_transition_to(new_status):
        control_manager.update_control(control_id, test_status=new_status)
        audit_log_manager.add_log(
            get_current_role(),
            "測試狀態轉換",
            "控制點矩陣",
            f"控制點 {control_id} 測試狀態變更為 {new_status}"
        )
        flash(f"測試狀態已更新為：{new_status}")
    else:
        flash("無效的狀態轉換。")
    
    return redirect(url_for("control_detail", control_id=control_id))


@app.route("/controls/manage", methods=["GET", "POST"])
@require_login()
@require_permission("can_edit_control")
def manage_controls():
    """控制點維護頁面"""
    if request.method == "POST":
        action = request.form.get("action", "")
        
        if action == "add":
            control_id = request.form.get("control_id", "").strip()
            name = request.form.get("name", "").strip()
            category = request.form.get("category", "").strip()
            process = request.form.get("process", "").strip()
            risk_level = request.form.get("risk_level", "M")
            description = request.form.get("description", "").strip()
            test_frequency = request.form.get("test_frequency", "每季")
            
            if not control_id or not name:
                flash("控制點ID和名稱為必填。", "error")
            else:
                try:
                    control_manager.create_control(
                        control_id, name, category, process, risk_level,
                        description, test_frequency, "", session.get("username", "system")
                    )
                    audit_log_manager.add_log(
                        session.get("username", "system"),
                        "建立控制點",
                        "控制點維護",
                        f"新增控制點：{control_id} - {name}"
                    )
                    flash(f"控制點 {control_id} 已建立。", "success")
                    return redirect(url_for("manage_controls"))
                except ValueError as e:
                    flash(str(e), "error")
    
    controls = control_manager.list_controls()
    body = ""
    body += "<div class=\"card\"><h2>控制點維護</h2>"
    body += "<p>稽核主管可以新增、編輯與停用控制點。</p></div>"
    
    # 上傳Excel表單
    body += "<div class=\"card\"><h3>批次匯入/匯出</h3>"
    body += "<div class=\"form-actions\" style=\"margin-bottom: 20px;\">"
    body += "<a class=\"button button-primary\" href=\"" + url_for('export_controls_excel') + "\">📥 下載控制點</a>"
    body += "</div>"
    body += "<form method=\"post\" enctype=\"multipart/form-data\" action=\"" + url_for('import_controls_excel') + "\">"
    body += "<div class=\"form-group\"><label for=\"excel_file\">上傳Excel檔案</label>"
    body += "<input type=\"file\" id=\"excel_file\" name=\"excel_file\" accept=\".xlsx,.xls\" required/>"
    body += "</div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">匯入控制點</button></div>"
    body += "</form></div>"
    
    # 新增控制點表單
    body += "<div class=\"card\"><h3>新增控制點</h3>"
    body += "<form method=\"post\" class=\"form-grid\">"
    body += "<input type=\"hidden\" name=\"action\" value=\"add\"/>"
    body += "<div class=\"form-group\"><label for=\"control_id\">控制點ID</label><input type=\"text\" id=\"control_id\" name=\"control_id\" required placeholder=\"例如：CP-001\"/></div>"
    body += "<div class=\"form-group\"><label for=\"name\">控制點名稱</label><input type=\"text\" id=\"name\" name=\"name\" required placeholder=\"控制點名稱\"/></div>"
    body += "<div class=\"form-group\"><label for=\"category\">分類</label><select id=\"category\" name=\"category\">"
    for cat in ["存取控制", "帳務核覆", "資安管理", "採購流程", "人事管理", "財務管理", "風險管理", "法規遵循"]:
        body += f"<option value=\"{cat}\">{cat}</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"process\">業務流程</label><select id=\"process\" name=\"process\">"
    for proc in PROCESSES:
        body += f"<option value=\"{proc}\">{proc}</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"risk_level\">風險等級</label><select id=\"risk_level\" name=\"risk_level\">"
    body += "<option value=\"H\">高</option><option value=\"M\" selected>中</option><option value=\"L\">低</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\"><label for=\"test_frequency\">測試頻率</label><select id=\"test_frequency\" name=\"test_frequency\">"
    for freq in ["每月", "每季", "每半年", "每年"]:
        body += f"<option value=\"{freq}\" {'selected' if freq == '每季' else ''}>{freq}</option>"
    body += "</select></div>"
    body += "<div class=\"form-group\" style=\"grid-column: 1 / -1;\"><label for=\"description\">描述</label><textarea id=\"description\" name=\"description\" rows=\"3\" placeholder=\"控制點描述\"></textarea></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">新增控制點</button></div>"
    body += "</form></div>"
    
    # 控制點列表
    body += "<div class=\"card\"><h3>控制點清單 (" + str(len(controls)) + ")</h3>"
    body += "<table class=\"table\"><thead><tr><th>ID</th><th>名稱</th><th>分類</th><th>流程</th><th>風險</th><th>測試頻率</th><th>狀態</th><th>操作</th></tr></thead><tbody>"
    
    for ctrl in controls:
        risk_label = RISK_LEVELS.get(ctrl.risk_level, ctrl.risk_level)
        body += f"<tr><td>{ctrl.id}</td><td>{ctrl.name}</td><td>{ctrl.category}</td><td>{ctrl.process}</td>"
        body += f"<td>{risk_label}</td><td>{ctrl.test_frequency}</td><td>{ctrl.status}</td>"
        body += f"<td class=\"action-buttons\">"
        body += f"<a class=\"button button-secondary\" href=\"{url_for('edit_control', control_id=ctrl.id)}\">編輯</a> "
        body += f"<form method=\"post\" action=\"{url_for('delete_control', control_id=ctrl.id)}\" style=\"display:inline;\">"
        body += f"<button class=\"button button-secondary\" type=\"submit\" onclick=\"return confirm('確定要停用此控制點嗎？');\">停用</button></form>"
        body += f"</td></tr>"
    
    body += "</tbody></table></div>"
    body += f"<a class=\"button button-secondary\" href=\"{url_for('controls')}\">回到控制點矩陣</a>"
    
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/controls/<control_id>/edit", methods=["GET", "POST"])
@require_login()
@require_permission("can_edit_control")
def edit_control(control_id):
    """編輯控制點"""
    control = control_manager.get_control(control_id)
    if not control:
        flash("找不到指定的控制點。", "error")
        return redirect(url_for("manage_controls"))
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        process = request.form.get("process", "").strip()
        risk_level = request.form.get("risk_level", "M")
        description = request.form.get("description", "").strip()
        test_frequency = request.form.get("test_frequency", "每季")
        
        control_manager.update_control(
            control_id, name=name, category=category, process=process,
            risk_level=risk_level, description=description, test_frequency=test_frequency
        )
        
        audit_log_manager.add_log(
            session.get("username", "system"),
            "編輯控制點",
            "控制點維護",
            f"修改控制點：{control_id}"
        )
        
        flash("控制點已更新。", "success")
        return redirect(url_for("manage_controls"))
    
    body = ""
    body += "<div class=\"card\"><h2>編輯控制點</h2>"
    body += "<p>修改控制點的相關資訊。</p></div>"
    body += "<div class=\"card\"><form method=\"post\" class=\"form-grid\">"
    body += f"<div class=\"form-group\"><label>控制點ID</label><input type=\"text\" value=\"{control.id}\" disabled/></div>"
    body += f"<div class=\"form-group\"><label for=\"name\">控制點名稱</label><input type=\"text\" id=\"name\" name=\"name\" value=\"{control.name}\" required/></div>"
    body += f"<div class=\"form-group\"><label for=\"category\">分類</label><select id=\"category\" name=\"category\">"
    for cat in ["存取控制", "帳務核覆", "資安管理", "採購流程", "人事管理", "財務管理", "風險管理", "法規遵循"]:
        selected = "selected" if cat == control.category else ""
        body += f"<option value=\"{cat}\" {selected}>{cat}</option>"
    body += "</select></div>"
    body += f"<div class=\"form-group\"><label for=\"process\">業務流程</label><select id=\"process\" name=\"process\">"
    for proc in PROCESSES:
        selected = "selected" if proc == control.process else ""
        body += f"<option value=\"{proc}\" {selected}>{proc}</option>"
    body += "</select></div>"
    body += f"<div class=\"form-group\"><label for=\"risk_level\">風險等級</label><select id=\"risk_level\" name=\"risk_level\">"
    for level, label in [("H", "高"), ("M", "中"), ("L", "低")]:
        selected = "selected" if level == control.risk_level else ""
        body += f"<option value=\"{level}\" {selected}>{label}</option>"
    body += "</select></div>"
    body += f"<div class=\"form-group\"><label for=\"test_frequency\">測試頻率</label><select id=\"test_frequency\" name=\"test_frequency\">"
    for freq in ["每月", "每季", "每半年", "每年"]:
        selected = "selected" if freq == control.test_frequency else ""
        body += f"<option value=\"{freq}\" {selected}>{freq}</option>"
    body += "</select></div>"
    body += f"<div class=\"form-group\" style=\"grid-column: 1 / -1;\"><label for=\"description\">描述</label><textarea id=\"description\" name=\"description\" rows=\"4\">{control.description}</textarea></div>"
    body += "<div class=\"form-actions\"><button class=\"button button-primary\" type=\"submit\">保存修改</button></div>"
    body += "</form></div>"
    body += f"<a class=\"button button-secondary\" href=\"{url_for('manage_controls')}\">取消</a>"
    
    return render_template_string(TEMPLATE_BASE, body=body)


@app.route("/controls/<control_id>/delete", methods=["POST"])
@require_login()
@require_permission("can_disable_control")
def delete_control(control_id):
    """停用控制點"""
    if control_manager.delete_control(control_id):
        audit_log_manager.add_log(
            session.get("username", "system"),
            "停用控制點",
            "控制點維護",
            f"停用控制點：{control_id}"
        )
        flash("控制點已停用。", "success")
    else:
        flash("無法停用該控制點。", "error")
    
    return redirect(url_for("manage_controls"))


@app.route("/controls/export-excel", methods=["GET"])
@require_login()
@require_permission("can_edit_control")
def export_controls_excel():
    """匯出所有控制點到Excel檔案"""
    import tempfile
    import os
    from datetime import datetime
    
    try:
        # 創建臨時Excel檔案
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = os.path.join(temp_dir, f"controls_{timestamp}.xlsx")
        
        # 匯出所有控制點
        controls = control_manager.list_controls()
        success = control_manager.export_to_excel(temp_file, controls)
        
        if not success:
            flash("匯出失敗：無法生成Excel檔案。", "error")
            return redirect(url_for("manage_controls"))
        
        # 記錄審核日誌
        audit_log_manager.add_log(
            session.get("username", "system"),
            "匯出控制點",
            "控制點維護",
            f"下載Excel檔案，共 {len(controls)} 筆控制點"
        )
        
        # 讀取檔案並發送
        from flask import send_file
        filename = f"控制點清單_{timestamp}.xlsx"
        
        return send_file(
            temp_file,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        flash(f"匯出出錯：{str(e)}", "error")
        return redirect(url_for("manage_controls"))


@app.route("/controls/import-excel", methods=["POST"])
@require_login()
@require_permission("can_edit_control")
def import_controls_excel():
    """從Excel匯入控制點"""
    if 'excel_file' not in request.files:
        flash("請選擇Excel檔案。", "error")
        return redirect(url_for("manage_controls"))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash("請選擇Excel檔案。", "error")
        return redirect(url_for("manage_controls"))
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash("請上傳Excel檔案 (.xlsx 或 .xls)。", "error")
        return redirect(url_for("manage_controls"))
    
    try:
        # 保存上傳的檔案
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, file.filename)
        file.save(temp_file)
        
        # 匯入
        result = control_manager.import_from_excel(temp_file)
        
        # 刪除臨時檔案
        os.remove(temp_file)
        
        if result['success']:
            audit_log_manager.add_log(
                session.get("username", "system"),
                "批次匯入控制點",
                "控制點維護",
                f"從Excel匯入 {result['imported']} 筆控制點"
            )
            flash(f"成功匯入 {result['imported']} 筆控制點", "success")
            
            if result.get('errors'):
                for error in result['errors'][:5]:
                    flash(f"警告：{error}", "warning")
        else:
            flash(f"匯入失敗：{result['message']}", "error")
    
    except Exception as e:
        flash(f"匯入出錯：{str(e)}", "error")
    
    return redirect(url_for("manage_controls"))


if __name__ == "__main__":
    app.run(debug=False, port=5000)
