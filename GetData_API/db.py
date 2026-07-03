import sqlite3
import sys
from pathlib import Path
from contextlib import contextmanager

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "api_tool.db"

# 全局連接緩存
_db_connection = None

CREATE_API_MASTER = """
CREATE TABLE IF NOT EXISTS api_master(
    id INTEGER PRIMARY KEY,
    api_name TEXT NOT NULL,
    api_url TEXT NOT NULL,
    method TEXT NOT NULL
);
"""

CREATE_API_PARAMETER = """
CREATE TABLE IF NOT EXISTS api_parameter(
    id INTEGER PRIMARY KEY,
    api_id INTEGER NOT NULL,
    parameter_name TEXT NOT NULL,
    source_column TEXT,
    default_value TEXT,
    FOREIGN KEY(api_id) REFERENCES api_master(id)
);
"""


def get_connection():
    """取得連接（使用連接池）"""
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect(DB_FILE, check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row
    return _db_connection


def close_connection():
    """關閉連接"""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None


@contextmanager
def get_db_cursor():
    """上下文管理器：取得遊標"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def init_db():
    with get_db_cursor() as cursor:
        cursor.execute(CREATE_API_MASTER)
        cursor.execute(CREATE_API_PARAMETER)


def save_api(api_name, api_url, method, api_id=None):
    with get_db_cursor() as cursor:
        if api_id:
            cursor.execute(
                "UPDATE api_master SET api_name = ?, api_url = ?, method = ? WHERE id = ?",
                (api_name, api_url, method, api_id),
            )
        else:
            cursor.execute(
                "INSERT INTO api_master(api_name, api_url, method) VALUES(?, ?, ?)",
                (api_name, api_url, method),
            )
            api_id = cursor.lastrowid
        return api_id


def get_api(api_id):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM api_master WHERE id = ?", (api_id,))
        return cursor.fetchone()


def load_apis():
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM api_master ORDER BY id DESC")
        return cursor.fetchall()


def delete_api(api_id):
    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM api_parameter WHERE api_id = ?", (api_id,))
        cursor.execute("DELETE FROM api_master WHERE id = ?", (api_id,))


def save_api_parameters(api_id, parameters):
    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM api_parameter WHERE api_id = ?", (api_id,))
        cursor.executemany(
            "INSERT INTO api_parameter(api_id, parameter_name, source_column, default_value) VALUES(?, ?, ?, ?)",
            [
                (
                    api_id,
                    p["parameter_name"],
                    p.get("source_column", ""),
                    p.get("default_value", ""),
                )
                for p in parameters
            ],
        )


def load_api_parameters(api_id):
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM api_parameter WHERE api_id = ? ORDER BY id",
            (api_id,),
        )
        return cursor.fetchall()
