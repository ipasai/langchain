import os
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DBType(Enum):
    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRES = "postgres"
    MARIADB = "mariadb"
    REDIS = "redis"
    MONGODB = "mongodb"


class DBConnectionError(Exception):
    pass


def _default_sqlite_path() -> str:
    return os.path.join(os.path.dirname(__file__), "data", "app_memory.db")


def _ensure_table_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_definition: str) -> None:
    columns = [row[1] for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()]
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def ensure_local_memory_database(db_path: Optional[str] = None) -> str:
    """確保本地 SQLite 記憶資料庫與所需資料表存在。"""
    if not db_path:
        db_path = _default_sqlite_path()

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS english_practice (id INTEGER PRIMARY KEY AUTOINCREMENT, english TEXT NOT NULL, translation TEXT NOT NULL, example TEXT, created_at TEXT NOT NULL)"
        )
        _ensure_table_column(connection, "english_practice", "example", "TEXT")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS study_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, test_type TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, accuracy REAL NOT NULL, created_at TEXT NOT NULL)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS daily_review_state (id INTEGER PRIMARY KEY AUTOINCREMENT, review_date TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)"
        )
        connection.commit()
    finally:
        connection.close()
    return db_path


def save_setting(key: str, value: str, db_path: Optional[str] = None) -> None:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.utcnow().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def load_setting(key: str, default: Optional[str] = None, db_path: Optional[str] = None) -> Optional[str]:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default
    finally:
        connection.close()


def save_chat_message(role: str, content: str, db_path: Optional[str] = None) -> None:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "INSERT INTO chat_messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, datetime.utcnow().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def load_recent_chat_messages(limit: int = 20, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT role, content, created_at FROM chat_messages ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"role": row[0], "content": row[1], "created_at": row[2]} for row in rows]
    finally:
        connection.close()


def clear_chat_messages(db_path: Optional[str] = None) -> None:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("DELETE FROM chat_messages")
        connection.commit()
    finally:
        connection.close()


