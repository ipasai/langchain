import csv
import io
import json
from pathlib import Path

import streamlit as st

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


DEFAULT_HISTORY_PATH = Path("data") / "analysis_history.json"


def _require_dependencies():
    if pd is None or plt is None:
        st.error("缺少必要套件，請先安裝：`pip install pandas matplotlib openpyxl`")
        st.stop()


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
    numeric_cols = []
    categorical_cols = []

    for col in df.columns:
        series = df[col]
        try:
            pd.to_numeric(series, errors="coerce")
            numeric_cols.append(col)
        except Exception:
            categorical_cols.append(col)

    return numeric_cols, categorical_cols


def suggest_chart_type(df, x_col, y_col=None):
    numeric_cols, _ = get_column_roles(df)

    if y_col is None:
        if x_col in numeric_cols:
            return {
                "type": "histogram",
                "reason": "單一數值欄位適合用直方圖觀察分布。",
            }
        return {
            "type": "bar",
            "reason": "類別欄位適合用長條圖觀察數量分布。",
        }

    x_is_numeric = x_col in numeric_cols
    y_is_numeric = y_col in numeric_cols

    if x_is_numeric and y_is_numeric:
        return {
            "type": "scatter",
            "reason": "兩個數值欄位適合用散佈圖觀察相關性。",
        }

    if y_is_numeric and not x_is_numeric:
        return {
            "type": "bar",
            "reason": "類別欄位搭配數值欄位，適合用長條圖比較平均值。",
        }

    return {
        "type": "bar",
        "reason": "建議使用長條圖做分類比較。",
    }


def analyze_chart_meaning(df, chart_type, x_col, y_col=None):
    if chart_type == "histogram":
        values = df[x_col].dropna() if y_col is None else df[y_col].dropna()
        mean_val = values.mean()
        std_val = values.std()
        return f"這個圖顯示資料分布情況，平均值約為 {mean_val:.2f}，標準差約為 {std_val:.2f}。"

    if chart_type == "bar":
        if y_col is None:
            counts = df[x_col].value_counts(dropna=False)
            top_label = counts.idxmax()
            top_value = counts.max()
            return f"{top_label} 的數量最高，約為 {top_value}。"
        grouped = df.groupby(x_col, dropna=False)[y_col].mean().sort_values(ascending=False)
        top_label = grouped.index[0]
        top_value = grouped.iloc[0]
        return f"{top_label} 的平均值最高，約為 {top_value:.2f}。"

    if chart_type == "scatter":
        corr = df[[x_col, y_col]].dropna().corr().iloc[0, 1]
        return f"散佈圖顯示 {x_col} 與 {y_col} 的相關性，相關係數約為 {corr:.2f}。"

    if chart_type == "line":
        return "折線圖能幫助你觀察資料的趨勢與變化方向。"

    if chart_type == "pie":
        counts = df[x_col].value_counts(dropna=False)
        top_label = counts.idxmax()
        return f"{top_label} 在資料中占比最突出。"

    return "圖表已建立，請根據數據與情境進一步解讀。"


def get_analysis_history_path(history_path=None):
    if history_path is None:
        history_path = DEFAULT_HISTORY_PATH
    history_path = Path(history_path).expanduser()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    return history_path


def load_analysis_history(history_path=None):
    path = get_analysis_history_path(history_path)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        return []
    return []


def save_analysis_history_entry(history_path, entry):
    path = get_analysis_history_path(history_path)
    history = load_analysis_history(path)
    history.append(entry)
    history = history[-20:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def remove_analysis_history_entry(history_path, index):
    path = get_analysis_history_path(history_path)
    history = load_analysis_history(path)
    if 0 <= index < len(history):
        del history[index]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return history


def export_history_to_csv(history_entries):
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["file_name", "file_path", "x_col", "y_col", "chart_type", "saved_path", "created_at"],
    )
    writer.writeheader()
    for entry in history_entries:
        writer.writerow(entry)
    return output.getvalue()


