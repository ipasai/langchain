import json
from pathlib import Path

import pandas as pd

from data_analysis_page import load_analysis_history, save_analysis_history_entry


def test_save_and_load_analysis_history(tmp_path):
    history_path = tmp_path / "analysis_history.json"

    entry = {
        "file_name": "sample.csv",
        "file_path": str(tmp_path / "sample.csv"),
        "x_col": "sales",
        "y_col": "month",
        "chart_type": "bar",
        "saved_path": str(tmp_path / "chart.png"),
        "created_at": "2026-08-03T00:00:00",
    }

    save_analysis_history_entry(history_path, entry)
    history = load_analysis_history(history_path)

    assert len(history) == 1
    assert history[0]["file_name"] == "sample.csv"
    assert history[0]["x_col"] == "sales"
    assert history[0]["chart_type"] == "bar"

    saved_text = history_path.read_text(encoding="utf-8")
    assert "sample.csv" in saved_text
