import os
import tempfile
import unittest

from db_utils import DBType, analyze_database, connect_database, delete_row, execute_sql_query, get_table_columns, insert_row, update_row


class ExecuteSqlQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.config = {"filepath": self.db_path}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_execute_select_query_returns_rows(self):
        execute_sql_query(DBType.SQLITE, self.config, "CREATE TABLE demo(id INTEGER PRIMARY KEY, name TEXT);")
        execute_sql_query(DBType.SQLITE, self.config, "INSERT INTO demo(name) VALUES ('Alice');")

        result = execute_sql_query(DBType.SQLITE, self.config, "SELECT name FROM demo;")

        self.assertEqual(result["columns"], ["name"])
        self.assertEqual(result["rows"], [("Alice",)])
        self.assertEqual(result["row_count"], 1)

    def test_insert_update_and_delete_row(self):
        execute_sql_query(DBType.SQLITE, self.config, "CREATE TABLE demo(id INTEGER PRIMARY KEY, name TEXT, age INTEGER);")

        insert_result = insert_row(DBType.SQLITE, self.config, "demo", {"name": "Alice", "age": 20})
        self.assertEqual(insert_result["row_count"], 1)

        update_result = update_row(DBType.SQLITE, self.config, "demo", {"age": 21}, "name = %s", ["Alice"])
        self.assertEqual(update_result["row_count"], 1)

        delete_result = delete_row(DBType.SQLITE, self.config, "demo", "name = %s", ["Alice"])
        self.assertEqual(delete_result["row_count"], 1)

        result = execute_sql_query(DBType.SQLITE, self.config, "SELECT COUNT(*) FROM demo;")
        self.assertEqual(result["rows"], [(0,)])

    def test_get_table_columns_returns_column_names(self):
        execute_sql_query(DBType.SQLITE, self.config, "CREATE TABLE demo(id INTEGER PRIMARY KEY, name TEXT, age INTEGER);")

        columns = get_table_columns(DBType.SQLITE, self.config, "demo")

        self.assertEqual(columns, ["id", "name", "age"])

    def test_analyze_database_includes_relationships_and_purpose(self):
        execute_sql_query(DBType.SQLITE, self.config, "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);")
        execute_sql_query(DBType.SQLITE, self.config, "CREATE TABLE orders(id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY(user_id) REFERENCES users(id));")

        connection = connect_database(DBType.SQLITE, self.config)
        try:
            analysis = analyze_database(DBType.SQLITE, connection, self.config)
        finally:
            connection.close()

        table_map = {table["name"]: table for table in analysis["tables"]}
        self.assertIn("users", table_map)
        self.assertIn("orders", table_map)
        self.assertTrue(table_map["users"].get("purpose", "").startswith(("使用者", "會員")))
        self.assertTrue(any(rel.get("to_table") == "users" for rel in table_map["orders"].get("relationships", [])))


if __name__ == "__main__":
    unittest.main()
