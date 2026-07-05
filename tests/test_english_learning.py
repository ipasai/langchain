import os
import sqlite3
import tempfile
import unittest

from app import (
    get_flashcard_display_content,
    merge_example_sentences,
    normalize_flashcard_state,
    parse_llm_example_sentences,
    parse_llm_translation_response,
    resolve_translation_lookup,
)
from db_utils import (
    delete_translation_entry,
    ensure_local_memory_database,
    list_english_practice_items,
    list_study_sessions,
    load_daily_review_state,
    record_study_session,
    save_daily_review_state,
    save_translation_entry,
    search_translation_entries,
    should_show_daily_review_reminder,
)


class EnglishLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "english.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_translation_entry_is_saved_and_searchable(self):
        save_translation_entry("hello", "你好", "Hello, world!", db_path=self.db_path)

        results = search_translation_entries("你好", db_path=self.db_path)
        self.assertEqual(results[0]["english"], "hello")
        self.assertEqual(results[0]["example"], "Hello, world!")

    def test_study_sessions_are_recorded(self):
        record_study_session("toefl", 4, 5, db_path=self.db_path)
        sessions = list_study_sessions(limit=5, db_path=self.db_path)
        self.assertEqual(sessions[0]["test_type"], "toefl")
        self.assertEqual(sessions[0]["score"], 4)
        self.assertEqual(sessions[0]["accuracy"], 0.8)

    def test_daily_review_state_is_saved_and_checked(self):
        save_daily_review_state("2026-07-05", db_path=self.db_path)
        self.assertEqual(load_daily_review_state(db_path=self.db_path), "2026-07-05")
        self.assertFalse(should_show_daily_review_reminder(db_path=self.db_path, today="2026-07-05"))
        self.assertTrue(should_show_daily_review_reminder(db_path=self.db_path, today="2026-07-06"))

    def test_flashcard_state_is_normalized_for_empty_or_out_of_range_values(self):
        safe_index, safe_revealed = normalize_flashcard_state([], 10, True)
        self.assertEqual(safe_index, 0)
        self.assertFalse(safe_revealed)

        safe_index, safe_revealed = normalize_flashcard_state([{"english": "hello"}], 5, True)
        self.assertEqual(safe_index, 0)
        self.assertTrue(safe_revealed)

    def test_llm_translation_response_is_parsed(self):
        translation, example = parse_llm_translation_response("中文意思：你好\n例句：Hello, world!")
        self.assertEqual(translation, "你好")
        self.assertEqual(example, "Hello, world!")

    def test_flashcard_display_mode_switches_between_english_and_chinese(self):
        card = {"english": "hello", "translation": "你好", "example": "Hello, world!"}
        self.assertEqual(get_flashcard_display_content(card, "english"), "hello")
        self.assertEqual(get_flashcard_display_content(card, "chinese"), "你好")

    def test_translation_entry_can_store_category(self):
        save_translation_entry("hello", "你好", "Hello, world!", category="TOEFL", db_path=self.db_path)
        items = list_english_practice_items(limit=5, db_path=self.db_path)
        self.assertEqual(items[0]["category"], "TOEFL")

    def test_merge_example_sentences_appends_unique_entries(self):
        merged = merge_example_sentences("Hello, world!", ["I am learning English.", "Hello, world!"])
        self.assertEqual(merged, ["Hello, world!", "I am learning English."])

    def test_translation_entry_can_be_deleted(self):
        save_translation_entry("hello", "你好", "Hello, world!", db_path=self.db_path)
        delete_translation_entry("hello", db_path=self.db_path)
        items = list_english_practice_items(limit=5, db_path=self.db_path)
        self.assertEqual(items, [])

    def test_translation_lookup_prefers_existing_local_record(self):
        save_translation_entry("hello", "你好", "Hello, world!", db_path=self.db_path)
        result = resolve_translation_lookup("你好", db_path=self.db_path)
        self.assertEqual(result["english"], "hello")
        self.assertEqual(result["source"], "local")

    def test_multiple_example_sentences_are_parsed(self):
        examples = parse_llm_example_sentences("例句1：Hello, world!\n例句2：I am learning English.\n例句3：This is useful.")
        self.assertEqual(len(examples), 3)
        self.assertIn("Hello, world!", examples)

    def test_existing_database_schema_is_migrated_to_include_example_column(self):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                "CREATE TABLE english_practice (id INTEGER PRIMARY KEY AUTOINCREMENT, english TEXT NOT NULL, translation TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            connection.commit()
        finally:
            connection.close()

        ensure_local_memory_database(self.db_path)
        connection = sqlite3.connect(self.db_path)
        try:
            columns = [row[1] for row in connection.execute("PRAGMA table_info('english_practice')").fetchall()]
            self.assertIn("example", columns)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
