import sqlite3
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
