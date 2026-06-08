import sqlite3
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "api_tool.db"

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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(CREATE_API_MASTER)
        cursor.execute(CREATE_API_PARAMETER)
        conn.commit()
    finally:
        conn.close()


def save_api(api_name, api_url, method, api_id=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
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
        conn.commit()
        return api_id
    finally:
        conn.close()


def get_api(api_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_master WHERE id = ?", (api_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def load_apis():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_master ORDER BY id DESC")
        return cursor.fetchall()
    finally:
        conn.close()


def delete_api(api_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_parameter WHERE api_id = ?", (api_id,))
        cursor.execute("DELETE FROM api_master WHERE id = ?", (api_id,))
        conn.commit()
    finally:
        conn.close()


def save_api_parameters(api_id, parameters):
    conn = get_connection()
    try:
        cursor = conn.cursor()
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
        conn.commit()
    finally:
        conn.close()


def load_api_parameters(api_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM api_parameter WHERE api_id = ? ORDER BY id",
            (api_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()