def save_translation_entry(english: str, translation: str, example: str = "", db_path: Optional[str] = None, category: Optional[str] = None) -> None:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        _ensure_table_column(connection, "english_practice", "category", "TEXT")
        connection.execute(
            "INSERT INTO english_practice (english, translation, example, category, created_at) VALUES (?, ?, ?, ?, ?)",
            (english.lower().strip(), translation.strip(), example.strip(), (category or "未分類").strip(), datetime.utcnow().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def delete_translation_entry(english: str, db_path: Optional[str] = None) -> int:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            "DELETE FROM english_practice WHERE lower(english) = ?",
            (english.lower().strip(),),
        )
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


def search_translation_entries(query: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        search_term = f"%{query.lower().strip()}%"
        rows = connection.execute(
            "SELECT english, translation, example, created_at FROM english_practice WHERE lower(english) LIKE ? OR lower(translation) LIKE ? ORDER BY id DESC LIMIT 10",
            (search_term, search_term),
        ).fetchall()
        return [{"english": row[0], "translation": row[1], "example": row[2], "created_at": row[3]} for row in rows]
    finally:
        connection.close()


def record_english_practice(english: str, translation: str, example: str = "", db_path: Optional[str] = None) -> None:
    save_translation_entry(english, translation, example, db_path=db_path)


def list_english_practice_items(limit: int = 10, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        _ensure_table_column(connection, "english_practice", "category", "TEXT")
        rows = connection.execute(
            "SELECT english, translation, example, category, created_at FROM english_practice ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"english": row[0], "translation": row[1], "example": row[2], "category": row[3] or "未分類", "created_at": row[4]} for row in rows]
    finally:
        connection.close()


def record_study_session(test_type: str, score: int, total: int, db_path: Optional[str] = None) -> None:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        accuracy = round(score / total, 2) if total else 0.0
        connection.execute(
            "INSERT INTO study_sessions (test_type, score, total, accuracy, created_at) VALUES (?, ?, ?, ?, ?)",
            (test_type, score, total, accuracy, datetime.utcnow().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def list_study_sessions(limit: int = 10, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT test_type, score, total, accuracy, created_at FROM study_sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"test_type": row[0], "score": row[1], "total": row[2], "accuracy": row[3], "created_at": row[4]} for row in rows]
    finally:
        connection.close()


def save_daily_review_state(review_date: str, db_path: Optional[str] = None) -> None:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "INSERT OR REPLACE INTO daily_review_state (review_date, created_at) VALUES (?, ?)",
            (review_date, datetime.utcnow().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def load_daily_review_state(db_path: Optional[str] = None) -> Optional[str]:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute("SELECT review_date FROM daily_review_state ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else None
    finally:
        connection.close()


def should_show_daily_review_reminder(db_path: Optional[str] = None, today: Optional[str] = None) -> bool:
    if not today:
        today = datetime.utcnow().date().isoformat()
    last_review = load_daily_review_state(db_path=db_path)
    return last_review != today


def get_learning_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    db_path = ensure_local_memory_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        total_items = connection.execute("SELECT COUNT(*) FROM english_practice").fetchone()[0]
        total_sessions = connection.execute("SELECT COUNT(*) FROM study_sessions").fetchone()[0]
        total_score = connection.execute("SELECT COALESCE(SUM(score), 0) FROM study_sessions").fetchone()[0]
        total_questions = connection.execute("SELECT COALESCE(SUM(total), 0) FROM study_sessions").fetchone()[0]
        accuracy = round(total_score / total_questions, 2) if total_questions else 0.0
        recent_accuracy = connection.execute(
            "SELECT accuracy FROM study_sessions ORDER BY id DESC LIMIT 5"
        ).fetchall()
        latest_accuracy = round(sum(row[0] for row in recent_accuracy) / len(recent_accuracy), 2) if recent_accuracy else 0.0
        return {
            "total_items": total_items,
            "total_sessions": total_sessions,
            "total_score": total_score,
            "total_questions": total_questions,
            "accuracy": accuracy,
            "latest_accuracy": latest_accuracy,
        }
    finally:
        connection.close()


def _import_module(module_name: str, package_hint: Optional[str] = None):
    try:
        return __import__(module_name)
    except ImportError as exc:
        hint = package_hint or module_name
        raise ImportError(
            f"缺少 Python 套件 '{module_name}'。請安裝: pip install {hint}"
        ) from exc


def connect_database(db_type: DBType, config: Dict[str, Any]):
    """建立指定資料庫連線物件。"""
    if db_type == DBType.SQLITE:
        path = config.get("filepath")
        if not path:
            raise DBConnectionError("請提供 SQLite 檔案路徑。")
        return sqlite3.connect(path, timeout=10)

    if db_type in {DBType.MYSQL, DBType.MARIADB}:
        pymysql = _import_module("pymysql")
        return pymysql.connect(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 3306)),
            user=config.get("user", "root"),
            password=config.get("password", ""),
            database=config.get("database", ""),
            connect_timeout=10,
            charset=config.get("charset", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor,
        )

    if db_type == DBType.POSTGRES:
        psycopg2 = _import_module("psycopg2")
        return psycopg2.connect(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 5432)),
            user=config.get("user", "postgres"),
            password=config.get("password", ""),
            dbname=config.get("database", "postgres"),
            connect_timeout=10,
        )

    if db_type == DBType.REDIS:
        redis = _import_module("redis")
        client = redis.Redis(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 6379)),
            password=config.get("password") or None,
            db=int(config.get("db", 0)),
            socket_connect_timeout=5,
        )
        client.ping()
        return client

    if db_type == DBType.MONGODB:
        pymongo = _import_module("pymongo", "pymongo")
        uri = config.get("uri")
        if not uri:
            raise DBConnectionError("請提供 MongoDB 連線 URI。")
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        return client

    raise DBConnectionError(f"不支援的資料庫類型: {db_type}")


def close_connection(db_type: DBType, connection: Any):
    if db_type == DBType.SQLITE:
        connection.close()
    elif db_type in {DBType.MYSQL, DBType.MARIADB, DBType.POSTGRES}:
        connection.close()
    elif db_type == DBType.REDIS:
        try:
            connection.close()
        except Exception:
            pass
    elif db_type == DBType.MONGODB:
        try:
            connection.close()
        except Exception:
            pass


def test_db_connection(db_type: DBType, config: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    try:
        connection = connect_database(db_type, config)
        analysis = analyze_database(db_type, connection, config)
        close_connection(db_type, connection)
        return True, "連線成功", analysis
    except Exception as exc:
        return False, str(exc), {}


def execute_sql_query(db_type: DBType, config: Dict[str, Any], query: str) -> Dict[str, Any]:
    """執行 SQL 查詢，支援 SELECT 與基本 DML。"""
    if not query or not query.strip():
        raise DBConnectionError("請輸入 SQL 查詢。")

    connection = connect_database(db_type, config)
    try:
        cursor = connection.cursor()
        cursor.execute(query)

        if cursor.description:
            columns = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchall()
            normalized_rows = []
            for row in raw_rows:
                if isinstance(row, dict):
                    normalized_rows.append(tuple(row.get(col) for col in columns))
                else:
                    normalized_rows.append(tuple(row))
            return {
                "ok": True,
                "operation": "SELECT",
                "columns": columns,
                "rows": normalized_rows,
                "row_count": len(normalized_rows),
            }

        connection.commit()
        return {
            "ok": True,
            "operation": "DML",
            "columns": [],
            "rows": [],
            "row_count": cursor.rowcount,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        close_connection(db_type, connection)


def get_table_preview(db_type: DBType, config: Dict[str, Any], table_name: str, limit: int = 10) -> Dict[str, Any]:
    """預覽資料表前幾筆資料。"""
    if not table_name:
        raise DBConnectionError("請選擇資料表。")

    connection = connect_database(db_type, config)
    try:
        cursor = connection.cursor()
        if db_type == DBType.SQLITE:
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT {limit};')
        elif db_type == DBType.POSTGRES:
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT {limit};')
        else:
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {limit};")

        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = [tuple(row) for row in cursor.fetchall()]
        return {
            "ok": True,
            "table": table_name,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    finally:
        close_connection(db_type, connection)


def _parameter_placeholder(db_type: DBType) -> str:
    return "?" if db_type == DBType.SQLITE else "%s"


def _normalize_query_placeholders(query: str, db_type: DBType) -> str:
    if db_type == DBType.SQLITE:
        return query.replace("%s", "?")
    return query


def get_table_columns(db_type: DBType, config: Dict[str, Any], table_name: str) -> List[str]:
    """取得資料表欄位名稱。"""
    if not table_name:
        raise DBConnectionError("請選擇資料表。")

    connection = connect_database(db_type, config)
    try:
        cursor = connection.cursor()
        if db_type == DBType.SQLITE:
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            return [row[1] for row in cursor.fetchall()]
        if db_type in {DBType.MYSQL, DBType.MARIADB}:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=%s ORDER BY ordinal_position;",
                (table_name,),
            )
            return [row[0] for row in cursor.fetchall()]
        if db_type == DBType.POSTGRES:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position;",
                (table_name,),
            )
            return [row[0] for row in cursor.fetchall()]
        return []
    finally:
        close_connection(db_type, connection)


def insert_row(db_type: DBType, config: Dict[str, Any], table_name: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """新增資料列。"""
    if not table_name or not values:
        raise DBConnectionError("請提供資料表名稱與欄位值。")

    columns = list(values.keys())
    placeholder = _parameter_placeholder(db_type)
    placeholders = ", ".join([placeholder] * len(columns))
    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

    connection = connect_database(db_type, config)
    try:
        cursor = connection.cursor()
        cursor.execute(query, list(values.values()))
        connection.commit()
        return {"ok": True, "row_count": cursor.rowcount}
    except Exception:
        connection.rollback()
        raise
    finally:
        close_connection(db_type, connection)


def update_row(db_type: DBType, config: Dict[str, Any], table_name: str, values: Dict[str, Any], where_clause: str, where_values: Optional[List[Any]] = None) -> Dict[str, Any]:
    """更新資料列。"""
    if not table_name or not values:
        raise DBConnectionError("請提供資料表名稱與更新欄位。")

    placeholder = _parameter_placeholder(db_type)
    assignments = ", ".join([f"{column} = {placeholder}" for column in values.keys()])
    query = f"UPDATE {table_name} SET {assignments}"
    if where_clause:
        query += f" WHERE {where_clause}"

    query = _normalize_query_placeholders(query, db_type)
    params = list(values.values()) + (where_values or [])

    connection = connect_database(db_type, config)
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return {"ok": True, "row_count": cursor.rowcount}
    except Exception:
        connection.rollback()
        raise
    finally:
        close_connection(db_type, connection)


def delete_row(db_type: DBType, config: Dict[str, Any], table_name: str, where_clause: str, where_values: Optional[List[Any]] = None) -> Dict[str, Any]:
    """刪除資料列。"""
    if not table_name:
        raise DBConnectionError("請提供資料表名稱。")

    query = f"DELETE FROM {table_name}"
    if where_clause:
        query += f" WHERE {where_clause}"

    query = _normalize_query_placeholders(query, db_type)
    connection = connect_database(db_type, config)
    try:
        cursor = connection.cursor()
        cursor.execute(query, where_values or [])
        connection.commit()
        return {"ok": True, "row_count": cursor.rowcount}
    except Exception:
        connection.rollback()
        raise
    finally:
        close_connection(db_type, connection)


def _infer_table_purpose(table_name: str, columns: List[Dict[str, str]]) -> str:
    normalized_name = table_name.lower()
    column_names = " ".join([col.get("name", "").lower() for col in columns])

    if any(token in normalized_name for token in ["user", "member", "account"]):
        return "使用者/會員資料表"
    if any(token in normalized_name for token in ["order", "purchase", "sale", "invoice"]):
        return "交易/訂單資料表"
    if any(token in normalized_name for token in ["product", "item", "goods", "sku"]):
        return "商品/項目資料表"
    if any(token in normalized_name for token in ["log", "event", "history"]):
        return "操作紀錄資料表"
    if any(token in normalized_name for token in ["config", "setting"]):
        return "設定資料表"
    if any(token in column_names for token in ["email", "phone", "password", "name"]):
        return "人員與聯絡資料表"
    return "業務資料表"


def _fetch_table_relationships(cursor: Any, db_type: DBType, table_name: str) -> List[Dict[str, Any]]:
    if db_type == DBType.SQLITE:
        cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
        rows = cursor.fetchall()
        return [
            {
                "from_column": row[3],
                "to_table": row[2],
                "to_column": row[4],
                "on_delete": row[5],
                "on_update": row[6],
            }
            for row in rows
        ]

    if db_type in {DBType.MYSQL, DBType.MARIADB}:
        cursor.execute(
            "SELECT kcu.COLUMN_NAME, kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME, rc.DELETE_RULE, rc.UPDATE_RULE "
            "FROM information_schema.KEY_COLUMN_USAGE kcu "
            "JOIN information_schema.REFERENTIAL_CONSTRAINTS rc "
            "ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA "
            "WHERE kcu.TABLE_SCHEMA = DATABASE() AND kcu.TABLE_NAME = %s AND kcu.REFERENCED_TABLE_NAME IS NOT NULL "
            "ORDER BY kcu.ORDINAL_POSITION;",
            (table_name,),
        )
        rows = cursor.fetchall()
        return [
            {
                "from_column": row[0],
                "to_table": row[1],
                "to_column": row[2],
                "on_delete": row[3],
                "on_update": row[4],
            }
            for row in rows
        ]

    if db_type == DBType.POSTGRES:
        cursor.execute(
            "SELECT kcu.column_name, ccu.table_name, ccu.column_name "
            "FROM information_schema.key_column_usage kcu "
            "JOIN information_schema.constraint_column_usage ccu "
            "ON kcu.constraint_name = ccu.constraint_name "
            "JOIN information_schema.table_constraints tc "
            "ON tc.constraint_name = kcu.constraint_name "
            "WHERE kcu.table_schema='public' AND kcu.table_name=%s AND tc.constraint_type='FOREIGN KEY';",
            (table_name,),
        )
        rows = cursor.fetchall()
        return [
            {
                "from_column": row[0],
                "to_table": row[1],
                "to_column": row[2],
                "on_delete": None,
                "on_update": None,
            }
            for row in rows
        ]

    return []


def analyze_database(db_type: DBType, connection: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    analysis: Dict[str, Any] = {
        "db_type": db_type.value,
        "config": {k: v for k, v in config.items() if k != "password"},
    }

    if db_type == DBType.SQLITE:
        cursor = connection.cursor()
        cursor.execute("SELECT sqlite_version();")
        version = cursor.fetchone()[0]
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        tables = [row[0] for row in cursor.fetchall()]
        table_info = []
        for table in tables[:10]:
            cursor.execute(f"SELECT COUNT(*) FROM \"{table}\";")
            count = cursor.fetchone()[0]
            fields = _fetch_table_columns(cursor, db_type, table, None)
            relationships = _fetch_table_relationships(cursor, db_type, table)
            table_info.append({
                "name": table,
                "row_count": count,
                "columns": fields,
                "purpose": _infer_table_purpose(table, fields),
                "relationships": relationships,
            })
        analysis.update({
            "version": version,
            "database": config.get("filepath"),
            "tables": table_info,
        })
        return analysis

    if db_type in {DBType.MYSQL, DBType.MARIADB, DBType.POSTGRES}:
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        if db_type == DBType.POSTGRES:
            cursor.execute("SELECT current_database();")
        else:
            cursor.execute("SELECT DATABASE();")
        current_db = cursor.fetchone()[0]

        if db_type == DBType.POSTGRES:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;"
            )
        else:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY table_name;"
            )
        tables = [row[0] for row in cursor.fetchall()]

        table_info: List[Dict[str, Any]] = []
        for table in tables[:10]:
            try:
                if db_type == DBType.POSTGRES:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
                count = cursor.fetchone()[0]
            except Exception:
                count = None
            fields = _fetch_table_columns(cursor, db_type, table, current_db)
            relationships = _fetch_table_relationships(cursor, db_type, table)
            table_info.append({
                "name": table,
                "row_count": count,
                "columns": fields,
                "purpose": _infer_table_purpose(table, fields),
                "relationships": relationships,
            })

        analysis.update({
            "version": version,
            "database": current_db,
            "tables": table_info,
        })
        return analysis

    if db_type == DBType.REDIS:
        info = connection.info()
        analysis.update({
            "version": info.get("redis_version"),
            "server": info.get("redis_mode"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "keyspace": info.get("db0", {}),
            "db_size": connection.dbsize(),
        })
        return analysis

    if db_type == DBType.MONGODB:
        uri = config.get("uri")
        db_name = config.get("database")
        server_info = connection.server_info()
        if db_name:
            database = connection[db_name]
        else:
            database = connection.get_default_database()
        collections = []
        if database is not None:
            collections = database.list_collection_names()
        collection_info = []
        for collection_name in collections[:10]:
            try:
                collection_info.append(
                    {
                        "name": collection_name,
                        "document_count": int(database[collection_name].estimated_document_count()),
                    }
                )
            except Exception:
                collection_info.append({"name": collection_name, "document_count": None})
        analysis.update({
            "version": server_info.get("version"),
            "database": db_name or str(database),
            "collections": collection_info,
        })
        return analysis

    raise DBConnectionError(f"無法分析資料庫類型: {db_type}")


def _fetch_table_columns(cursor: Any, db_type: DBType, table_name: str, current_db: Optional[str]) -> List[Dict[str, str]]:
    if db_type == DBType.SQLITE:
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        return [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]

    if db_type in {DBType.MYSQL, DBType.MARIADB}:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=%s ORDER BY ordinal_position;",
            (table_name,),
        )
        return [{"name": row[0], "type": row[1]} for row in cursor.fetchall()]

    if db_type == DBType.POSTGRES:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position;",
            (table_name,),
        )
        return [{"name": row[0], "type": row[1]} for row in cursor.fetchall()]

    return []


def build_sql_generation_prompt(
    db_type: DBType,
    analysis: Dict[str, Any],
    user_description: str,
) -> str:
    if db_type not in {DBType.SQLITE, DBType.MYSQL, DBType.POSTGRES, DBType.MARIADB}:
        raise DBConnectionError(
            "目前僅支援 MySQL / MariaDB / PostgreSQL / SQLite 的 SQL 生成。"
        )

    schema_lines = [
        f"資料庫類型: {db_type.value}",
        f"資料庫名稱: {analysis.get('database')}",
        f"版本: {analysis.get('version')}",
        "已知資料表與欄位:",
    ]

    for table in analysis.get("tables", []):
        columns = table.get("columns") or []
        column_desc = ", ".join([f"{c['name']}({c['type']})" for c in columns])
        schema_lines.append(f"- {table['name']}: {column_desc}")

    schema_lines.append("")
    schema_lines.append(
        "請根據上面的資料庫結構，僅回傳一個有效的 SQL 查詢語句，不要加説明、註解或其他文字。"
    )
    schema_lines.append(f"查詢敘述: {user_description}")

    return "\n".join(schema_lines)
