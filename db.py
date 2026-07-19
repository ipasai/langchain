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

class DatabasePage:
    def __init__(self):
        pass

    def render(self):
        st.subheader(t("db_management"))

        db_options = [
            DBType.SQLITE,
            DBType.MYSQL,
            DBType.POSTGRES,
            DBType.MARIADB,
            DBType.REDIS,
            DBType.MONGODB,
        ]
        st.session_state.db_type = st.selectbox(
            t("db_type_label"),
            options=db_options,
            format_func=lambda value: value.name,
            index=db_options.index(st.session_state.db_type),
        )

        current_db_signature = (
            st.session_state.db_type.value,
            st.session_state.db_config.get("filepath", ""),
            st.session_state.db_config.get("database", ""),
            st.session_state.db_config.get("host", ""),
            st.session_state.db_config.get("port", ""),
            st.session_state.db_config.get("uri", ""),
        )
        if st.session_state.db_source_signature != current_db_signature:
            st.session_state.db_source_signature = current_db_signature
            st.session_state.db_test_result = None
            st.session_state.db_analysis = {}
            st.session_state.query_result = None
            st.session_state.selected_table = ""

        if st.session_state.db_type == DBType.SQLITE:
            st.session_state.db_config["filepath"] = st.text_input(
                t("sqlite_path"),
                value=st.session_state.db_config.get("filepath", "sample.db"),
                placeholder=t("sqlite_placeholder"),
            )
        elif st.session_state.db_type in {DBType.MYSQL, DBType.MARIADB, DBType.POSTGRES}:
            st.session_state.db_config["host"] = st.text_input(
                t("host_label"),
                value=st.session_state.db_config.get("host", "localhost"),
            )
            st.session_state.db_config["port"] = st.text_input(
                t("port_label"),
                value=st.session_state.db_config.get("port", "5432" if st.session_state.db_type == DBType.POSTGRES else "3306"),
            )
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.db_config["user"] = st.text_input(
                    t("username_label"),
                    value=st.session_state.db_config.get("user", "root"),
                )
            with col2:
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
                st.session_state.db_config["charset"] = st.text_input(
                    t("charset_label"),
                    value=st.session_state.db_config.get("charset", "utf8mb4"),
                )
        elif st.session_state.db_type == DBType.REDIS:
            st.session_state.db_config["host"] = st.text_input(
                t("host_label"),
                value=st.session_state.db_config.get("host", "localhost"),
            )
            st.session_state.db_config["port"] = st.text_input(
                t("port_label"),
                value=st.session_state.db_config.get("port", "6379"),
            )
            st.session_state.db_config["password"] = st.text_input(
                t("password_label"),
                value=st.session_state.db_config.get("password", ""),
                type="password",
            )
            st.session_state.db_config["db"] = st.text_input(
                t("redis_db_label"),
                value=st.session_state.db_config.get("db", "0"),
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

        if st.button(t("test_connection"), use_container_width=True):
            with st.spinner("正在測試資料庫連線與分析結構..."):
                ok, message, analysis = test_db_connection(
                    st.session_state.db_type,
                    st.session_state.db_config,
                )
                st.session_state.db_test_result = {"ok": ok, "message": message}
                st.session_state.db_analysis = analysis

        if st.session_state.db_test_result is not None:
            if st.session_state.db_test_result["ok"]:
                st.success(f"✅ {st.session_state.db_test_result['message']}")
            else:
                st.error(f"❌ {st.session_state.db_test_result['message']}")

        if st.session_state.db_analysis:
            st.markdown("---")
            st.subheader(t("analysis_results"))
            st.write(f"**{t('database_type')}**: {st.session_state.db_analysis.get('db_type')}  |  **{t('version_label')}**: {st.session_state.db_analysis.get('version')}")
            st.write(f"**{t('connection_config')}**: `{st.session_state.db_analysis.get('config')}`")

            if st.session_state.db_type in {DBType.SQLITE, DBType.MYSQL, DBType.POSTGRES, DBType.MARIADB}:
                table_summary = []
                for table in st.session_state.db_analysis.get("tables", []):
                    columns = table.get("columns") or []
                    table_summary.append({
                        t("table_label"): table.get("name"),
                        t("purpose_label"): table.get("purpose") or t("uncategorized_label"),
                        t("row_count_label"): table.get("row_count"),
                        t("columns_label"): ", ".join([f"{c.get('name')}({c.get('type')})" for c in columns]),
                        t("relationship_count_label"): len(table.get("relationships") or []),
                    })
                st.dataframe(table_summary, use_container_width=True)

                for table in st.session_state.db_analysis.get("tables", []):
                    with st.expander(f"📄 {table.get('name')}"):
                        cols = table.get("columns") or []
                        st.write(f"**{t('purpose_label')}**: {table.get('purpose') or t('uncategorized_label')}")
                        st.write(f"**{t('row_count_label')}**: {table.get('row_count')}")
                        if cols:
                            st.write(f"**{t('columns_label')}**: " + ", ".join([f"{c.get('name')}({c.get('type')})" for c in cols]))
                        relationships = table.get("relationships") or []
                        if relationships:
                            st.write(f"**{t('relationships_label')}**")
                            for rel in relationships:
                                st.write(f"- {rel.get('from_column')} → {rel.get('to_table')}.{rel.get('to_column')}")
                        else:
                            st.info(t("no_relationships_hint"))

                        try:
                            preview = get_table_preview(
                                st.session_state.db_type,
                                st.session_state.db_config,
                                table.get("name"),
                                limit=st.session_state.table_page_size,
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
                    "keyspace": st.session_state.db_analysis.get("keyspace"),
                    "db_size": st.session_state.db_analysis.get("db_size"),
                    "connected_clients": st.session_state.db_analysis.get("connected_clients"),
                    "used_memory": st.session_state.db_analysis.get("used_memory_human"),
                })
            elif st.session_state.db_type == DBType.MONGODB:
                collection_summary = [
                    {"集合": item.get("name"), "文件數": item.get("document_count")} for item in st.session_state.db_analysis.get("collections", [])
                ]
                st.table(collection_summary)

        if st.session_state.db_type in {DBType.SQLITE, DBType.MYSQL, DBType.POSTGRES, DBType.MARIADB}:
            st.markdown("---")
            st.subheader(t("basic_operations"))

            if st.button("🔄 重載資料表結構", use_container_width=True):
                st.session_state.db_test_result = None
                st.session_state.db_analysis = {}
                st.session_state.selected_table = ""
                st.session_state.query_result = None
                st.rerun()

            tables = [table.get("name") for table in st.session_state.db_analysis.get("tables", []) if table.get("name")]
            if tables:
                if st.session_state.selected_table not in tables:
                    st.session_state.selected_table = tables[0]
                table_col, preview_col = st.columns([4, 1])
                with table_col:
                    st.session_state.selected_table = st.selectbox(
                        t("select_table"),
                        options=tables,
                        index=tables.index(st.session_state.selected_table),
                    )
                with preview_col:
                    st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button(t("preview"), use_container_width=True):
                        with st.spinner("正在載入資料表預覽..."):
                            try:
                                st.session_state.query_result = get_table_preview(
                                    st.session_state.db_type,
                                    st.session_state.db_config,
                                    st.session_state.selected_table,
                                )
                            except Exception as e:
                                st.session_state.query_result = {"ok": False, "error": str(e)}

            col_page_size, col_refresh = st.columns([3, 2])
            with col_page_size:
                st.session_state.table_page_size = st.number_input(
                    "每頁筆數",
                    min_value=5,
                    max_value=100,
                    value=st.session_state.table_page_size,
                    step=5,
                )
            with col_refresh:
                st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 重新載入", use_container_width=True):
                    st.rerun()

            st.session_state.query_sql = st.text_area(
                t("sql_query_label"),
                value=st.session_state.query_sql,
                height=140,
                placeholder=t("sql_placeholder"),
            )
            if st.button(t("run_sql"), use_container_width=True):
                if not st.session_state.query_sql.strip():
                    st.warning(t("sql_query_required"))
                else:
                    with st.spinner("正在執行 SQL 查詢..."):
                        try:
                            st.session_state.query_result = execute_sql_query(
                                st.session_state.db_type,
                                st.session_state.db_config,
                                st.session_state.query_sql,
                            )
                        except Exception as e:
                            st.session_state.query_result = {"ok": False, "error": str(e)}

            if st.session_state.query_result:
                if st.session_state.query_result.get("ok"):
                    result = st.session_state.query_result
                    if result.get("columns"):
                        records = [dict(zip(result["columns"], row)) for row in result["rows"]]
                        total_pages = max(1, (len(records) + st.session_state.table_page_size - 1) // st.session_state.table_page_size)
                        st.session_state.table_page = min(st.session_state.table_page, total_pages - 1)
                        if total_pages > 1:
                            page_col1, page_col2 = st.columns([3, 1])
                            with page_col1:
                                st.caption(t("query_result_label") + f": {t('query_result_count').format(count=result['row_count'])}")
                            with page_col2:
                                page = st.selectbox("頁數", options=list(range(total_pages)), index=st.session_state.table_page)
                                st.session_state.table_page = page
                        else:
                            st.caption(t("query_result_label") + f": {t('query_result_count').format(count=result['row_count'])}")
                        start = st.session_state.table_page * st.session_state.table_page_size
                        end = start + st.session_state.table_page_size
                        editable_rows = records[start:end]
                        editable_df = pd.DataFrame(editable_rows)
                        with st.container():
                            st.markdown("<div style='border:1px solid #e5e7eb;border-radius:14px;padding:1rem;background:linear-gradient(135deg,#f9fafb 0%, #eef2ff 100%);'>", unsafe_allow_html=True)
                            edited_df = st.data_editor(
                                editable_df,
                                use_container_width=True,
                                hide_index=True,
                                key=f"table_editor_{st.session_state.selected_table}",
                            )
                            st.markdown("</div>", unsafe_allow_html=True)
                        delete_target_col, delete_action_col = st.columns([3, 1])
                        with delete_target_col:
                            pk_column = next((column for column in result["columns"] if column.lower() in {"id", "_id"}), result["columns"][0] if result["columns"] else "")
                            delete_row_options = [f"{idx + 1}. {', '.join(str(row.get(col, '')) for col in result['columns'][:3])}" for idx, row in enumerate(records)]
                            selected_delete_index = st.selectbox("刪除資料列", options=list(range(len(delete_row_options))), format_func=lambda idx: delete_row_options[idx], key="table_delete_row")
                        with delete_action_col:
                            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
                            if st.button("🗑️ 刪除單筆", use_container_width=True):
                                with st.spinner("正在刪除資料列..."):
                                    try:
                                        target_row = records[selected_delete_index]
                                        target_value = target_row.get(pk_column)
                                        if target_value is None:
                                            raise ValueError("找不到可用的主鍵欄位")
                                        delete_row(
                                            st.session_state.db_type,
                                            st.session_state.db_config,
                                            st.session_state.selected_table,
                                            f"{pk_column} = %s",
                                            [target_value],
                                        )
                                        st.session_state.query_result = None
                                        st.success("已刪除所選資料列")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"刪除失敗：{exc}")
                        if st.button("💾 保存編輯結果", use_container_width=True):
                            with st.spinner("正在保存編輯結果..."):
                                try:
                                    if hasattr(edited_df, "to_dict"):
                                        for row in edited_df.to_dict(orient="records"):
                                            if pk_column in row:
                                                update_row(
                                                    st.session_state.db_type,
                                                    st.session_state.db_config,
                                                    st.session_state.selected_table,
                                                    {k: v for k, v in row.items() if k != pk_column},
                                                    f"{pk_column} = %s",
                                                    [row[pk_column]],
                                                )
                                    st.success("已保存編輯結果")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"保存失敗：{exc}")

                        csv_buffer = io.StringIO()
                        if isinstance(edited_df, pd.DataFrame):
                            edited_df.to_csv(csv_buffer, index=False)
                        else:
                            writer = csv.DictWriter(csv_buffer, fieldnames=list(editable_rows[0].keys()) if editable_rows else [])
                            writer.writeheader()
                            writer.writerows(editable_rows)
                        st.download_button(
                            label="⬇️ 下載 CSV",
                            data=csv_buffer.getvalue(),
                            file_name=f"{st.session_state.selected_table}_page_{st.session_state.table_page + 1}.csv",
                            mime="text/csv",
                        )
                    else:
                        st.success(t("sql_execution_success").format(count=result.get('row_count', 0)))
                else:
                    st.error(t("sql_execution_error").format(error=st.session_state.query_result.get('error')))

            st.markdown("---")
            st.subheader(t("crud_title"))
            st.session_state.crud_mode = st.selectbox(
                t("crud_mode"),
                options=["insert", "update", "delete"],
                format_func=lambda value: {"insert": t("crud_insert"), "update": t("crud_update"), "delete": t("crud_delete")}[value],
                index=["insert", "update", "delete"].index(st.session_state.crud_mode),
            )

            if st.session_state.selected_table:
                try:
                    table_columns = get_table_columns(
                        st.session_state.db_type,
                        st.session_state.db_config,
                        st.session_state.selected_table,
                    )
                except Exception:
                    table_columns = ["id", "name"]

                if not table_columns:
                    table_columns = ["id", "name"]

                if st.session_state.crud_mode == "insert":
                    for column in table_columns:
                        st.session_state.crud_values[column] = st.text_input(
                            f"{column}",
                            value=st.session_state.crud_values.get(column, ""),
                            key=f"insert_{column}",
                        )
                    if st.button(t("crud_insert_button"), use_container_width=True):
                        with st.spinner("正在新增資料列..."):
                            try:
                                payload = {k: v for k, v in st.session_state.crud_values.items() if v != ""}
                                result = insert_row(st.session_state.db_type, st.session_state.db_config, st.session_state.selected_table, payload)
                                st.session_state.crud_message = {"ok": True, "message": t("crud_success_insert").format(count=result['row_count'])}
                            except Exception as e:
                                st.session_state.crud_message = {"ok": False, "message": str(e)}
                elif st.session_state.crud_mode == "update":
                    st.session_state.crud_where = st.text_input(t("update_condition_label"), value=st.session_state.crud_where)
                    for column in table_columns:
                        st.session_state.crud_values[column] = st.text_input(
                            f"{column}",
                            value=st.session_state.crud_values.get(column, ""),
                            key=f"update_{column}",
                        )
                    st.session_state.crud_where_values = st.text_input("條件參數（以逗號分隔）", value=st.session_state.crud_where_values)
                    if st.button(t("crud_update_button"), use_container_width=True):
                        with st.spinner("正在更新資料列..."):
                            try:
                                values = {k: v for k, v in st.session_state.crud_values.items() if v != ""}
                                where_values = [item.strip() for item in st.session_state.crud_where_values.split(",") if item.strip()]
                                result = update_row(st.session_state.db_type, st.session_state.db_config, st.session_state.selected_table, values, st.session_state.crud_where, where_values)
                                st.session_state.crud_message = {"ok": True, "message": t("crud_success_update").format(count=result['row_count'])}
                            except Exception as e:
                                st.session_state.crud_message = {"ok": False, "message": str(e)}
                else:
                    st.session_state.crud_where = st.text_input(t("delete_condition_label"), value=st.session_state.crud_where)
                    st.session_state.crud_where_values = st.text_input("條件參數（以逗號分隔）", value=st.session_state.crud_where_values)
                    if st.button(t("crud_delete_button"), use_container_width=True):
                        with st.spinner("正在刪除資料列..."):
                            try:
                                where_values = [item.strip() for item in st.session_state.crud_where_values.split(",") if item.strip()]
                                result = delete_row(st.session_state.db_type, st.session_state.db_config, st.session_state.selected_table, st.session_state.crud_where, where_values)
                                st.session_state.crud_message = {"ok": True, "message": t("crud_success_delete").format(count=result['row_count'])}
                            except Exception as e:
                                st.session_state.crud_message = {"ok": False, "message": str(e)}

                if st.session_state.crud_message:
                    if st.session_state.crud_message["ok"]:
                        st.success(st.session_state.crud_message["message"])
                    else:
                        st.error(st.session_state.crud_message["message"])
            else:
                st.info(t("empty_table_hint"))

            st.markdown("---")
            st.subheader(t("sql_generation_title"))
            st.session_state.sql_description = st.text_area(
                t("sql_description_label"),
                value=st.session_state.sql_description,
                height=120,
            )
            if st.button(t("generate_sql"), use_container_width=True):
                if not st.session_state.sql_description.strip():
                    st.session_state.sql_feedback = {"type": "warning", "message": t("sql_description_required")}
                elif not st.session_state.db_analysis:
                    st.session_state.sql_feedback = {"type": "warning", "message": t("sql_analysis_required")}
                else:
                    with st.spinner("AI 正在為您分析資料庫結構並生成 SQL 查詢..."):
                        prompt = build_sql_generation_prompt(
                            st.session_state.db_type,
                            st.session_state.db_analysis,
                            st.session_state.sql_description,
                        )
                        try:
                            llm = LLMFactory.get_llm(
                                st.session_state.provider,
                                model_name=st.session_state.model,
                                temperature=st.session_state.temperature,
                            )
                            messages = [HumanMessage(content=prompt)]
                            response = llm.invoke(messages)
                            st.session_state.generated_sql = response.content.strip()
                            st.session_state.sql_feedback = {"type": "success", "message": "✅ 已生成 SQL 查詢建議。"}
                        except Exception as e:
                            st.session_state.generated_sql = ""
                            st.session_state.sql_feedback = {"type": "error", "message": t("sql_generation_error").format(error=e)}

            if st.session_state.sql_feedback:
                feedback = st.session_state.sql_feedback
                if feedback["type"] == "success":
                    st.success(feedback["message"])
                elif feedback["type"] == "warning":
                    st.warning(feedback["message"])
                else:
                    st.error(feedback["message"])

            if st.session_state.generated_sql:
                st.markdown(f"**{t('suggested_sql')}**")
                st.code(st.session_state.generated_sql, language="sql")
        else:
            st.markdown("---")
            st.info(t("unsupported_sql"))
