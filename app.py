#!/usr/bin/env python3
"""
LangChain Streamlit Web UI 應用
提供漂亮的網頁介面來選擇模型、調整參數並與 AI 進行對話
"""

try:
    import streamlit as st
    from llm_factory import LLMFactory, ModelProvider
    from langchain_core.messages import HumanMessage
    from db_utils import DBType, test_db_connection, build_sql_generation_prompt, execute_sql_query, get_table_preview, get_table_columns, insert_row, update_row, delete_row
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None

if STREAMLIT_AVAILABLE:
    st.set_page_config(
        page_title="🤖 LangChain 多模型應用",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stContainer {
            max-width: 1000px;
            margin: 0 auto;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    def st(*args, **kwargs):
        pass


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "provider" not in st.session_state:
        st.session_state.provider = ModelProvider.OLLAMA
    if "model" not in st.session_state:
        st.session_state.model = "llama3"
    if "temperature" not in st.session_state:
        st.session_state.temperature = LLMFactory.resolve_temperature()
    if "db_type" not in st.session_state:
        st.session_state.db_type = DBType.SQLITE
    if "db_config" not in st.session_state:
        st.session_state.db_config = {
            "filepath": "sample.db",
            "host": "localhost",
            "port": "3306",
            "user": "root",
            "password": "",
            "database": "",
            "uri": "mongodb://localhost:27017",
            "db": "0",
            "charset": "utf8mb4",
        }
    if "db_test_result" not in st.session_state:
        st.session_state.db_test_result = None
    if "db_analysis" not in st.session_state:
        st.session_state.db_analysis = {}
    if "sql_description" not in st.session_state:
        st.session_state.sql_description = ""
    if "generated_sql" not in st.session_state:
        st.session_state.generated_sql = ""
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    if "query_sql" not in st.session_state:
        st.session_state.query_sql = ""
    if "query_result" not in st.session_state:
        st.session_state.query_result = None
    if "selected_table" not in st.session_state:
        st.session_state.selected_table = ""
    if "crud_mode" not in st.session_state:
        st.session_state.crud_mode = "insert"
    if "crud_values" not in st.session_state:
        st.session_state.crud_values = {}
    if "crud_where" not in st.session_state:
        st.session_state.crud_where = ""
    if "crud_where_values" not in st.session_state:
        st.session_state.crud_where_values = ""
    if "crud_message" not in st.session_state:
        st.session_state.crud_message = None


def render_sidebar():
    st.header("⚙️ 應用設定")

    provider_options = {
        "Ollama (本地)": ModelProvider.OLLAMA,
        "OpenAI (雲端)": ModelProvider.OPENAI,
        "Google Gemini (雲端)": ModelProvider.GOOGLE,
    }
    selected_provider_name = st.selectbox(
        "選擇 AI 模型提供者",
        options=list(provider_options.keys()),
        index=list(provider_options.values()).index(st.session_state.provider),
    )
    st.session_state.provider = provider_options[selected_provider_name]

    available_models = LLMFactory.get_available_models(st.session_state.provider)
    if st.session_state.model not in available_models:
        st.session_state.model = available_models[0]

    st.session_state.temperature = st.slider(
        "溫度 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=float(st.session_state.temperature),
        step=0.1,
        help="可直接調整本次對話的創意度，預設會套用 .env 的 TEMPERATURE。",
    )

    st.markdown("---")
    st.subheader("📋 目前設定")
    st.info(f"""
    **提供者**: {st.session_state.provider.value.upper()}  
    **模型**: 由 .env 的 _MODEL 設定自動讀取  
    **溫度**: {st.session_state.temperature}
    """)

    st.markdown("---")
    st.subheader("🗄️ 資料庫設定")
    st.write(f"**資料庫類型**: {st.session_state.db_type.name}")
    if st.session_state.db_test_result is not None:
        status = "成功" if st.session_state.db_test_result.get("ok") else "失敗"
        st.write(f"**測試連線**: {status}")
        st.write(f"**訊息**: {st.session_state.db_test_result.get('message')}")

    if st.button("🗑️ 清除對話歷史", use_container_width=True):
        st.session_state.messages = []
        st.session_state.user_input = ""
        st.session_state.generated_sql = ""
        st.rerun()


def render_chat_tab():
    st.subheader("💬 AI 對話")

    if st.session_state.messages:
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message["content"])
    else:
        st.info(
            "👋 歡迎使用 LangChain 多模型應用！\n\n"
            "請在下方輸入您的提示詞開始與 AI 互動。"
        )

    st.markdown("---")
    st.subheader("📝 輸入提示詞")

    col1, col2 = st.columns([9, 1])
    with col1:
        st.session_state.user_input = st.text_input(
            "您的提示詞",
            placeholder="請輸入您想詢問 AI 的問題或任務...",
            label_visibility="collapsed",
            value=st.session_state.user_input,
            key="user_input_input",
        )
    with col2:
        submit_button = st.button("📤 送出", use_container_width=True)

    if submit_button and st.session_state.user_input:
        st.session_state.messages.append({
            "role": "user",
            "content": st.session_state.user_input,
        })
        with st.spinner(f"⏳ {st.session_state.provider.value.upper()} 正在處理您的提示詞..."):
            try:
                llm = LLMFactory.get_llm(
                    st.session_state.provider,
                    temperature=st.session_state.temperature,
                )
                messages = [HumanMessage(content=st.session_state.user_input)]
                response = llm.invoke(messages)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.content,
                })
                st.session_state.user_input = ""
                st.rerun()
            except Exception as e:
                st.error(f"❌ 發生錯誤: {str(e)}")
                st.warning("💡 請檢查:")
                st.markdown("""
                - 所選模型提供者的連線設定
                - API 金鑰是否正確設定在 .env 檔案
                - 網路連線是否正常
                - 若使用 Ollama，請確保 Ollama 服務已啟動
                """)

    st.markdown("---")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("### 📚 支援的提供者")
        st.markdown("""
        - **Ollama** - 本地 LLM
        - **OpenAI** - ChatGPT 系列
        - **Google** - Gemini 系列
        """)
    with cols[1]:
        st.markdown("### 🔧 快速提示")
        st.markdown("""
        - 溫度越低越穩定
        - 溫度越高越有創意
        - 清除歷史開始新對話
        """)
    with cols[2]:
        st.markdown("### ⚙️ 設定")
        st.markdown("""
        - 編輯 `.env` 檔案設定 API 金鑰
        - 在側邊欄選擇所需模型
        - 調整溫度參數
        - 使用資料庫頁面管理連線
        """)


