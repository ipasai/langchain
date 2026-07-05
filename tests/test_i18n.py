import unittest

import app


class LocalizationTests(unittest.TestCase):
    def test_translation_uses_selected_locale(self):
        self.assertEqual(app.t("app_title", "zh-tw"), "LangChain 多模型交互式應用")
        self.assertEqual(app.t("app_title", "en"), "LangChain Multi-Model Interactive Application")

    def test_default_language_falls_back_to_chinese(self):
        self.assertEqual(app.t("app_title", "fr"), "LangChain 多模型交互式應用")

    def test_database_translation_keys_use_selected_locale(self):
        self.assertEqual(app.t("version_label", "zh-tw"), "版本")
        self.assertEqual(app.t("version_label", "en"), "Version")
        self.assertEqual(app.t("uncategorized_label", "zh-tw"), "未分類")
        self.assertEqual(app.t("uncategorized_label", "en"), "Uncategorized")


if __name__ == "__main__":
    unittest.main()