def build_chart_config_defaults(df, x_col, y_col=None, chart_type="bar"):
    numeric_cols, _ = get_column_roles(df)
    y_is_numeric = y_col in numeric_cols if y_col else False

    defaults = {
        "title": f"{x_col} vs {y_col}" if y_col else x_col,
        "x_label": x_col,
        "y_label": y_col or "數量",
        "color": "#4C78A8",
        "bins": 10,
        "show_grid": True,
        "aggregation": "平均值" if chart_type in {"bar", "line"} and y_col and y_is_numeric else "計數",
        "figsize": (8.5, 5.2),
    }

    if chart_type == "histogram":
        defaults.update({"title": f"{x_col if y_col is None else y_col} 分布圖", "x_label": x_col if y_col is None else y_col, "y_label": "頻次", "color": "#4C78A8"})
    elif chart_type == "bar":
        defaults.update({"title": f"{x_col} vs {y_col}" if y_col else f"{x_col} 分類比較", "x_label": x_col, "y_label": y_col or "數量", "color": "#54A24B"})
    elif chart_type == "line":
        defaults.update({"title": f"{x_col} 趨勢圖", "x_label": x_col, "y_label": y_col or x_col, "color": "#F58518"})
    elif chart_type == "scatter":
        defaults.update({"title": f"{x_col} vs {y_col}", "x_label": x_col, "y_label": y_col or "值", "color": "#EE854A"})
    elif chart_type == "pie":
        defaults.update({"title": f"{x_col} 比例圖", "color": "#3B82F6"})

    return defaults


