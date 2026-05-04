"""
匯入示範資料到 SQLite
"""
from database import get_db_connection, init_database
from datetime import datetime

def seed_data():
    init_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 匯入公告資料
    announcements = [
        (1, "2026 年度金融監管報告更新", "本次更新包括：\n1. 修訂『營運風險管理指引』第 4.2 節。\n2. 新增資安稽核報告提交週期。\n3. 強化內部稽核追蹤機制。\n請於 2026/05/01 前完成相關程序檢核。", "法規更新", "高", "已發布", "全體", "", "system_admin", "2026-04-15", "2026-04-18", "2026-04-18"),
        (2, "遠端工作資安新制發布", "新增遠端工作設備安全檢查清單。\n員工須在每次遠端辦公前完成自我檢核，並於系統上傳檢核結果。\n請務必遵守新制，以避免資料外洩風險。", "內部政策變更", "中", "已發布", "全體", "", "system_admin", "2026-04-10", "2026-04-10", "2026-04-10"),
        (3, "系統存取權限定期檢視通知", "各部門主管請於本月底前完成員工存取權限檢視。\n如有異常請立即提出調整申請。", "稽核提醒", "低", "已發布", "全體", "", "system_admin", "2026-04-05", "2026-04-05", "2026-04-05"),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO announcements (id, title, content, category, importance, publish_status, target_scope, due_read_date, created_by, created_at, updated_at, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, announcements)
    
    # 匯入 Issue 資料
    issues = [
        (1, "系統存取權限未定期檢視", "部分帳號仍保有離職員工存取權限。", "H", "C-401", "立即執行存取權限清查，並移除不必要帳號。", "Open", "IT 安全團隊", "2026-04-18", "2026-04-18"),
        (2, "備份資料未完成異地保存", "每日備份未同步到異地災備中心。", "M", "C-207", "設定自動備份同步機制並建立異地備份驗證。", "Assigned", "IT 運維", "2026-04-12", "2026-04-14"),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO issues (id, title, finding, risk_level, control_id, recommendation, status, owner, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, issues)
    
    # 匯入控制點資料
    controls = [
        ("CP-001", "帳務調整核覆", "帳務核覆", "財務管理", "H", "所有帳務調整金額超過 NT$50,000 須經過二線主管核可後才能入帳", "每月", "財務部", "張小明", "2025-01-01", "2026-03-15"),
        ("CP-002", "系統存取權限審查", "存取控制", "資訊安全", "H", "每季執行系統帳號權限檢視，確認離職員工帳號已停用", "每季", "資訊部", "李大正", "2025-01-01", "2026-01-20"),
        ("CP-003", "採購比價程序", "採購流程", "採購管理", "M", "單筆金額超過 NT$100,000 之採購須進行三家比價並留下書面記錄", "每月", "採購部", "王小美", "2025-01-01", "2026-02-28"),
        ("CP-004", "資安事件通報", "資安管理", "資訊安全", "H", "發生資安事件時，須於 24 小時內完成通報並啟動應變程序", "每季", "資安室", "陳安全", "2025-01-01", "2026-01-10"),
        ("CP-005", "個資保護措施", "法規遵循", "法務合規", "H", "客戶個人資料須加密儲存，且存取須留下軌跡記錄", "每半年", "法務部", "林律師", "2025-01-01", "2025-12-01"),
        ("CP-006", "員工到職訓練", "人事管理", "人力資源", "M", "新進員工須於到職一週內完成必修合規訓練", "每月", "人資部", "黃人資", "2025-01-01", "2026-03-01"),
        ("CP-007", "存貨盤點", "帳務核覆", "生產製造", "M", "每季執行存貨盤點，盤盈盤損須超過 5% 者須呈報", "每季", "生管部", "張生管", "2025-01-01", "2026-02-15"),
        ("CP-008", "合約審閱流程", "法規遵循", "法務合規", "M", "所有對外合約須經法務審閱後才能用印", "每月", "法務部", "林律師", "2025-01-01", "2026-03-20"),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO controls (id, name, category, process, risk_level, description, test_frequency, owner_dept, owner_user, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, controls)
    
    # 匯入資源資料
    resources = [
        (1, "資安政策手冊", "公司制度", "https://example.com/security-policy", "最新資安政策與執行指引。", "system_admin", now),
        (2, "人資請假流程", "公司制度", "https://example.com/hr-leave", "遠端與辦公室請假申請流程。", "system_admin", now),
        (3, "Issue Tracker 使用手冊", "風險管理", "https://example.com/issue-tracker", "Issue 管理與稽核記錄操作說明。", "system_admin", now),
        (4, "金融監理公告", "外部法規", "https://example.com/regulator-notice", "監理機構最新公告與修訂條文。", "system_admin", now),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO resources (id, name, category, file_path, description, uploaded_by, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, resources)
    
    # 匯入稽核日誌
    audit_logs = [
        (1, "admin", "登入", "系統", "成功登入系統", "2026-04-19 09:00:00"),
        (2, "admin", "建立公告", "公告中心", "建立新公告：2026 年度金融監管報告更新", "2026-04-19 09:15:00"),
        (3, "user1", "確認閱讀", "公告中心", "確認閱讀公告 ID: 1", "2026-04-19 09:30:00"),
        (4, "admin", "建立 Issue", "Issue Tracker", "建立新 Issue：系統存取權限未定期檢視", "2026-04-19 10:00:00"),
        (5, "user2", "狀態轉換", "Issue Tracker", "將 Issue ID: 2 從 Open 轉換到 Plan", "2026-04-19 10:30:00"),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO audit_logs (id, actor, action, target, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, audit_logs)
    
    conn.commit()
    conn.close()
    print("示範資料匯入完成！")

if __name__ == "__main__":
    seed_data()