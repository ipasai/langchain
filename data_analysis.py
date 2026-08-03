#!/usr/bin/env python3
"""
資料分析模組
提供：
1. 讀取 CSV / Excel 資料
2. 分析資料內容與統計摘要
3. 讓使用者選擇欄位
4. 建議適合的圖表類型
5. 生成圖表並儲存為檔案
6. 對圖表提供意義分析
"""

import json
import os
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def _require_dependencies():
    if pd is None or plt is None:
        raise RuntimeError(
            "缺少必要套件，請先安裝：\n"
            "pip install pandas matplotlib openpyxl"
        )


def _load_json_to_dataframe(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        if len(data) == 1:
            value = next(iter(data.values()))
            if isinstance(value, list):
                return pd.DataFrame(value)

        if all(isinstance(v, list) for v in data.values()):
            return pd.DataFrame(data)

        return pd.json_normalize(data)

    raise ValueError("JSON 資料格式不支援，請提供物件陣列或欄位映射的字典。")


def _load_xml_to_dataframe(path):
    import xml.etree.ElementTree as ET

    tree = ET.parse(path)
    root = tree.getroot()
    rows = []

    elements = list(root)
    if len(elements) == 1 and list(elements[0]):
        elements = list(elements[0])

    for elem in elements:
        row = {}
        row.update(elem.attrib)

        if list(elem):
            for child in elem:
                row[child.tag] = child.text
        elif elem.text and elem.text.strip():
            row[elem.tag] = elem.text.strip()

        if row:
            rows.append(row)

    if not rows:
        raise ValueError("XML 內容無法轉換為資料表。請提供由多筆相同結構元素組成的資料。")

    return pd.DataFrame(rows)


def load_data(file_path):
    """讀取 CSV、Excel、JSON 或 XML 檔案"""
    _require_dependencies()

    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"找不到檔案: {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix in {".xlsx", ".xls"}:
        try:
            import openpyxl  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("讀取 Excel 需要 openpyxl，請安裝：pip install openpyxl") from exc
        return pd.read_excel(path)

    if suffix == ".json":
        return _load_json_to_dataframe(path)

    if suffix == ".xml":
        return _load_xml_to_dataframe(path)

    raise ValueError("目前僅支援 CSV / Excel / JSON / XML 檔案")


def get_column_roles(df):
    """判斷欄位類型：數值欄位 / 類別欄位"""
    numeric_cols = []
    categorical_cols = []

    for col in df.columns:
        series = df[col]
        try:
            pd.to_numeric(series, errors="coerce")
            if series.notna().sum() > 0:
                numeric_cols.append(col)
            else:
                categorical_cols.append(col)
        except Exception:
            categorical_cols.append(col)

    return numeric_cols, categorical_cols


def summarize_data(df):
    """產生資料摘要"""
    print("\n" + "=" * 60)
    print("📊 資料摘要")
    print("=" * 60)

    print(f"資料列數: {len(df)}")
    print(f"資料欄位數: {len(df.columns)}")
    print("欄位名稱:")
    for idx, col in enumerate(df.columns, 1):
        print(f"  {idx}. {col}")

    numeric_cols, categorical_cols = get_column_roles(df)

    print("\n數值欄位:")
    if numeric_cols:
        for col in numeric_cols:
            s = df[col]
            print(f"  - {col}: 平均={s.mean():.2f}, 中位數={s.median():.2f}, 最小={s.min():.2f}, 最大={s.max():.2f}")
    else:
        print("  (無數值欄位)")

    print("\n類別欄位:")
    if categorical_cols:
        for col in categorical_cols:
            print(f"  - {col}")
    else:
        print("  (無類別欄位)")

    print("\n缺失值統計:")
    missing = df.isna().sum()
    for col in df.columns:
        if missing[col] > 0:
            print(f"  - {col}: {missing[col]} 個缺失值")


def suggest_chart_type(df, x_col, y_col=None):
    """根據資料欄位類型建議圖表類型"""
    numeric_cols, categorical_cols = get_column_roles(df)

    if y_col is None:
        if x_col in numeric_cols:
            return {
                "type": "histogram",
                "reason": "單一數值欄位適合用直方圖觀察分布情況。",
            }
        return {
            "type": "bar",
            "reason": "類別欄位適合用長條圖觀察各類別數量或平均值。",
        }

    x_is_numeric = x_col in numeric_cols
    y_is_numeric = y_col in numeric_cols

    if x_is_numeric and y_is_numeric:
        return {
            "type": "scatter",
            "reason": "兩個數值欄位同時存在，適合用散佈圖觀察彼此關係。",
        }

    if y_is_numeric and not x_is_numeric:
        return {
            "type": "bar",
            "reason": "類別欄位搭配數值欄位，適合用長條圖比較不同類別的平均值。",
        }

    if x_is_numeric and not y_is_numeric:
        return {
            "type": "line",
            "reason": "數值欄位對應非數值欄位時，可用折線圖觀察趨勢。",
        }

    return {
        "type": "bar",
        "reason": "兩個欄位都不屬於數值類型，建議使用長條圖或分類比較圖。",
    }


def analyze_chart_meaning(df, chart_type, x_col, y_col=None):
    """針對圖表結果提供意義分析"""
    numeric_cols, categorical_cols = get_column_roles(df)

    if chart_type == "histogram":
        if y_col is None:
            values = df[x_col].dropna()
            mean_val = values.mean()
            std_val = values.std()
            return (
                f"這個直方圖顯示 {x_col} 的分布特徵。"
                f"平均值約為 {mean_val:.2f}，標準差約為 {std_val:.2f}，"
                f"可用來判斷資料是否集中、是否有極端值。"
            )
        values = df[y_col].dropna()
        mean_val = values.mean()
        std_val = values.std()
        return (
            f"這個直方圖顯示 {y_col} 的分布特徵。"
            f"平均值約為 {mean_val:.2f}，標準差約為 {std_val:.2f}，"
            f"可用來判斷資料是否集中、是否有極端值。"
        )

    if chart_type == "bar":
        if y_col is None:
            counts = df[x_col].value_counts(dropna=False)
            top_label = counts.idxmax()
            top_count = counts.max()
            return (
                f"長條圖顯示 {x_col} 的分布情況。"
                f"其中 {top_label} 的數量最高，約為 {top_count}，"
                f"表示此類別在資料中最為突出。"
            )

        grouped = df.groupby(x_col, dropna=False)[y_col].mean().sort_values(ascending=False)
        top_label = grouped.index[0]
        top_value = grouped.iloc[0]
        low_label = grouped.index[-1]
        low_value = grouped.iloc[-1]
        return (
            f"長條圖顯示各類別在 {y_col} 的平均表現。"
            f"{top_label} 的平均值最高，約為 {top_value:.2f}；"
            f"{low_label} 的平均值最低，約為 {low_value:.2f}。"
        )

    if chart_type == "line":
        if y_col is None:
            return "折線圖顯示資料隨時間或順序變化的趨勢，適合觀察上升、下降或波動。"
        if x_col in numeric_cols and y_col in numeric_cols:
            sorted_df = df[[x_col, y_col]].dropna().sort_values(by=x_col)
            if len(sorted_df) > 1:
                corr = sorted_df[x_col].corr(sorted_df[y_col])
                return (
                    f"折線圖顯示 {y_col} 隨 {x_col} 的變化趨勢。"
                    f"相關係數約為 {corr:.2f}，可判斷其是正相關、負相關或接近無相關。"
                )
        return "折線圖可用來觀察趨勢與變化節奏。"

    if chart_type == "scatter":
        corr = df[[x_col, y_col]].dropna().corr().iloc[0, 1]
        if abs(corr) > 0.7:
            direction = "強" if corr > 0 else "強負"
            return (
                f"散佈圖顯示 {x_col} 與 {y_col} 之間的關係。"
                f"相關係數約為 {corr:.2f}，呈現{direction}相關。"
            )
        return (
            f"散佈圖顯示 {x_col} 與 {y_col} 之間的關係。"
            f"相關係數約為 {corr:.2f}，顯示兩者關係不十分明顯。"
        )

    return "圖表已建立，請根據實際數據與上下文進一步解讀。"


def generate_chart(df, chart_type, x_col, y_col=None, output_path=None):
    """建立圖表並儲存"""
    _require_dependencies()

    if output_path is None:
        output_path = "data_analysis_chart.png"

    output_path = Path(output_path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))

    if chart_type == "histogram":
        values = df[x_col].dropna() if y_col is None else df[y_col].dropna()
        plt.hist(values, bins=10, color="#4C78A8", edgecolor="black")
        plt.title(f"{x_col if y_col is None else y_col} 分布圖")
        plt.xlabel(x_col if y_col is None else y_col)
        plt.ylabel("頻次")

    elif chart_type == "bar":
        if y_col is None:
            counts = df[x_col].value_counts(dropna=False)
            counts.plot(kind="bar", color="#F58518", edgecolor="black")
            plt.title(f"{x_col} 分類數量")
            plt.xlabel(x_col)
            plt.ylabel("數量")
        else:
            grouped = df.groupby(x_col, dropna=False)[y_col].mean().reset_index()
            plt.bar(grouped[x_col].astype(str), grouped[y_col], color="#54A24B", edgecolor="black")
            plt.title(f"{x_col} vs {y_col}")
            plt.xlabel(x_col)
            plt.ylabel(f"{y_col} 平均值")

    elif chart_type == "line":
        if y_col is None:
            plt.plot(range(len(df)), df[x_col].dropna(), marker="o")
            plt.title(f"{x_col} 趨勢圖")
            plt.xlabel("索引")
            plt.ylabel(x_col)
        else:
            sorted_df = df[[x_col, y_col]].dropna().sort_values(by=x_col)
            plt.plot(sorted_df[x_col], sorted_df[y_col], marker="o")
            plt.title(f"{x_col} vs {y_col} 趨勢圖")
            plt.xlabel(x_col)
            plt.ylabel(y_col)

    elif chart_type == "scatter":
        clean_df = df[[x_col, y_col]].dropna()
        plt.scatter(clean_df[x_col], clean_df[y_col], color="#EE854A", edgecolors="black")
        plt.title(f"{x_col} vs {y_col} 散佈圖")
        plt.xlabel(x_col)
        plt.ylabel(y_col)

    elif chart_type == "pie":
        counts = df[x_col].value_counts(dropna=False)
        plt.pie(counts.values, labels=counts.index.astype(str), autopct="%1.1f%%")
        plt.title(f"{x_col} 比例圖")

    else:
        raise ValueError(f"不支援的圖表類型: {chart_type}")

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

    return str(output_path)


