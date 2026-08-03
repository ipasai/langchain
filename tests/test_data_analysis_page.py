import unittest

import pandas as pd

from data_analysis_page import build_chart_config_defaults


class DataAnalysisPageTests(unittest.TestCase):
    def test_build_chart_config_defaults_provides_reasonable_values(self):
        df = pd.DataFrame({"city": ["A", "B", "C"], "sales": [100, 200, 150]})

        config = build_chart_config_defaults(df, "city", "sales", "bar")

        self.assertEqual(config["title"], "city vs sales")
        self.assertEqual(config["x_label"], "city")
        self.assertEqual(config["y_label"], "sales")
        self.assertEqual(config["aggregation"], "平均值")
        self.assertEqual(config["bins"], 10)
        self.assertTrue(config["show_grid"])


if __name__ == "__main__":
    unittest.main()