def generate_chart(df, chart_type, x_col, y_col=None, output_path=None, config=None):
    _require_dependencies()

    if output_path is None:
        output_path = "chart.png"

    output_path = Path(output_path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chart_config = build_chart_config_defaults(df, x_col, y_col, chart_type) if config is None else config
    plt.figure(figsize=chart_config.get("figsize", (8.5, 5.2)))
    plt.style.use("seaborn-v0_8-whitegrid")

    if chart_type == "histogram":
        values = df[x_col].dropna() if y_col is None else df[y_col].dropna()
        plt.hist(values, bins=chart_config.get("bins", 10), color=chart_config.get("color", "#4C78A8"), edgecolor="black")
        plt.title(chart_config.get("title", f"{x_col if y_col is None else y_col} 分布圖"))
        plt.xlabel(chart_config.get("x_label", x_col if y_col is None else y_col))
        plt.ylabel(chart_config.get("y_label", "頻次"))

    elif chart_type == "bar":
        if y_col is None:
            counts = df[x_col].value_counts(dropna=False)
            counts.plot(kind="bar", color=chart_config.get("color", "#54A24B"), edgecolor="black")
            plt.title(chart_config.get("title", f"{x_col} 分類數量"))
            plt.xlabel(chart_config.get("x_label", x_col))
            plt.ylabel(chart_config.get("y_label", "數量"))
        else:
            if chart_config.get("aggregation", "平均值") == "計數":
                grouped = df.groupby(x_col, dropna=False)[y_col].count().reset_index(name="count")
                values = grouped["count"]
            else:
                grouped = df.groupby(x_col, dropna=False)[y_col].mean().reset_index()
                values = grouped[y_col]
            plt.bar(grouped[x_col].astype(str), values, color=chart_config.get("color", "#54A24B"), edgecolor="black")
            plt.title(chart_config.get("title", f"{x_col} vs {y_col}"))
            plt.xlabel(chart_config.get("x_label", x_col))
            plt.ylabel(chart_config.get("y_label", y_col))

    elif chart_type == "line":
        if y_col is None:
            plt.plot(range(len(df)), df[x_col].dropna(), marker="o", color=chart_config.get("color", "#F58518"))
            plt.title(chart_config.get("title", f"{x_col} 趨勢圖"))
            plt.xlabel(chart_config.get("x_label", "索引"))
            plt.ylabel(chart_config.get("y_label", x_col))
        else:
            sorted_df = df[[x_col, y_col]].dropna().sort_values(by=x_col)
            plt.plot(sorted_df[x_col], sorted_df[y_col], marker="o", color=chart_config.get("color", "#F58518"))
            plt.title(chart_config.get("title", f"{x_col} vs {y_col} 趨勢圖"))
            plt.xlabel(chart_config.get("x_label", x_col))
            plt.ylabel(chart_config.get("y_label", y_col))

    elif chart_type == "scatter":
        clean_df = df[[x_col, y_col]].dropna()
        plt.scatter(clean_df[x_col], clean_df[y_col], color=chart_config.get("color", "#EE854A"), edgecolors="black")
        plt.title(chart_config.get("title", f"{x_col} vs {y_col} 散佈圖"))
        plt.xlabel(chart_config.get("x_label", x_col))
        plt.ylabel(chart_config.get("y_label", y_col))

    elif chart_type == "pie":
        counts = df[x_col].value_counts(dropna=False)
        plt.pie(counts.values, labels=counts.index.astype(str), autopct="%1.1f%%", colors=[chart_config.get("color", "#3B82F6")] * len(counts))
        plt.title(chart_config.get("title", f"{x_col} 比例圖"))

    else:
        raise ValueError(f"不支援的圖表類型: {chart_type}")

    if chart_config.get("show_grid", True):
        plt.grid(True, alpha=0.25)

    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()

    return str(output_path)


def group_history_entries(history_entries, search_query=""):
    filtered_entries = history_entries
    if search_query:
        query = search_query.lower()
        filtered_entries = [
            entry for entry in history_entries
            if query in str(entry.get("file_name", "")).lower()
            or query in str(entry.get("chart_type", "")).lower()
            or query in str(entry.get("x_col", "")).lower()
            or query in str(entry.get("y_col", "")).lower()
        ]

    grouped = {}
    for entry in filtered_entries:
        created_at = entry.get("created_at", "")
        date_key = created_at.split(" ")[0] if created_at else "未知日期"
        grouped.setdefault(date_key, []).append(entry)

    ordered_dates = sorted(grouped.keys(), reverse=True)
    return [(date_key, grouped[date_key]) for date_key in ordered_dates]


class DataAnalysisPage:
    def render(self):
        st.markdown(
            """
            <style>
            .block-container { padding-top: 1rem; }
            .stTextInput > div > div > input,
            .stSelectbox > div > div > div,
            .stNumberInput input {
                font-size: 0.95rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<h2 style='margin-bottom:0.2rem;'>📊 資料分析</h2>", unsafe_allow_html=True)
        st.caption("上傳資料檔後，先選擇欄位與圖表設定，再生成圖表與分析摘要。")

        history_path = get_analysis_history_path()
        history_entries = load_analysis_history(history_path)
        search_query = st.text_input("搜尋歷史紀錄", key="analysis_history_search")

        selected_history_entry = st.session_state.get("selected_history_entry")
        uploaded_file = st.file_uploader(
            "上傳資料檔",
            type=["csv", "xlsx", "xls", "json", "xml"],
            key="data_analysis_upload",
            help="支援 CSV / Excel / JSON / XML，建議先上傳再進行分析。",
        )

        source_path = None
        if uploaded_file is not None:
            temp_dir = Path("temp_uploads")
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / uploaded_file.name
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            source_path = str(temp_path)
        elif selected_history_entry and selected_history_entry.get("file_path"):
            source_path = selected_history_entry["file_path"]
            if not Path(source_path).exists():
                st.error("歷史紀錄中的檔案已不存在。")
                return

        if source_path is None:
            if history_entries:
                st.subheader("📜 最近分析摘要")
                latest_entry = history_entries[-1]
                latest_file = latest_entry.get("file_name", "-")
                latest_chart = latest_entry.get("chart_type", "-")
                latest_time = latest_entry.get("created_at", "-")
                metrics = st.columns(4)
                metrics[0].metric("歷史筆數", len(history_entries))
                metrics[1].metric("最新檔案", latest_file)
                metrics[2].metric("最新圖表", latest_chart)
                metrics[3].metric("最新時間", latest_time)
            self._render_history_section(history_entries, history_path, search_query)
            return

        try:
            df = load_data(source_path)
        except Exception as e:
            st.error(f"讀取檔案失敗：{e}")
            return

        file_name = Path(source_path).name
        uploaded_name = uploaded_file.name if uploaded_file is not None else file_name
        st.success(f"已成功讀取：{uploaded_name}")

        with st.expander("📋 資料預覽與摘要", expanded=True):
            st.dataframe(df.head(50), use_container_width=True)
            col1, col2, col3 = st.columns(3)
            col1.metric("資料列數", len(df))
            col2.metric("資料欄位數", len(df.columns))
            col3.metric("缺失值總數", int(df.isna().sum().sum()))
            numeric_cols, categorical_cols = get_column_roles(df)
            st.caption(f"數值欄位：{numeric_cols or '無'}")
            st.caption(f"類別欄位：{categorical_cols or '無'}")

        with st.expander("⚙️ 圖表設定", expanded=True):
            default_x = selected_history_entry.get("x_col") if selected_history_entry else None
            default_y = selected_history_entry.get("y_col") if selected_history_entry else None
            x_col = st.selectbox("選擇 X 欄位", df.columns, index=df.columns.get_loc(default_x) if default_x in df.columns else 0, key="data_analysis_x")
            y_options = [""] + list(df.columns)
            default_y_index = 0
            if default_y in y_options:
                default_y_index = y_options.index(default_y)
            y_col_option = st.selectbox("選擇 Y 欄位（可留空）", y_options, index=default_y_index, key="data_analysis_y")
            y_col = y_col_option if y_col_option else None

            chart_type_choice = st.selectbox(
                "圖表類型",
                ["自動建議", "bar", "line", "scatter", "histogram", "pie"],
                key="data_analysis_chart_type",
            )

            if chart_type_choice == "自動建議":
                suggestion = suggest_chart_type(df, x_col, y_col)
                chart_type = suggestion["type"]
                st.info(f"建議圖表：{chart_type}")
                st.caption(f"原因：{suggestion['reason']}")
            else:
                chart_type = chart_type_choice

            chart_config = build_chart_config_defaults(df, x_col, y_col, chart_type)
            chart_title = st.text_input("圖表標題", value=chart_config["title"], key="data_analysis_title")
            chart_config["title"] = chart_title
            chart_config["x_label"] = st.text_input("X 軸標籤", value=chart_config["x_label"], key="data_analysis_x_label")
            chart_config["y_label"] = st.text_input("Y 軸標籤", value=chart_config["y_label"], key="data_analysis_y_label")
            chart_config["color"] = st.color_picker("圖表顏色", value=chart_config["color"], key="data_analysis_color")
            chart_config["bins"] = st.number_input("分箱數", min_value=3, max_value=50, value=chart_config["bins"], step=1, key="data_analysis_bins")
            chart_config["aggregation"] = st.selectbox(
                "聚合方式",
                ["平均值", "計數"],
                index=0 if chart_config["aggregation"] == "平均值" else 1,
                key="data_analysis_aggregation",
            )
            chart_config["show_grid"] = st.checkbox("顯示格線", value=chart_config["show_grid"], key="data_analysis_show_grid")
            chart_config["figsize"] = (8.5, 5.2)

            if st.button("🤖 生成圖表與分析", type="primary", use_container_width=True, key="generate_data_analysis_chart"):
                output_dir = Path("charts")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{Path(file_name).stem}_{chart_type}.png"
                saved_path = generate_chart(df, chart_type, x_col, y_col=y_col, output_path=str(output_path), config=chart_config)

                entry = {
                    "file_name": file_name,
                    "file_path": source_path,
                    "x_col": x_col,
                    "y_col": y_col,
                    "chart_type": chart_type,
                    "saved_path": saved_path,
                    "created_at": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S") if pd is not None else "unknown",
                }
                save_analysis_history_entry(history_path, entry)

                st.subheader("📈 圖表結果")
                st.image(saved_path, caption=chart_title or f"{chart_type} 圖表")
                with open(saved_path, "rb") as f:
                    chart_bytes = f.read()
                st.download_button(
                    label="下載圖表",
                    data=chart_bytes,
                    file_name=output_path.name,
                    mime="image/png",
                )

                st.subheader("🧠 圖表意義分析")
                st.write(analyze_chart_meaning(df, chart_type, x_col, y_col=y_col))

        self._render_history_section(history_entries, history_path, search_query)

    def _render_history_section(self, history_entries, history_path, search_query):
        if not history_entries:
            st.info("尚無分析歷史，先生成一次圖表即可建立。")
            return

        st.subheader("📜 分析歷史紀錄")
        st.caption("可依日期分組顯示、搜尋、刪除、重跑與匯出。")
        history_groups = group_history_entries(history_entries, search_query)
        delete_candidates = []
        for date_key, entries in history_groups:
            st.subheader(date_key)
            for entry in entries:
                original_index = history_entries.index(entry)
                delete_candidates.append((original_index, f"{entry.get('file_name', '未知檔案')} | {entry.get('chart_type', '-')}"))
                with st.container():
                    col1, col2, col3, col4, col5, col6 = st.columns([3, 2.4, 2.4, 1.2, 1.2, 1.2])
                    col1.write(entry.get("file_name", "未知檔案"))
                    col2.write(f"X: {entry.get('x_col', '-')} | Y: {entry.get('y_col', '-')}")
                    col3.write(f"圖表: {entry.get('chart_type', '-')} | {entry.get('created_at', '-')}")
                    if col4.button("圖表", key=f"preview_history_{original_index}"):
                        st.session_state["preview_history_chart_path"] = entry.get("saved_path")
                    if col5.button("重跑", key=f"rerun_history_{original_index}"):
                        try:
                            df = load_data(entry.get("file_path"))
                            output_dir = Path("charts")
                            output_dir.mkdir(parents=True, exist_ok=True)
                            output_path = output_dir / f"{Path(entry.get('file_name', 'analysis')).stem}_{entry.get('chart_type', 'chart')}_rerun.png"
                            saved_path = generate_chart(df, entry.get("chart_type"), entry.get("x_col"), y_col=entry.get("y_col"), output_path=str(output_path))
                            new_entry = dict(entry)
                            new_entry["saved_path"] = saved_path
                            new_entry["created_at"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S") if pd is not None else "unknown"
                            save_analysis_history_entry(history_path, new_entry)
                            st.session_state["preview_history_chart_path"] = saved_path
                            st.success("已重新生成圖表")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"重跑失敗：{exc}")
                    if col6.button("刪除", key=f"delete_history_{original_index}"):
                        remove_analysis_history_entry(history_path, original_index)
                        st.session_state.pop("selected_history_entry", None)
                        st.session_state.pop("preview_history_chart_path", None)
                        st.rerun()

        if delete_candidates:
            selected_to_delete = st.multiselect(
                "批次刪除歷史",
                options=[item[0] for item in delete_candidates],
                format_func=lambda idx: next(label for item_idx, label in delete_candidates if item_idx == idx),
                key="analysis_history_delete_candidates",
            )
            if st.button("刪除選取項目"):
                for index in sorted(selected_to_delete, reverse=True):
                    remove_analysis_history_entry(history_path, index)
                st.session_state.pop("selected_history_entry", None)
                st.session_state.pop("preview_history_chart_path", None)
                st.rerun()

        export_col1, export_col2 = st.columns(2)
        with export_col1:
            history_json = json.dumps(history_entries, ensure_ascii=False, indent=2)
            st.download_button(
                label="下載 JSON",
                data=history_json,
                file_name="analysis_history.json",
                mime="application/json",
                key="download_analysis_history_json",
            )
        with export_col2:
            history_csv = export_history_to_csv(history_entries)
            st.download_button(
                label="下載 CSV",
                data=history_csv,
                file_name="analysis_history.csv",
                mime="text/csv",
                key="download_analysis_history_csv",
            )

        if st.session_state.get("preview_history_chart_path"):
            preview_chart_path = st.session_state["preview_history_chart_path"]
            if Path(preview_chart_path).exists():
                st.subheader("🖼️ 歷史圖表預覽")
                st.image(preview_chart_path, use_container_width=True)