def run_data_analysis():
    """互動式資料分析流程"""
    print("\n" + "=" * 60)
    print("📈 資料分析模組")
    print("=" * 60)

    try:
        _require_dependencies()
    except Exception as exc:
        print(f"❌ {exc}")
        input("\n按 Enter 返回主選單...")
        return

    file_path = input("請輸入資料檔案路徑 (CSV / Excel): ").strip()
    if not file_path:
        print("❌ 未輸入檔案路徑")
        input("\n按 Enter 返回主選單...")
        return

    try:
        df = load_data(file_path)
    except Exception as exc:
        print(f"❌ 讀取資料失敗: {exc}")
        input("\n按 Enter 返回主選單...")
        return

    summarize_data(df)

    print("\n請選擇要分析的欄位：")
    columns = list(df.columns)
    for idx, col in enumerate(columns, 1):
        print(f"  {idx}. {col}")

    try:
        x_idx = int(input("\n請輸入 X 欄位編號: ").strip()) - 1
        x_col = columns[x_idx]
    except Exception:
        print("❌ 無效的欄位選擇")
        input("\n按 Enter 返回主選單...")
        return

    y_col = input("請輸入 Y 欄位編號（留空則只分析單一欄位）: ").strip()
    if y_col:
        try:
            y_idx = int(y_col) - 1
            y_col = columns[y_idx]
        except Exception:
            print("❌ 無效的 Y 欄位選擇")
            input("\n按 Enter 返回主選單...")
            return
    else:
        y_col = None

    print("\n可用圖表類型:")
    print("  1. bar")
    print("  2. line")
    print("  3. scatter")
    print("  4. histogram")
    print("  5. pie")

    chart_choice = input("請選擇圖表類型（輸入 1-5，留空使用自動建議）: ").strip()

    if chart_choice == "1":
        chart_type = "bar"
    elif chart_choice == "2":
        chart_type = "line"
    elif chart_choice == "3":
        chart_type = "scatter"
    elif chart_choice == "4":
        chart_type = "histogram"
    elif chart_choice == "5":
        chart_type = "pie"
    else:
        suggestion = suggest_chart_type(df, x_col, y_col)
        chart_type = suggestion["type"]
        print(f"\n🤖 建議圖表類型: {chart_type}")
        print(f"理由: {suggestion['reason']}")

    output_path = input("\n請輸入圖表輸出檔名（例如: charts/output.png，留空使用預設）: ").strip()
    if not output_path:
        output_path = f"charts/{Path(file_path).stem}_{chart_type}.png"

    try:
        saved_path = generate_chart(df, chart_type, x_col, y_col=y_col, output_path=output_path)
    except Exception as exc:
        print(f"❌ 圖表生成失敗: {exc}")
        input("\n按 Enter 返回主選單...")
        return

    print("\n" + "=" * 60)
    print("🧠 圖表意義分析")
    print("=" * 60)
    meaning = analyze_chart_meaning(df, chart_type, x_col, y_col=y_col)
    print(meaning)

    print("\n✅ 圖表已成功生成並下載")
    print(f"下載路徑: {saved_path}")

    input("\n按 Enter 返回主選單...")


if __name__ == "__main__":
    run_data_analysis()