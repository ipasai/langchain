import csv
import io
import streamlit as st
import pandas as pd
from llm_factory import LLMFactory
from langchain_core.messages import HumanMessage
from i18n import t
from db_utils import (
    DBType,
    build_sql_generation_prompt,
    delete_row,
    execute_sql_query,
    get_table_columns,
    get_table_preview,
    insert_row,
    test_db_connection,
    update_row,
)

# ── 共用樣式 ───────────────────────────────────────────────────
_DIVIDER = "<hr style='border:none;border-top:1.5px solid #e0e7ff;margin:1.4rem 0;'/>"
_CARD_WRAP = (
    "background:#fff;border:1.5px solid #e0e7ff;border-radius:16px;"
    "padding:1.1rem 1.3rem;box-shadow:0 3px 12px rgba(99,102,241,0.07);"
    "margin-bottom:0.8rem;"
)


def _divider():
    st.markdown(_DIVIDER, unsafe_allow_html=True)


def _section(icon: str, title: str):
    st.markdown(
        f"<div style='font-size:1.05rem;font-weight:700;color:#4f46e5;"
        f"margin-bottom:0.35rem;'>{icon} {title}</div>",
        unsafe_allow_html=True,
    )


class DatabasePage:
    def __init__(self):
        pass

    def render(self):
        # ── 頁面標題 ──────────────────────────────────────────────
        st.markdown(
            "<h2 style='color:#4f46e5;margin-bottom:0.1rem;'>🗄️ 資料庫管理</h2>"
            "<p style='color:#6b7280;font-size:0.92rem;margin-top:0;'>"
            "連線測試・資料表瀏覽・SQL 執行・CRUD・AI SQL 生成</p>",
            unsafe_allow_html=True,
        )

        # ════════════════════════════════════════════════════════
        # 區塊 1：連線設定
        # ════════════════════════════════════════════════════════
        _section("🔌", "連線設定")

        db_options = [
            DBType.SQLITE, DBType.MYSQL, DBType.POSTGRES,
            DBType.MARIADB, DBType.REDIS, DBType.MONGODB,
        ]
        st.session_state.db_type = st.selectbox(
            t("db_type_label"),
            options=db_options,
            format_func=lambda v: v.name,
            index=db_options.index(st.session_state.db_type),
        )

        # 簽章變動偵測 → 清除舊狀態
        current_sig = (
            st.session_state.db_type.value,
            st.session_state.db_config.get("filepath", ""),
            st.session_state.db_config.get("database", ""),
            st.session_state.db_config.get("host", ""),
            st.session_state.db_config.get("port", ""),
            st.session_state.db_config.get("uri", ""),
        )
        if st.session_state.db_source_signature != current_sig:
            st.session_state.db_source_signature = current_sig
            st.session_state.db_test_result = None
            st.session_state.db_analysis = {}
            st.session_state.query_result = None
            st.session_state.selected_table = ""

        # 依資料庫類型顯示對應欄位
        if st.session_state.db_type == DBType.SQLITE:
            st.session_state.db_config["filepath"] = st.text_input(
                t("sqlite_path"),
                value=st.session_state.db_config.get("filepath", "sample.db"),
                placeholder=t("sqlite_placeholder"),
            )

        elif st.session_state.db_type in {DBType.MYSQL, DBType.MARIADB, DBType.POSTGRES}:
            h_col, p_col = st.columns([3, 1])
            with h_col:
                st.session_state.db_config["host"] = st.text_input(
                    t("host_label"),
                    value=st.session_state.db_config.get("host", "localhost"),
                )
            with p_col:
                default_port = "5432" if st.session_state.db_type == DBType.POSTGRES else "3306"
                st.session_state.db_config["port"] = st.text_input(
                    t("port_label"),
                    value=st.session_state.db_config.get("port", default_port),
                )
            u_col, pw_col = st.columns(2)
            with u_col:
                st.session_state.db_config["user"] = st.text_input(
                    t("username_label"),
                    value=st.session_state.db_config.get("user", "root"),
                )
            with pw_col:
                st.session_state.db_config["password"] = st.text_input(
                    t("password_label"),
                    value=st.session_state.db_config.get("password", ""),
                    type="password",
                )
            st.session_state.db_config["database"] = st.text_input(
                t("database_name_label"),
                value=st.session_state.db_config.get("database", ""),
            )
            if st.session_state.db_type in {DBType.MYSQL, DBType.MARIADB}:
                with st.expander("⚙️ 進階設定（選填）"):
                    st.session_state.db_config["charset"] = st.text_input(
                        t("charset_label"),
                        value=st.session_state.db_config.get("charset", "utf8mb4"),
                        help="預設為 utf8mb4，一般情況不需要修改",
                    )

        elif st.session_state.db_type == DBType.REDIS:
            rh, rp = st.columns([3, 1])
            with rh:
                st.session_state.db_config["host"] = st.text_input(
                    t("host_label"), value=st.session_state.db_config.get("host", "localhost"),
                )
            with rp:
                st.session_state.db_config["port"] = st.text_input(
                    t("port_label"), value=st.session_state.db_config.get("port", "6379"),
                )
            rw_col, rdb_col = st.columns(2)
            with rw_col:
                st.session_state.db_config["password"] = st.text_input(
                    t("password_label"), value=st.session_state.db_config.get("password", ""), type="password",
                )
            with rdb_col:
                st.session_state.db_config["db"] = st.text_input(
                    t("redis_db_label"), value=st.session_state.db_config.get("db", "0"),
                )

        elif st.session_state.db_type == DBType.MONGODB:
            st.session_state.db_config["uri"] = st.text_input(
                t("mongodb_uri"),
                value=st.session_state.db_config.get("uri", "mongodb://localhost:27017"),
                placeholder=t("mongodb_placeholder"),
            )
            st.session_state.db_config["database"] = st.text_input(
                t("mongodb_database_label"),
                value=st.session_state.db_config.get("database", ""),
            )

        if st.button("🔗 " + t("test_connection"), use_container_width=True, type="primary"):
            with st.spinner("正在測試資料庫連線與分析結構…"):
                ok, message, analysis = test_db_connection(
                    st.session_state.db_type, st.session_state.db_config,
                )
                st.session_state.db_test_result = {"ok": ok, "message": message}
                st.session_state.db_analysis = analysis

        # 連線狀態
        if st.session_state.db_test_result is not None:
            if st.session_state.db_test_result["ok"]:
                st.success(f"✅ {st.session_state.db_test_result['message']}")
            else:
                st.error(f"❌ {st.session_state.db_test_result['message']}")

        # ════════════════════════════════════════════════════════
        # 區塊 2：分析結果
        # ════════════════════════════════════════════════════════
        if st.session_state.db_analysis:
            _divider()
            _section("🔍", t("analysis_results"))

            ana = st.session_state.db_analysis
            # 摘要資訊列
            info_cols = st.columns(3)
            meta = [
                ("資料庫類型", ana.get("db_type", "—")),
                ("版本", ana.get("version", "—")),
                ("資料庫", ana.get("database", "—")),
            ]
            for col, (label, val) in zip(info_cols, meta):
                with col:
                    st.markdown(
                        f"<div style='{_CARD_WRAP}text-align:center;'>"
                        f"<div style='font-size:0.78rem;color:#9ca3af;'>{label}</div>"
                        f"<div style='font-size:0.97rem;font-weight:700;color:#1e1b4b;margin-top:0.2rem;'>{val}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            if st.session_state.db_type in {DBType.SQLITE, DBType.MYSQL, DBType.POSTGRES, DBType.MARIADB}:
                table_summary = []
                for tbl in ana.get("tables", []):
                    cols = tbl.get("columns") or []
                    table_summary.append({
                        t("table_label"): tbl.get("name"),
                        t("purpose_label"): tbl.get("purpose") or t("uncategorized_label"),
                        t("row_count_label"): tbl.get("row_count"),
                        t("columns_label"): ", ".join([f"{c.get('name')}({c.get('type')})" for c in cols]),
                        t("relationship_count_label"): len(tbl.get("relationships") or []),
                    })
                st.dataframe(table_summary, use_container_width=True)

                for tbl in ana.get("tables", []):
                    with st.expander(f"📄 {tbl.get('name')}"):
                        cols = tbl.get("columns") or []
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            st.markdown(f"**{t('purpose_label')}**：{tbl.get('purpose') or t('uncategorized_label')}")
                        with dc2:
                            st.markdown(f"**{t('row_count_label')}**：{tbl.get('row_count')}")
                        if cols:
                            badges = "".join(
                                f"<span style='display:inline-block;background:#eef2ff;color:#4338ca;"
                                f"border-radius:8px;padding:0.15rem 0.55rem;margin:0.15rem;"
                                f"font-size:0.8rem;'>{c.get('name')}<span style='color:#9ca3af;"
                                f"font-size:0.72rem;'> {c.get('type')}</span></span>"
                                for c in cols
                            )
                            st.markdown(f"**欄位**：", unsafe_allow_html=False)
                            st.markdown(badges, unsafe_allow_html=True)
                        rels = tbl.get("relationships") or []
                        if rels:
                            st.markdown(f"**{t('relationships_label')}**")
                            for rel in rels:
                                st.markdown(
                                    f"<span style='background:#fef9c3;border-radius:6px;"
                                    f"padding:0.15rem 0.5rem;font-size:0.83rem;'>"
                                    f"🔗 {rel.get('from_column')} → {rel.get('to_table')}.{rel.get('to_column')}</span>",
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.caption(t("no_relationships_hint"))
                        try:
                            preview = get_table_preview(
                                st.session_state.db_type, st.session_state.db_config,
                                tbl.get("name"), limit=st.session_state.table_page_size,
                            )
                            if preview.get("ok"):
                                records = [dict(zip(preview["columns"], row)) for row in preview["rows"]]
                                st.caption(f"內容預覽（最多 {st.session_state.table_page_size} 筆）")
                                st.dataframe(records, use_container_width=True)
                            else:
                                st.warning(preview.get("error", "無法預覽內容"))
                        except Exception as exc:
                            st.warning(f"無法預覽內容：{exc}")

            elif st.session_state.db_type == DBType.REDIS:
                st.json({
                    "keyspace": ana.get("keyspace"),
                    "db_size": ana.get("db_size"),
                    "connected_clients": ana.get("connected_clients"),
                    "used_memory": ana.get("used_memory_human"),
                })
            elif st.session_state.db_type == DBType.MONGODB:
                coll_rows = [{"集合": c.get("name"), "文件數": c.get("document_count")}
                             for c in ana.get("collections", [])]
                st.table(coll_rows)

        # ════════════════════════════════════════════════════════
        # 區塊 3：基本操作（僅 SQL 資料庫）
        # ════════════════════════════════════════════════════════
        if st.session_state.db_type not in {DBType.SQLITE, DBType.MYSQL, DBType.POSTGRES, DBType.MARIADB}:
            _divider()
            st.info(t("unsupported_sql"))
            return

        _divider()
        _section("⚙️", t("basic_operations"))

        # 重載結構按鈕（單獨一行）
        if st.button("🔄 重載資料表結構", use_container_width=False):
            st.session_state.db_test_result = None
            st.session_state.db_analysis = {}
            st.session_state.selected_table = ""
            st.session_state.query_result = None
            st.rerun()

        # 資料表選擇 + 預覽
        tables = [tbl.get("name") for tbl in st.session_state.db_analysis.get("tables", []) if tbl.get("name")]
        if tables:
            if st.session_state.selected_table not in tables:
                st.session_state.selected_table = tables[0]

            tbl_col, prev_col = st.columns([4, 1])
            with tbl_col:
                st.session_state.selected_table = st.selectbox(
                    t("select_table"),
                    options=tables,
                    index=tables.index(st.session_state.selected_table),
                )
            with prev_col:
                st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
                if st.button(t("preview"), use_container_width=True):
                    with st.spinner("載入預覽…"):
                        try:
                            st.session_state.query_result = get_table_preview(
                                st.session_state.db_type, st.session_state.db_config,
                                st.session_state.selected_table,
                            )
                        except Exception as e:
                            st.session_state.query_result = {"ok": False, "error": str(e)}

        # SQL 輸入 & 執行
        st.session_state.query_sql = st.text_area(
            t("sql_query_label"),
            value=st.session_state.query_sql,
            height=120,
            placeholder=t("sql_placeholder"),
        )
        if st.button("▶ " + t("run_sql"), use_container_width=True, type="primary"):
            if not st.session_state.query_sql.strip():
                st.warning(t("sql_query_required"))
            else:
                with st.spinner("執行 SQL 查詢…"):
                    try:
                        st.session_state.query_result = execute_sql_query(
                            st.session_state.db_type, st.session_state.db_config,
                            st.session_state.query_sql,
                        )
                    except Exception as e:
                        st.session_state.query_result = {"ok": False, "error": str(e)}

        # 查詢結果
        if st.session_state.query_result:
            result = st.session_state.query_result
            if result.get("ok"):
                if result.get("columns"):
                    records = [dict(zip(result["columns"], row)) for row in result["rows"]]

                    # 每頁筆數 + 分頁並排
                    ps_col, pg_label_col, pg_sel_col = st.columns([2, 3, 1])
                    with ps_col:
                        st.session_state.table_page_size = st.number_input(
                            "每頁筆數", min_value=5, max_value=100,
                            value=st.session_state.table_page_size, step=5,
                        )
                    total_pages = max(1, (len(records) + st.session_state.table_page_size - 1) // st.session_state.table_page_size)
                    st.session_state.table_page = min(st.session_state.table_page, total_pages - 1)
                    with pg_label_col:
                        st.markdown(
                            f"<div style='padding-top:32px;font-size:0.88rem;color:#6b7280;'>"
                            f"共 {result['row_count']} 筆，第 {st.session_state.table_page + 1}/{total_pages} 頁</div>",
                            unsafe_allow_html=True,
                        )
                    with pg_sel_col:
                        if total_pages > 1:
                            page = st.selectbox("頁數", list(range(total_pages)),
                                                index=st.session_state.table_page,
                                                label_visibility="collapsed")
                            st.session_state.table_page = page

                    start = st.session_state.table_page * st.session_state.table_page_size
                    editable_rows = records[start: start + st.session_state.table_page_size]
                    editable_df = pd.DataFrame(editable_rows)

                    edited_df = st.data_editor(
                        editable_df, use_container_width=True, hide_index=True,
                        key=f"table_editor_{st.session_state.selected_table}",
                    )

                    # 單筆刪除
                    pk_column = next(
                        (c for c in result["columns"] if c.lower() in {"id", "_id"}),
                        result["columns"][0] if result["columns"] else "",
                    )
                    del_opts = [
                        f"{i + 1}. {', '.join(str(row.get(c, '')) for c in result['columns'][:3])}"
                        for i, row in enumerate(records)
                    ]
                    del_col, del_btn_col = st.columns([3, 1])
                    with del_col:
                        sel_del = st.selectbox("刪除資料列", list(range(len(del_opts))),
                                               format_func=lambda i: del_opts[i], key="table_delete_row")
                    with del_btn_col:
                        st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️ 刪除單筆", use_container_width=True):
                            with st.spinner("刪除中…"):
                                try:
                                    target_row = records[sel_del]
                                    target_val = target_row.get(pk_column)
                                    if target_val is None:
                                        raise ValueError("找不到可用的主鍵欄位")
                                    delete_row(
                                        st.session_state.db_type, st.session_state.db_config,
                                        st.session_state.selected_table,
                                        f"{pk_column} = %s", [target_val],
                                    )
                                    st.session_state.query_result = None
                                    st.success("已刪除所選資料列")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"刪除失敗：{exc}")

                    save_col, dl_col = st.columns([1, 1])
                    with save_col:
                        if st.button("💾 保存編輯結果", use_container_width=True):
                            with st.spinner("保存中…"):
                                try:
                                    if hasattr(edited_df, "to_dict"):
                                        for row in edited_df.to_dict(orient="records"):
                                            if pk_column in row:
                                                update_row(
                                                    st.session_state.db_type, st.session_state.db_config,
                                                    st.session_state.selected_table,
                                                    {k: v for k, v in row.items() if k != pk_column},
                                                    f"{pk_column} = %s", [row[pk_column]],
                                                )
                                    st.success("已保存編輯結果")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"保存失敗：{exc}")
                    with dl_col:
                        csv_buf = io.StringIO()
                        if isinstance(edited_df, pd.DataFrame):
                            edited_df.to_csv(csv_buf, index=False)
                        else:
                            writer = csv.DictWriter(csv_buf, fieldnames=list(editable_rows[0].keys()) if editable_rows else [])
                            writer.writeheader()
                            writer.writerows(editable_rows)
                        st.download_button(
                            "⬇️ 下載 CSV", data=csv_buf.getvalue(),
                            file_name=f"{st.session_state.selected_table}_p{st.session_state.table_page + 1}.csv",
                            mime="text/csv", use_container_width=True,
                        )
                else:
                    st.success(t("sql_execution_success").format(count=result.get("row_count", 0)))
            else:
                st.error(t("sql_execution_error").format(error=result.get("error")))

        # ════════════════════════════════════════════════════════
        # 區塊 4：CRUD
        # ════════════════════════════════════════════════════════
        _divider()
        _section("✏️", t("crud_title"))

        st.session_state.crud_mode = st.selectbox(
            t("crud_mode"),
            options=["insert", "update", "delete"],
            format_func=lambda v: {"insert": t("crud_insert"), "update": t("crud_update"), "delete": t("crud_delete")}[v],
            index=["insert", "update", "delete"].index(st.session_state.crud_mode),
        )

        if st.session_state.selected_table:
            try:
                table_columns = get_table_columns(
                    st.session_state.db_type, st.session_state.db_config,
                    st.session_state.selected_table,
                )
            except Exception:
                table_columns = ["id", "name"]
            if not table_columns:
                table_columns = ["id", "name"]

            with st.container():
                if st.session_state.crud_mode == "insert":
                    # 每行兩欄
                    pairs = [table_columns[i:i+2] for i in range(0, len(table_columns), 2)]
                    for pair in pairs:
                        pair_cols = st.columns(len(pair))
                        for col, column in zip(pair_cols, pair):
                            with col:
                                st.session_state.crud_values[column] = st.text_input(
                                    column, value=st.session_state.crud_values.get(column, ""),
                                    key=f"insert_{column}",
                                )
                    if st.button(t("crud_insert_button"), use_container_width=True, type="primary"):
                        with st.spinner("新增中…"):
                            try:
                                payload = {k: v for k, v in st.session_state.crud_values.items() if v != ""}
                                res = insert_row(st.session_state.db_type, st.session_state.db_config,
                                                 st.session_state.selected_table, payload)
                                st.session_state.crud_message = {"ok": True, "message": t("crud_success_insert").format(count=res["row_count"])}
                            except Exception as e:
                                st.session_state.crud_message = {"ok": False, "message": str(e)}

                elif st.session_state.crud_mode == "update":
                    st.session_state.crud_where = st.text_input(t("update_condition_label"), value=st.session_state.crud_where)
                    pairs = [table_columns[i:i+2] for i in range(0, len(table_columns), 2)]
                    for pair in pairs:
                        pair_cols = st.columns(len(pair))
                        for col, column in zip(pair_cols, pair):
                            with col:
                                st.session_state.crud_values[column] = st.text_input(
                                    column, value=st.session_state.crud_values.get(column, ""),
                                    key=f"update_{column}",
                                )
                    st.session_state.crud_where_values = st.text_input("條件參數（逗號分隔）", value=st.session_state.crud_where_values)
                    if st.button(t("crud_update_button"), use_container_width=True, type="primary"):
                        with st.spinner("更新中…"):
                            try:
                                values = {k: v for k, v in st.session_state.crud_values.items() if v != ""}
                                where_vals = [i.strip() for i in st.session_state.crud_where_values.split(",") if i.strip()]
                                res = update_row(st.session_state.db_type, st.session_state.db_config,
                                                 st.session_state.selected_table, values,
                                                 st.session_state.crud_where, where_vals)
                                st.session_state.crud_message = {"ok": True, "message": t("crud_success_update").format(count=res["row_count"])}
                            except Exception as e:
                                st.session_state.crud_message = {"ok": False, "message": str(e)}

                else:  # delete
                    st.session_state.crud_where = st.text_input(t("delete_condition_label"), value=st.session_state.crud_where)
                    st.session_state.crud_where_values = st.text_input("條件參數（逗號分隔）", value=st.session_state.crud_where_values)
                    if st.button(t("crud_delete_button"), use_container_width=True, type="primary"):
                        with st.spinner("刪除中…"):
                            try:
                                where_vals = [i.strip() for i in st.session_state.crud_where_values.split(",") if i.strip()]
                                res = delete_row(st.session_state.db_type, st.session_state.db_config,
                                                 st.session_state.selected_table,
                                                 st.session_state.crud_where, where_vals)
                                st.session_state.crud_message = {"ok": True, "message": t("crud_success_delete").format(count=res["row_count"])}
                            except Exception as e:
                                st.session_state.crud_message = {"ok": False, "message": str(e)}

            if st.session_state.crud_message:
                msg = st.session_state.crud_message
                if msg["ok"]:
                    st.success(msg["message"])
                else:
                    st.error(msg["message"])
        else:
            st.info(t("empty_table_hint"))

        # ════════════════════════════════════════════════════════
        # 區塊 5：AI SQL 生成
        # ════════════════════════════════════════════════════════
        _divider()
        _section("🤖", t("sql_generation_title"))

        st.session_state.sql_description = st.text_area(
            t("sql_description_label"),
            value=st.session_state.sql_description,
            height=100,
            placeholder="例如：查詢過去 7 天每天的訂單數量，依日期由新到舊排列",
        )
        if st.button("✨ " + t("generate_sql"), use_container_width=True, type="primary"):
            if not st.session_state.sql_description.strip():
                st.session_state.sql_feedback = {"type": "warning", "message": t("sql_description_required")}
            elif not st.session_state.db_analysis:
                st.session_state.sql_feedback = {"type": "warning", "message": t("sql_analysis_required")}
            else:
                with st.spinner("AI 正在分析資料庫結構並生成 SQL…"):
                    prompt = build_sql_generation_prompt(
                        st.session_state.db_type, st.session_state.db_analysis,
                        st.session_state.sql_description,
                    )
                    try:
                        llm = LLMFactory.get_llm(
                            st.session_state.provider,
                            model_name=st.session_state.model,
                            temperature=st.session_state.temperature,
                        )
                        response = llm.invoke([HumanMessage(content=prompt)])
                        st.session_state.generated_sql = response.content.strip()
                        st.session_state.sql_feedback = {"type": "success", "message": "✅ 已生成 SQL 查詢建議。"}
                    except Exception as e:
                        st.session_state.generated_sql = ""
                        st.session_state.sql_feedback = {"type": "error", "message": t("sql_generation_error").format(error=e)}

        if st.session_state.sql_feedback:
            fb = st.session_state.sql_feedback
            {"success": st.success, "warning": st.warning, "error": st.error}[fb["type"]](fb["message"])

        if st.session_state.generated_sql:
            st.markdown(f"**{t('suggested_sql')}**")
            st.code(st.session_state.generated_sql, language="sql")
            if st.button("📋 複製到 SQL 輸入框", use_container_width=False):
                st.session_state.query_sql = st.session_state.generated_sql
                st.rerun()
