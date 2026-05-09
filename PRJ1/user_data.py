"""
用戶管理模組 (SQLite)
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from database import get_db_connection
import hashlib


@dataclass
class User:
    """用戶資料結構"""
    id: int
    username: str
    password: str  # 已加密
    role: str
    full_name: str = ""
    email: str = ""
    status: str = "Active"  # Active / Inactive / Suspended
    force_password_change: bool = False  # 是否強制修改密碼
    created_at: str = ""
    updated_at: str = ""

    def is_active(self) -> bool:
        """檢查用戶是否在活動狀態"""
        return self.status == "Active"


class UserManager:
    """用戶管理器"""
    
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "admin123"
    DEFAULT_ADMIN_ROLE = "system_admin"

    def __init__(self):
        self._ensure_table_exists()
        self._load_users()
        self._seed_default_admin()
    
    def _ensure_table_exists(self):
        """確保用戶表存在"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        # 檢查並添加 force_password_change 欄位
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'force_password_change' not in column_names:
            cursor.execute("ALTER TABLE users ADD COLUMN force_password_change INTEGER DEFAULT 0")
        
        conn.commit()
        conn.close()
    
    def _load_users(self):
        """從資料庫載入所有用戶"""
        self._users = {}
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            self._users[row["id"]] = self._row_to_user(row)
    
    def _seed_default_admin(self):
        """當資料庫中尚無用戶時，建立預設系統管理員帳號"""
        if self._users:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO users (username, password, role, full_name, email, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Active', ?, ?)
            """,
            (
                self.DEFAULT_ADMIN_USERNAME,
                self.hash_password(self.DEFAULT_ADMIN_PASSWORD),
                self.DEFAULT_ADMIN_ROLE,
                "系統管理員",
                "",
                now,
                now,
            ),
        )
        conn.commit()
        conn.close()
        self._load_users()

    def _row_to_user(self, row) -> User:
        """將資料庫資料轉換為 User 物件"""
        return User(
            id=row["id"],
            username=row["username"],
            password=row["password"],
            role=row["role"],
            full_name=row["full_name"] or "",
            email=row["email"] or "",
            status=row["status"] or "Active",
            force_password_change=bool(row["force_password_change"]) if "force_password_change" in row.keys() else False,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )

    @staticmethod
    def hash_password(password: str) -> str:
        """加密密碼 (簡單 SHA-256，生產環境應使用 bcrypt)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """驗證用戶名和密碼"""
        user = self.get_user_by_username(username)
        if user and user.is_active():
            # 檢查密碼
            if user.password == self.hash_password(password):
                return user
        return None

    def list_users(self) -> List[User]:
        """取得所有用戶清單"""
        return sorted(self._users.values(), key=lambda u: u.id)

    def get_user(self, user_id: int) -> Optional[User]:
        """取得指定用戶 (根據 ID)"""
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """取得指定用戶 (根據用戶名)"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        full_name: str = "",
        email: str = "",
    ) -> Optional[User]:
        """建立新用戶"""
        # 檢查用戶名是否已存在
        if self.get_user_by_username(username):
            raise ValueError(f"用戶 {username} 已存在")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hashed_pwd = self.hash_password(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (username, password, role, full_name, email, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Active', ?, ?)
        """, (username, hashed_pwd, role, full_name, email, now, now))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self._load_users()
        return self.get_user(user_id)

    def update_user(
        self,
        user_id: int,
        full_name: str = None,
        email: str = None,
        role: str = None,
        status: str = None,
    ) -> Optional[User]:
        """更新用戶資訊"""
        user = self._users.get(user_id)
        if not user:
            return None
        
        fields = {}
        if full_name is not None:
            fields["full_name"] = full_name
        if email is not None:
            fields["email"] = email
        if role is not None:
            fields["role"] = role
        if status is not None:
            fields["status"] = status
        
        if fields:
            fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values()) + [user_id]
            
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
            
            self._load_users()
        
        return self.get_user(user_id)

    def change_password(self, user_id: int, new_password: str) -> bool:
        """更改密碼"""
        user = self._users.get(user_id)
        if not user:
            return False
        
        hashed_pwd = self.hash_password(new_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET password = ?, updated_at = ? WHERE id = ?",
            (hashed_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        conn.commit()
        conn.close()
        
        self._load_users()
        return True

    def update_password_by_username(self, username: str, new_password: str) -> bool:
        """根據用戶名更新密碼"""
        user = self.get_user_by_username(username)
        if not user:
            return False
        
        return self.change_password(user.id, new_password)

    def set_force_password_change(self, username: str, force_change: bool = True) -> bool:
        """設置用戶是否需要強制修改密碼"""
        user = self.get_user_by_username(username)
        if not user:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET force_password_change = ?, updated_at = ? WHERE id = ?",
            (1 if force_change else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user.id)
        )
        conn.commit()
        conn.close()
        
        self._load_users()
        return True

    def disable_user(self, user_id: int) -> bool:
        """停用用戶"""
        return self.update_user(user_id, status="Inactive") is not None

    def enable_user(self, user_id: int) -> bool:
        """啟用用戶"""
        return self.update_user(user_id, status="Active") is not None

    def get_stats(self) -> dict:
        """取得用戶統計"""
        total = len(self._users)
        active = sum(1 for u in self._users.values() if u.status == "Active")
        
        by_role = {}
        for user in self._users.values():
            if user.role not in by_role:
                by_role[user.role] = 0
            by_role[user.role] += 1
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "by_role": by_role,
        }


# 全域用戶管理器實例
user_manager = UserManager()