def render_db_tab():
    st.subheader("🗄️ 資料庫管理")

    db_options = [
        DBType.SQLITE,
        DBType.MYSQL,
        DBType.POSTGRES,
        DBType.MARIADB,
        DBType.REDIS,
        DBType.MONGODB,
    ]
    st.session_state.db_type = st.selectbox(
        "選擇資料庫類型",
        options=db_options,
        format_func=lambda value: value.name,
        index=db_options.index(st.session_state.db_type),
    )

    if st.session_state.db_type == DBType.SQLITE:
        st.session_state.db_config["filepath"] = st.text_input(
            "SQLite 檔案路徑",
            value=st.session_state.db_config.get("filepath", "sample.db"),
            placeholder="例如: ./data/example.db",
        )
    elif st.session_state.db_type in {DBType.MYSQL, DBType.MARIADB, DBType.POSTGRES}:
        st.session_state.db_config["host"] = st.text_input(
            "主機 (host)",
            value=st.session_state.db_config.get("host", "localhost"),
        )
        st.session_state.db_config["port"] = st.text_input(
            "連接埠 (port)",
            value=st.session_state.db_config.get("port", "5432" if st.session_state.db_type == DBType.POSTGRES else "3306"),
        )
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.db_config["user"] = st.text_input(
                "使用者",
                value=st.session_state.db_config.get("user", "root"),
            )
        with col2:
            st.session_state.db_config["password"] = st.text_input(
                "密碼",
                value=st.session_state.db_config.get("password", ""),
                type="password",
            )

        st.session_state.db_config["database"] = st.text_input(
            "資料庫名稱",
            value=st.session_state.db_config.get("database", ""),
        )
        if st.session_state.db_type in {DBType.MYSQL, DBType.MARIADB}:
            st.session_state.db_config["charset"] = st.text_input(
                "字元編碼 (charset)",
                value=st.session_state.db_config.get("charset", "utf8mb4"),
            )
    elif st.session_state.db_type == DBType.REDIS:
        st.session_state.db_config["host"] = st.text_input(
            "主機 (host)",
            value=st.session_state.db_config.get("host", "localhost"),
        )
        st.session_state.db_config["port"] = st.text_input(
            "連接埠 (port)",
            value=st.session_state.db_config.get("port", "6379"),
        )
        st.session_state.db_config["password"] = st.text_input(
            "密碼 (可選)",
            value=st.session_state.db_config.get("password", ""),
            type="password",
        )
        st.session_state.db_config["db"] = st.text_input(
            "Redis 資料庫索引",
            value=st.session_state.db_config.get("db", "0"),
        )
    elif st.session_state.db_type == DBType.MONGODB:
        st.session_state.db_config["uri"] = st.text_input(
            "MongoDB 連線 URI",
            value=st.session_state.db_config.get("uri", "mongodb://localhost:27017"),
            placeholder="mongodb://user:pass@localhost:27017/dbname",
        )
        st.session_state.db_config["database"] = st.text_input(
            "預設資料庫名稱 (可選)",
            value=st.session_state.db_config.get("database", ""),
        )

    if st.button("🔍 測試資料庫連線", use_container_width=True):
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
        st.subheader("📊 資料庫分析結果")
        st.write(f"**資料庫類型**: {st.session_state.db_analysis.get('db_type')}  |  **版本**: {st.session_state.db_analysis.get('version')}")
        st.write(f"**連線設定**: `{st.session_state.db_analysis.get('config')}`")

        if st.session_state.db_type in {DBType.SQLITE, DBType.MYSQL, DBType.POSTGRES, DBType.MARIADB}:
            table_summary = []
            for table in st.session_state.db_analysis.get("tables", []):
                columns = table.get("columns") or []
                table_summary.append({
                    "資料表": table.get("name"),
                    "用途": table.get("purpose") or "未分類",
                    "列數": table.get("row_count"),
                    "欄位": ", ".join([f"{c.get('name')}({c.get('type')})" for c in columns]),
                    "關聯數": len(table.get("relationships") or []),
                })
            st.dataframe(table_summary, use_container_width=True)

            for table in st.session_state.db_analysis.get("tables", []):
                with st.expander(f"📄 {table.get('name')}"):
                    cols = table.get("columns") or []
                    st.write(f"**用途**: {table.get('purpose') or '未分類'}")
                    st.write(f"**列數**: {table.get('row_count')}")
                    if cols:
                        st.write("**欄位**: " + ", ".join([f"{c.get('name')}({c.get('type')})" for c in cols]))
                    relationships = table.get("relationships") or []
                    if relationships:
                        st.write("**關聯**")
                        for rel in relationships:
                            st.write(
                                f"- {rel.get('from_column')} → {rel.get('to_table')}.{rel.get('to_column')}"
                            )
                    else:
                        st.info("此資料表目前沒有檢測到外鍵關聯。")
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
        st.subheader("🧰 基本資料庫操作")

        tables = [table.get("name") for table in st.session_state.db_analysis.get("tables", []) if table.get("name")]
        if tables:
            if st.session_state.selected_table not in tables:
                st.session_state.selected_table = tables[0]
            table_col, preview_col = st.columns([4, 1])
            with table_col:
                st.session_state.selected_table = st.selectbox(
                    "選擇資料表",
                    options=tables,
                    index=tables.index(st.session_state.selected_table),
                )
            with preview_col:
                if st.button("🔎 預覽", use_container_width=True):
                    try:
                        st.session_state.query_result = get_table_preview(
                            st.session_state.db_type,
                            st.session_state.db_config,
                            st.session_state.selected_table,
                        )
                    except Exception as e:
                        st.session_state.query_result = {"ok": False, "error": str(e)}

        st.session_state.query_sql = st.text_area(
            "執行 SQL 查詢",
            value=st.session_state.query_sql,
            height=140,
            placeholder="例如: SELECT * FROM users LIMIT 10;",
        )
        if st.button("▶️ 執行 SQL", use_container_width=True):
            if not st.session_state.query_sql.strip():
                st.warning("請先輸入 SQL 查詢。")
            else:
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
                    st.caption(f"查詢結果：{result['row_count']} 筆")
                    st.dataframe(records)
                else:
                    st.success(f"✅ SQL 已執行，影響列數：{result.get('row_count', 0)}")
            else:
                st.error(f"❌ 執行 SQL 時發生錯誤: {st.session_state.query_result.get('error')}")

        st.markdown("---")
        st.subheader("📝 資料列 CRUD")
        st.session_state.crud_mode = st.selectbox(
            "操作類型",
            options=["insert", "update", "delete"],
            format_func=lambda value: {"insert": "新增", "update": "更新", "delete": "刪除"}[value],
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
                if st.button("➕ 新增資料列", use_container_width=True):
                    try:
                        payload = {k: v for k, v in st.session_state.crud_values.items() if v != ""}
                        result = insert_row(st.session_state.db_type, st.session_state.db_config, st.session_state.selected_table, payload)
                        st.session_state.crud_message = {"ok": True, "message": f"新增成功，影響 {result['row_count']} 列"}
                    except Exception as e:
                        st.session_state.crud_message = {"ok": False, "message": str(e)}
            elif st.session_state.crud_mode == "update":
                st.session_state.crud_where = st.text_input("更新條件（例如: id = 1）", value=st.session_state.crud_where)
                for column in table_columns:
                    st.session_state.crud_values[column] = st.text_input(
                        f"{column}",
                        value=st.session_state.crud_values.get(column, ""),
                        key=f"update_{column}",
                    )
                st.session_state.crud_where_values = st.text_input("條件參數（以逗號分隔）", value=st.session_state.crud_where_values)
                if st.button("✏️ 更新資料列", use_container_width=True):
                    try:
                        values = {k: v for k, v in st.session_state.crud_values.items() if v != ""}
                        where_values = [item.strip() for item in st.session_state.crud_where_values.split(",") if item.strip()]
                        result = update_row(st.session_state.db_type, st.session_state.db_config, st.session_state.selected_table, values, st.session_state.crud_where, where_values)
                        st.session_state.crud_message = {"ok": True, "message": f"更新成功，影響 {result['row_count']} 列"}
                    except Exception as e:
                        st.session_state.crud_message = {"ok": False, "message": str(e)}
            else:
                st.session_state.crud_where = st.text_input("刪除條件（例如: id = 1）", value=st.session_state.crud_where)
                st.session_state.crud_where_values = st.text_input("條件參數（以逗號分隔）", value=st.session_state.crud_where_values)
                if st.button("🗑️ 刪除資料列", use_container_width=True):
                    try:
                        where_values = [item.strip() for item in st.session_state.crud_where_values.split(",") if item.strip()]
                        result = delete_row(st.session_state.db_type, st.session_state.db_config, st.session_state.selected_table, st.session_state.crud_where, where_values)
                        st.session_state.crud_message = {"ok": True, "message": f"刪除成功，影響 {result['row_count']} 列"}
                    except Exception as e:
                        st.session_state.crud_message = {"ok": False, "message": str(e)}

            if st.session_state.crud_message:
                if st.session_state.crud_message["ok"]:
                    st.success(st.session_state.crud_message["message"])
                else:
                    st.error(st.session_state.crud_message["message"])
        else:
            st.info("請先測試連線並選擇資料表。")

        st.markdown("---")
        st.subheader("🧠 自然語言轉 SQL 查詢")
        st.session_state.sql_description = st.text_area(
            "請輸入要查詢資料庫的敘述，例如: 查詢最新 10 筆使用者資料",
            value=st.session_state.sql_description,
            height=120,
        )
        if st.button("🧾 生成 SQL 語法", use_container_width=True):
            if not st.session_state.sql_description.strip():
                st.warning("請先輸入查詢描述。")
            elif not st.session_state.db_analysis:
                st.warning("請先測試連線並取得資料庫分析結果。")
            else:
                prompt = build_sql_generation_prompt(
                    st.session_state.db_type,
                    st.session_state.db_analysis,
                    st.session_state.sql_description,
                )
                try:
                    llm = LLMFactory.get_llm(
                        st.session_state.provider,
                        temperature=st.session_state.temperature,
                    )
                    messages = [HumanMessage(content=prompt)]
                    response = llm.invoke(messages)
                    st.session_state.generated_sql = response.content.strip()
                except Exception as e:
                    st.error(f"❌ 生成 SQL 時發生錯誤: {e}")

        if st.session_state.generated_sql:
            st.markdown("**建議 SQL**")
            st.code(st.session_state.generated_sql, language="sql")
    else:
        st.markdown("---")
        st.info("目前資料庫類型不支援 SQL 生成，僅支援 SQLite / MySQL / PostgreSQL / MariaDB。")


def main():
    if not STREAMLIT_AVAILABLE:
        print("❌ Streamlit 未安裝或無法導入")
        print("\n若要使用 Web UI，請安裝 Streamlit:")
        print("  pip install streamlit")
        print("\n或者使用 CLI 版本:")
        print("  python cli.py")
        return

    initialize_session_state()
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown("# 🤖")
    with col2:
        st.markdown("# LangChain 多模型交互式應用")
    st.markdown("---")

    with st.sidebar:
        render_sidebar()

    tab_chat, tab_db = st.tabs(["💬 AI 對話", "🗄️ 資料庫管理"])
    with tab_chat:
        render_chat_tab()
    with tab_db:
        render_db_tab()

if __name__ == "__main__":
    main()
