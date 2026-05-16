"""
SQLite 資料庫管理模組
"""
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.environ.get("PRJ1_DB_PATH") or os.path.join(os.path.dirname(__file__), "icp_system.db")


def get_db_connection():
    """取得資料庫連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化資料庫結構"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 公告資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            importance TEXT,
            publish_status TEXT DEFAULT 'draft',
            target_scope TEXT,
            due_read_date TEXT,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            published_at TEXT,
            archived_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # 若現有資料庫缺少 is_active 欄位，則新增它
    cursor.execute("PRAGMA table_info(announcements)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "is_active" not in existing_columns:
        cursor.execute("ALTER TABLE announcements ADD COLUMN is_active INTEGER DEFAULT 1")
    
    # Issue 資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            finding TEXT NOT NULL,
            risk_level TEXT DEFAULT 'M',
            control_id TEXT,
            recommendation TEXT,
            owner TEXT,
            status TEXT DEFAULT 'Open',
            issue_type TEXT,
            root_cause TEXT,
            impact_scope TEXT,
            planned_due_date TEXT,
            closed_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            recurring_flag INTEGER DEFAULT 0,
            extension_status TEXT,
            compensating_control TEXT
        )
    """)
    
    # 控制點資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS controls (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            process TEXT,
            risk_level TEXT,
            description TEXT,
            test_frequency TEXT,
            control_objective TEXT,
            control_type TEXT,
            control_mode TEXT,
            key_control_flag INTEGER DEFAULT 0,
            effective_from TEXT,
            effective_to TEXT,
            version_no TEXT DEFAULT 'V1.0',
            last_test_date TEXT,
            last_test_result TEXT DEFAULT '待測試',
            next_test_date TEXT,
            owner_dept TEXT,
            owner_user TEXT,
            status TEXT DEFAULT '有效',
            created_at TEXT,
            updated_at TEXT,
            test_status TEXT DEFAULT '排程建立'
        )
    """)
    
    # 控制測試記錄表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS control_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            control_id TEXT NOT NULL,
            test_date TEXT,
            test_result TEXT,
            tester TEXT,
            test_period TEXT,
            test_method TEXT,
            sample_method TEXT,
            sample_size INTEGER DEFAULT 0,
            exception_count INTEGER DEFAULT 0,
            reviewer TEXT,
            findings TEXT,
            evidence_files TEXT,
            related_issue_id INTEGER,
            test_status TEXT DEFAULT '待執行',
            FOREIGN KEY (control_id) REFERENCES controls(id)
        )
    """)
    
    # 憑證資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT NOT NULL,
            record_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT,
            file_hash TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT,
            description TEXT
        )
    """)
    
    # 通知資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            target_user TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT,
            read_at TEXT
        )
    """)
    
    # 稽核日誌資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT,
            detail TEXT,
            created_at TEXT
        )
    """)
    
    # 資源資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            file_path TEXT,
            description TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    
    # 若現有資料庫缺少 active 欄位，則新增它
    cursor.execute("PRAGMA table_info(resources)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "active" not in existing_columns:
        cursor.execute("ALTER TABLE resources ADD COLUMN active INTEGER DEFAULT 1")
    
    # 匯出日誌資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS export_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exporter TEXT NOT NULL,
            report_name TEXT NOT NULL,
            purpose TEXT,
            exported_at TEXT
        )
    """)
    
    # 用戶資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    # 移除遞迴呼叫，避免 RecursionError
    conn.commit()
    conn.close()
