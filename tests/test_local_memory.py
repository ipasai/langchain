import os
import tempfile
import unittest

from db_utils import (
    ensure_local_memory_database,
    list_english_practice_items,
    load_recent_chat_messages,
    load_setting,
    record_english_practice,
    save_chat_message,
    save_setting,
)


class LocalMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "memory.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_settings_and_english_practice_are_persisted(self):
        ensure_local_memory_database(self.db_path)
        save_setting("app_locale", "en", db_path=self.db_path)
        self.assertEqual(load_setting("app_locale", "zh-tw", db_path=self.db_path), "en")

        record_english_practice("hello", "你好", db_path=self.db_path)
        records = list_english_practice_items(db_path=self.db_path)
        self.assertEqual(records[0]["english"], "hello")
        self.assertEqual(records[0]["translation"], "你好")

    def test_chat_messages_are_loaded_from_sqlite(self):
        ensure_local_memory_database(self.db_path)
        save_chat_message("user", "hello", db_path=self.db_path)
        save_chat_message("assistant", "hi", db_path=self.db_path)

        messages = load_recent_chat_messages(limit=5, db_path=self.db_path)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["content"], "hi")


if __name__ == "__main__":
    unittest.main()
