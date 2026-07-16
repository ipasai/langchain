#!/usr/bin/env python3
"""
LangChain Streamlit Web UI 應用
提供漂亮的網頁介面來選擇模型、調整參數並與 AI 進行對話
"""

import csv
import io
import json
import os
import random
from datetime import datetime

import pandas as pd

try:
    import streamlit as st
    from llm_factory import LLMFactory, ModelProvider
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from db_utils import (
        DBType,
        build_sql_generation_prompt,
        clear_chat_messages,
        delete_row,
        delete_translation_entry,
        ensure_local_memory_database,
        execute_sql_query,
        get_learning_stats,
        get_table_columns,
        get_table_preview,
        insert_row,
        list_english_practice_items,
        list_study_sessions,
        load_daily_review_state,
        load_recent_chat_messages,
        load_setting,
        record_english_practice,
        record_study_session,
        save_chat_message,
        save_daily_review_state,
        save_setting,
        save_translation_entry,
        search_translation_entries,
        should_show_daily_review_reminder,
        test_db_connection,
        update_row,
    )
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
        /* 讓下拉選單與選項支援換行 */
        div[data-baseweb="select"], ul[role="listbox"] li {
            white-space: pre-line !important;
        }
        ul[role="listbox"] li {
            line-height: 1.3 !important;
            padding-top: 6px !important;
            padding-bottom: 6px !important;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    def st(*args, **kwargs):
        pass


DEFAULT_LOCALE = "zh-tw"
LANGUAGE_OPTIONS = {"zh-tw": "繁體中文", "en": "English"}
TRANSLATIONS = {
    "page_title": {"zh-tw": "🤖 LangChain 多模型應用", "en": "🤖 LangChain Multi-Model Application"},
    "app_title": {"zh-tw": "LangChain 多模型交互式應用", "en": "LangChain Multi-Model Interactive Application"},
    "language_label": {"zh-tw": "語言", "en": "Language"},
    "language_zh_tw": {"zh-tw": "繁體中文", "en": "Traditional Chinese"},
    "language_en": {"zh-tw": "English", "en": "English"},
    "app_settings": {"zh-tw": "應用設定", "en": "Application Settings"},
    "provider_label": {"zh-tw": "選擇 AI 模型提供者", "en": "Select AI Model Provider"},
    "provider_ollama": {"zh-tw": "Ollama (本地)", "en": "Ollama (Local)"},
    "provider_openai": {"zh-tw": "OpenAI (雲端)", "en": "OpenAI (Cloud)"},
    "provider_google": {"zh-tw": "Google Gemini (雲端)", "en": "Google Gemini (Cloud)"},
    "temperature_label": {"zh-tw": "溫度 (Temperature)", "en": "Temperature"},
    "temperature_help": {"zh-tw": "可直接調整本次對話的創意度，預設會套用 .env 的 TEMPERATURE。", "en": "Adjust the creativity of this chat directly; it defaults to the TEMPERATURE value in .env."},
    "current_settings": {"zh-tw": "目前設定", "en": "Current Settings"},
    "provider": {"zh-tw": "提供者", "en": "Provider"},
    "model_from_env": {"zh-tw": "模型: 由 .env 的 _MODEL 設定自動讀取", "en": "Model: automatically loaded from the _MODEL setting in .env"},
    "temperature_value": {"zh-tw": "溫度: {value}", "en": "Temperature: {value}"},
    "database_settings": {"zh-tw": "資料庫設定", "en": "Database Settings"},
    "version_label": {"zh-tw": "版本", "en": "Version"},
    "uncategorized_label": {"zh-tw": "未分類", "en": "Uncategorized"},
    "english_learning_tab": {"zh-tw": "📘 英文學習", "en": "📘 English Practice"},
    "english_learning_title": {"zh-tw": "📘 英文學習", "en": "📘 English Practice"},
    "english_learning_desc": {"zh-tw": "把常用英文與中文意思記錄到本機 SQLite 資料庫，方便之後反覆練習。", "en": "Save common English phrases and their Chinese meaning in the local SQLite database for repeated practice."},
    "english_input_label": {"zh-tw": "英文句子", "en": "English phrase"},
    "translation_input_label": {"zh-tw": "中文意思", "en": "Chinese meaning"},
    "save_practice": {"zh-tw": "💾 儲存單字", "en": "💾 Save phrase"},
    "practice_saved": {"zh-tw": "✅ 已加入英文學習記錄。", "en": "✅ Added to your practice list."},
    "practice_empty": {"zh-tw": "目前還沒有學習紀錄。", "en": "No practice items yet."},
    "database_type": {"zh-tw": "資料庫類型", "en": "Database Type"},
    "connection_status": {"zh-tw": "測試連線", "en": "Connection Test"},
    "connection_message": {"zh-tw": "訊息", "en": "Message"},
    "success": {"zh-tw": "成功", "en": "Success"},
    "failure": {"zh-tw": "失敗", "en": "Failure"},
    "connection_config": {"zh-tw": "連線設定", "en": "Connection settings"},
    "clear_history": {"zh-tw": "清除對話歷史", "en": "Clear chat history"},
    "chat_tab_title": {"zh-tw": "💬 AI 對話", "en": "💬 AI Chat"},
    "chat_welcome": {"zh-tw": "👋 歡迎使用 LangChain 多模型應用！\n\n請在下方輸入您的提示詞開始與 AI 互動。", "en": "👋 Welcome to the LangChain multi-model app!\n\nType your prompt below to start chatting."},
    "prompt_input_title": {"zh-tw": "📝 輸入提示詞", "en": "📝 Enter a prompt"},
    "prompt_placeholder": {"zh-tw": "請輸入您想詢問 AI 的問題或任務...", "en": "Describe the question or task you want the AI to handle..."},
    "prompt_label": {"zh-tw": "您的提示詞", "en": "Your prompt"},
    "submit": {"zh-tw": "送出", "en": "Send"},
    "processing_message": {"zh-tw": "⏳ {provider} 正在處理您的提示詞...", "en": "⏳ {provider} is processing your prompt..."},
    "error_title": {"zh-tw": "❌ 發生錯誤", "en": "❌ An error occurred"},
    "check_list": {"zh-tw": "💡 請檢查:", "en": "💡 Please check:"},
    "support_providers": {"zh-tw": "📚 支援的提供者", "en": "📚 Supported providers"},
    "provider_list": {"zh-tw": "- **Ollama** - 本地 LLM\n- **OpenAI** - ChatGPT 系列\n- **Google** - Gemini 系列", "en": "- **Ollama** - Local LLM\n- **OpenAI** - ChatGPT series\n- **Google** - Gemini series"},
    "quick_tips": {"zh-tw": "🔧 快速提示", "en": "🔧 Quick tips"},
    "tips_list": {"zh-tw": "- 溫度越低越穩定\n- 溫度越高越有創意\n- 清除歷史開始新對話", "en": "- Lower temperature is more stable\n- Higher temperature is more creative\n- Clear history and start a new chat"},
    "settings_hint": {"zh-tw": "⚙️ 設定", "en": "⚙️ Settings"},
    "settings_list": {"zh-tw": "- 編輯 `.env` 檔案設定 API 金鑰\n- 在側邊欄選擇所需模型\n- 調整溫度參數\n- 使用資料庫頁面管理連線", "en": "- Edit the `.env` file to set API keys\n- Choose a model in the sidebar\n- Adjust the temperature\n- Use the database page to manage connections"},
    "db_management": {"zh-tw": "🗄️ 資料庫管理", "en": "🗄️ Database Management"},
    "db_type_label": {"zh-tw": "選擇資料庫類型", "en": "Select database type"},
    "sqlite_path": {"zh-tw": "SQLite 檔案路徑", "en": "SQLite file path"},
    "host_label": {"zh-tw": "主機 (host)", "en": "Host"},
    "port_label": {"zh-tw": "連接埠 (port)", "en": "Port"},
    "username_label": {"zh-tw": "使用者", "en": "User"},
    "password_label": {"zh-tw": "密碼", "en": "Password"},
    "database_name_label": {"zh-tw": "資料庫名稱", "en": "Database name"},
    "charset_label": {"zh-tw": "字元編碼 (charset)", "en": "Charset"},
    "redis_db_label": {"zh-tw": "Redis 資料庫索引", "en": "Redis database index"},
    "mongodb_uri": {"zh-tw": "MongoDB 連線 URI", "en": "MongoDB connection URI"},
    "mongodb_database_label": {"zh-tw": "預設資料庫名稱 (可選)", "en": "Default database name (optional)"},
    "test_connection": {"zh-tw": "🔍 測試資料庫連線", "en": "🔍 Test database connection"},
    "analysis_results": {"zh-tw": "📊 資料庫分析結果", "en": "📊 Database analysis results"},
    "basic_operations": {"zh-tw": "🧰 基本資料庫操作", "en": "🧰 Basic database operations"},
    "table_label": {"zh-tw": "資料表", "en": "Table"},
    "purpose_label": {"zh-tw": "用途", "en": "Purpose"},
    "row_count_label": {"zh-tw": "列數", "en": "Row count"},
    "columns_label": {"zh-tw": "欄位", "en": "Columns"},
    "relationship_count_label": {"zh-tw": "關聯數", "en": "Relationship count"},
    "relationships_label": {"zh-tw": "關聯", "en": "Relationships"},
    "no_relationships_hint": {"zh-tw": "此資料表目前沒有檢測到外鍵關聯。", "en": "No foreign-key relationships were detected for this table."},
    "query_result_label": {"zh-tw": "查詢結果", "en": "Query result"},
    "query_result_count": {"zh-tw": "{count} 筆", "en": "{count} rows"},
    "sql_execution_success": {"zh-tw": "✅ SQL 已執行，影響列數：{count}", "en": "✅ SQL executed successfully. Affected rows: {count}"},
    "sql_execution_error": {"zh-tw": "❌ 執行 SQL 時發生錯誤: {error}", "en": "❌ An error occurred while executing SQL: {error}"},
    "sql_query_required": {"zh-tw": "請先輸入 SQL 查詢。", "en": "Please enter a SQL query first."},
    "sql_description_required": {"zh-tw": "請先輸入查詢描述。", "en": "Please enter a query description first."},
    "sql_analysis_required": {"zh-tw": "請先測試連線並取得資料庫分析結果。", "en": "Please test the connection and obtain the database analysis first."},
    "sql_generation_error": {"zh-tw": "❌ 生成 SQL 時發生錯誤: {error}", "en": "❌ An error occurred while generating SQL: {error}"},
    "sql_generation_title": {"zh-tw": "🧠 自然語言轉 SQL 查詢", "en": "🧠 Natural language to SQL"},
    "crud_success_insert": {"zh-tw": "新增成功，影響 {count} 列", "en": "Inserted successfully. Affected rows: {count}"},
    "crud_success_update": {"zh-tw": "更新成功，影響 {count} 列", "en": "Updated successfully. Affected rows: {count}"},
    "crud_success_delete": {"zh-tw": "刪除成功，影響 {count} 列", "en": "Deleted successfully. Affected rows: {count}"},
    "update_condition_label": {"zh-tw": "更新條件（例如: id = 1）", "en": "Update condition (for example: id = 1)"},
    "where_values_label": {"zh-tw": "條件參數（以逗號分隔）", "en": "Condition values (comma separated)"},
    "delete_condition_label": {"zh-tw": "刪除條件（例如: id = 1）", "en": "Delete condition (for example: id = 1)"},
    "check_connection_message": {"zh-tw": "請先測試連線並選擇資料表。", "en": "Please test the connection and select a table first."},
    "select_table": {"zh-tw": "選擇資料表", "en": "Select table"},
    "preview": {"zh-tw": "預覽", "en": "Preview"},
    "run_sql": {"zh-tw": "▶️ 執行 SQL", "en": "▶️ Run SQL"},
    "sql_query_label": {"zh-tw": "執行 SQL 查詢", "en": "Run SQL query"},
    "sql_placeholder": {"zh-tw": "例如: SELECT * FROM users LIMIT 10;", "en": "Example: SELECT * FROM users LIMIT 10;"},
    "crud_title": {"zh-tw": "📝 資料列 CRUD", "en": "📝 Row CRUD"},
    "crud_mode": {"zh-tw": "操作類型", "en": "Operation type"},
    "crud_insert": {"zh-tw": "新增", "en": "Insert"},
    "crud_update": {"zh-tw": "更新", "en": "Update"},
    "crud_delete": {"zh-tw": "刪除", "en": "Delete"},
    "crud_insert_button": {"zh-tw": "➕ 新增資料列", "en": "➕ Insert row"},
    "crud_update_button": {"zh-tw": "✏️ 更新資料列", "en": "✏️ Update row"},
    "crud_delete_button": {"zh-tw": "🗑️ 刪除資料列", "en": "🗑️ Delete row"},
    "generate_sql": {"zh-tw": "🧾 生成 SQL 語法", "en": "🧾 Generate SQL"},
    "sql_description_label": {"zh-tw": "請輸入要查詢資料庫的敘述，例如: 查詢最新 10 筆使用者資料", "en": "Describe the database query you want, for example: show the latest 10 users"},
    "sql_description_placeholder": {"zh-tw": "請輸入要查詢資料庫的敘述，例如: 查詢最新 10 筆使用者資料", "en": "Describe the query you want to run..."},
    "sqlite_placeholder": {"zh-tw": "例如: ./data/example.db", "en": "Example: ./data/example.db"},
    "mongodb_placeholder": {"zh-tw": "mongodb://user:pass@localhost:27017/dbname", "en": "mongodb://user:pass@localhost:27017/dbname"},
    "suggested_sql": {"zh-tw": "建議 SQL", "en": "Suggested SQL"},
    "unsupported_sql": {"zh-tw": "目前資料庫類型不支援 SQL 生成，僅支援 SQLite / MySQL / PostgreSQL / MariaDB。", "en": "The current database type does not support SQL generation; only SQLite / MySQL / PostgreSQL / MariaDB are supported."},
    "empty_table_hint": {"zh-tw": "請先測試連線並選擇資料表。", "en": "Please test the connection and choose a table first."},
}


def get_current_locale():
    if STREAMLIT_AVAILABLE and hasattr(st, "session_state"):
        return st.session_state.get("locale", DEFAULT_LOCALE)
    return DEFAULT_LOCALE


def t(key, locale=None):
    current_locale = locale or get_current_locale()
    translations = TRANSLATIONS.get(key, {})
    if current_locale in translations:
        return translations[current_locale]
    return translations.get(DEFAULT_LOCALE, key)


def _load_saved_categories(db_path):
    raw_value = load_setting("english_categories", "[]", db_path=db_path) or "[]"
    try:
        categories = json.loads(raw_value)
    except Exception:
        categories = []
    return [item for item in categories if isinstance(item, str) and item.strip()] or ["未分類"]


def _save_saved_categories(categories, db_path):
    save_setting("english_categories", json.dumps(categories, ensure_ascii=False), db_path=db_path)


def initialize_session_state():
    base_dir = os.path.dirname(__file__)
    st.session_state.db_path = os.path.join(base_dir, "data", "app_memory.db")
    ensure_local_memory_database(st.session_state.db_path)

    if "messages" not in st.session_state:
        st.session_state.messages = load_recent_chat_messages(limit=50, db_path=st.session_state.db_path)
    if "locale" not in st.session_state:
        st.session_state.locale = DEFAULT_LOCALE
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
    if "table_page_size" not in st.session_state:
        st.session_state.table_page_size = 10
    if "table_page" not in st.session_state:
        st.session_state.table_page = 0
    if "table_editing" not in st.session_state:
        st.session_state.table_editing = None
    if "table_edit_row" not in st.session_state:
        st.session_state.table_edit_row = None
    if "flashcard_display_mode" not in st.session_state:
        st.session_state.flashcard_display_mode = "english"
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "未分類"
    if "new_category_name" not in st.session_state:
        st.session_state.new_category_name = ""
    if "saved_categories" not in st.session_state:
        st.session_state.saved_categories = _load_saved_categories(st.session_state.db_path)
    if "sql_feedback" not in st.session_state:
        st.session_state.sql_feedback = None
    if "last_search_query" not in st.session_state:
        st.session_state.last_search_query = ""
    if "favorite_cards" not in st.session_state:
        st.session_state.favorite_cards = []
    if "db_source_signature" not in st.session_state:
        st.session_state.db_source_signature = None


def render_sidebar():
    st.header(f"⚙️ {t('app_settings')}")

    provider_options = {
        t("provider_ollama"): ModelProvider.OLLAMA,
        t("provider_openai"): ModelProvider.OPENAI,
        t("provider_google"): ModelProvider.GOOGLE,
    }
    selected_provider_name = st.selectbox(
        t("provider_label"),
        options=list(provider_options.keys()),
        index=list(provider_options.values()).index(st.session_state.provider),
    )
    st.session_state.provider = provider_options[selected_provider_name]

    # 1. 取得當前供應商可用的模型列表
    available_models = LLMFactory.get_available_models(st.session_state.provider)

    # 2. 【核心安全檢查】如果當前 model 不在可用列表中，主動將其修正為列表的第一個預設值
    if st.session_state.model not in available_models:
        # 確保列表不為空，避免 pop() 或 index 0 報錯
        st.session_state.model = available_models[0] if available_models else ""

    # 3. 渲染選單（此時 index 必定能安全對應）
    selected_model = st.selectbox(
        "選擇 AI 模型",
        options=available_models,
        index=available_models.index(st.session_state.model) if available_models else 0,
        format_func=LLMFactory.get_formatted_model_name
    )

    # 4. 同步更新狀態
    st.session_state.model = selected_model

    print("debug", selected_model)
    print("debug", st.session_state.model)
    print("debug", available_models)
    print("debug", available_models.index(st.session_state.model))
    print("debug", LLMFactory.get_formatted_model_name)

    st.session_state.temperature = st.slider(
        t("temperature_label"),
        min_value=0.0,
        max_value=1.0,
        value=float(st.session_state.temperature),
        step=0.1,
        help=t("temperature_help"),
    )

    st.markdown("---")
    st.subheader("👤 角色設定 (Persona)")
    persona_options = {
        "通用助理 (General Assistant)": "你是一個親切且專業的 AI 助理，請用繁體中文回答問題。",
        "程式專家 (Coding Expert)": "你是一位精通軟體開發與系統架構的程式專家。請提供乾淨、高效且有詳細註解的程式碼，並使用繁體中文解釋。",
        "英文導師 (English Tutor)": "You are an encouraging and professional English tutor. Help the user learn English by correcting grammar, explaining vocabulary, and providing natural example sentences. Respond in Traditional Chinese with English explanations.",
        "自訂角色 (Custom Prompt)": "custom"
    }
    
    if "selected_persona" not in st.session_state:
        st.session_state.selected_persona = list(persona_options.keys())[0]
        
    selected_persona = st.selectbox(
        "選擇 AI 角色",
        options=list(persona_options.keys()),
        index=list(persona_options.keys()).index(st.session_state.selected_persona)
    )
    st.session_state.selected_persona = selected_persona
    
    if selected_persona == "自訂角色 (Custom Prompt)":
        if "custom_system_prompt" not in st.session_state:
            st.session_state.custom_system_prompt = "你是一個 AI 助理。"
        st.session_state.system_prompt = st.text_area(
            "輸入自訂 System Prompt",
            value=st.session_state.custom_system_prompt
        )
        st.session_state.custom_system_prompt = st.session_state.system_prompt
    else:
        st.session_state.system_prompt = persona_options[selected_persona]

    st.markdown("---")
    st.subheader(f"📋 {t('current_settings')}")
    st.info(f"""
    **{t('provider')}**: {st.session_state.provider.value.upper()}  
    **模型**: `{st.session_state.model}`  
    **建議用途**: {LLMFactory.get_model_recommendation(st.session_state.model)}  
    **{t('temperature_value').format(value=st.session_state.temperature)}**
    """)

    st.markdown("---")
    st.subheader(f"🗄️ {t('database_settings')}")
    st.write(f"**{t('database_type')}**: {st.session_state.db_type.name}")
    if st.session_state.db_test_result is not None:
        status = t("success") if st.session_state.db_test_result.get("ok") else t("failure")
        st.write(f"**{t('connection_status')}**: {status}")
        st.write(f"**{t('connection_message')}**: {st.session_state.db_test_result.get('message')}")

    if st.button(f"🗑️ {t('clear_history')}", width=True):
        st.session_state.messages = []
        st.session_state.user_input = ""
        st.session_state.generated_sql = ""
        clear_chat_messages(db_path=st.session_state.db_path)
        st.rerun()


def render_chat_tab():
    st.subheader(t("chat_tab_title"))

    if st.session_state.messages:
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message["content"])
    else:
        st.info(t("chat_welcome"))

    st.markdown("---")
    st.subheader(t("prompt_input_title"))

    col1, col2 = st.columns([9, 1])
    with col1:
        st.session_state.user_input = st.text_input(
            t("prompt_label"),
            placeholder=t("prompt_placeholder"),
            label_visibility="collapsed",
            value=st.session_state.user_input,
            key="user_input_input",
        )
    with col2:
        submit_button = st.button(t("submit"), width=True)

    if submit_button and st.session_state.user_input:
        user_message = st.session_state.user_input
        st.session_state.messages.append({
            "role": "user",
            "content": user_message,
        })
        save_chat_message("user", user_message, db_path=st.session_state.db_path)
        try:
            llm = LLMFactory.get_llm(
                st.session_state.provider,
                model_name=st.session_state.model,
                temperature=st.session_state.temperature,
            )
            
            api_messages = []
            if "system_prompt" in st.session_state and st.session_state.system_prompt:
                api_messages.append(SystemMessage(content=st.session_state.system_prompt))
            
            # 載入最後 10 筆歷史對話以提供脈絡記憶
            recent_history = st.session_state.messages[-10:] if len(st.session_state.messages) > 10 else st.session_state.messages
            for msg in recent_history:
                if msg["role"] == "user":
                    api_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    api_messages.append(AIMessage(content=msg["content"]))
                    
            with st.chat_message("assistant", avatar="🤖"):
                placeholder = st.empty()
                assistant_reply = ""
                for chunk in llm.stream(api_messages):
                    assistant_reply += chunk.content
                    placeholder.markdown(assistant_reply)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_reply,
            })
            save_chat_message("assistant", assistant_reply, db_path=st.session_state.db_path)
            st.session_state.user_input = ""
            st.rerun()
        except Exception as e:
            st.error(t("error_title") + f": {str(e)}")
            st.warning(t("check_list"))
            st.markdown(f"""
            - {t('provider_label')} 的連線設定
            - API 金鑰是否正確設定在 .env 檔案
            - 網路連線是否正常
            - 若使用 Ollama，請確保 Ollama 服務已啟動
            """)

    st.markdown("---")
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"### {t('support_providers')}")
        st.markdown(t("provider_list"))
    with cols[1]:
        st.markdown(f"### {t('quick_tips')}")
        st.markdown(t("tips_list"))
    with cols[2]:
        st.markdown(f"### {t('settings_hint')}")
        st.markdown(t("settings_list"))


def render_english_tab():
    st.subheader(t("english_learning_title"))
    st.caption(t("english_learning_desc"))

    with st.form("english_practice_form", clear_on_submit=True):
        english_phrase = st.text_input(t("english_input_label"), placeholder="Hello")
        translation_phrase = st.text_input(t("translation_input_label"), placeholder="你好")
        submitted = st.form_submit_button(t("save_practice"))
        if submitted and english_phrase.strip():
            record_english_practice(english_phrase.strip(), translation_phrase.strip(), db_path=st.session_state.db_path)
            st.success(t("practice_saved"))
            st.rerun()

    practice_items = list_english_practice_items(limit=10, db_path=st.session_state.db_path)
    if practice_items:
        for item in practice_items:
            st.markdown(f"- **{item['english']}** → {item['translation']}")
    else:
        st.info(t("practice_empty"))


def normalize_flashcard_state(practice_items, flashcard_index, flashcard_revealed):
    if not practice_items:
        return 0, False
    total_cards = len(practice_items)
    safe_index = max(0, min(int(flashcard_index), total_cards - 1))
    return safe_index, bool(flashcard_revealed)


def parse_llm_translation_response(response_text: str):
    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    translation = ""
    example = ""

    for line in lines:
        if line.lower().startswith("中文意思") or line.lower().startswith("意思"):
            translation = line.split("：", 1)[-1].strip() if "：" in line else line.split(":", 1)[-1].strip()
        elif line.lower().startswith("例句"):
            example = line.split("：", 1)[-1].strip() if "：" in line else line.split(":", 1)[-1].strip()

    if not translation and lines:
        translation = lines[0]
    if not example and lines and len(lines) > 1:
        example = lines[1]
    return translation, example


def parse_llm_example_sentences(response_text: str):
    examples = []
    for line in response_text.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.lower().startswith(("例句", "example", "例句1", "例句2", "例句3")):
            value = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
            if value:
                examples.append(value)
    return examples


def parse_llm_example_items(response_text: str, fallback_translation: str = ""):
    items = []
    for line in response_text.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.lower().startswith(("例句", "example", "例句1", "例句2", "例句3")):
            raw_value = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
            english = raw_value
            chinese = fallback_translation
            if "｜" in raw_value:
                parts = [part.strip() for part in raw_value.split("｜") if part.strip()]
                if parts:
                    english = parts[0]
                    chinese = parts[1] if len(parts) > 1 else fallback_translation
            elif "|" in raw_value:
                parts = [part.strip() for part in raw_value.split("|") if part.strip()]
                if parts:
                    english = parts[0]
                    chinese = parts[1] if len(parts) > 1 else fallback_translation
            elif "中文翻譯：" in raw_value:
                english, chinese = raw_value.split("中文翻譯：", 1)
                english = english.strip()
                chinese = chinese.strip() or fallback_translation
            elif "中文：" in raw_value:
                english, chinese = raw_value.split("中文：", 1)
                english = english.strip()
                chinese = chinese.strip() or fallback_translation
            if english:
                items.append({"english": english, "chinese": chinese or fallback_translation})
    return items


def serialize_example_items(example_items: list) -> str:
    lines = []
    for item in example_items or []:
        if isinstance(item, dict):
            english = (item.get("english") or "").strip()
            chinese = (item.get("chinese") or "").strip()
        else:
            english = (item or "").strip()
            chinese = ""
        if not english:
            continue
        if chinese:
            lines.append(f"{english}｜{chinese}")
        else:
            lines.append(english)
    return "\n".join(lines)


def parse_stored_examples(example_text: str):
    items = []
    if not example_text:
        return items
    for line in example_text.splitlines():
        text = line.strip()
        if not text:
            continue
        english = text
        chinese = ""
        if "｜" in text:
            parts = [part.strip() for part in text.split("｜") if part.strip()]
            if parts:
                english = parts[0]
                chinese = parts[1] if len(parts) > 1 else ""
        elif "|" in text:
            parts = [part.strip() for part in text.split("|") if part.strip()]
            if parts:
                english = parts[0]
                chinese = parts[1] if len(parts) > 1 else ""
        elif "中文翻譯：" in text:
            english, chinese = text.split("中文翻譯：", 1)
            english = english.strip()
            chinese = chinese.strip()
        elif "中文：" in text:
            english, chinese = text.split("中文：", 1)
            english = english.strip()
            chinese = chinese.strip()
        if english:
            items.append({"english": english, "chinese": chinese})
    return items


def merge_example_sentences(primary_example: str, candidate_examples: list) -> list:
    merged = []
    seen = set()
    for example in [primary_example] + list(candidate_examples or []):
        normalized = (example or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def merge_example_items(primary_example, candidate_examples: list, fallback_translation: str = "") -> list:
    merged = []
    seen = set()
    source_items = []
    if isinstance(primary_example, dict):
        source_items.append(primary_example)
    elif primary_example:
        source_items.append({"english": primary_example, "chinese": fallback_translation})
    for item in list(candidate_examples or []):
        if isinstance(item, dict):
            source_items.append(item)
        elif item:
            source_items.append({"english": item, "chinese": fallback_translation})
    for item in source_items:
        english = (item.get("english") if isinstance(item, dict) else item or "").strip()
        chinese = (item.get("chinese") if isinstance(item, dict) else fallback_translation or "").strip()
        if not english:
            continue
        key = english.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append({"english": english, "chinese": chinese or fallback_translation})
    return merged


def resolve_translation_lookup(query: str, db_path: str = None):
    local_records = search_translation_entries(query, db_path=db_path)
    if local_records:
        record = local_records[0]
        example_entries = parse_stored_examples(record.get("example", ""))
        if not example_entries and record.get("example"):
            example_entries = [{"english": record.get("example", ""), "chinese": record.get("translation", "")}]
        return {
            "english": record["english"],
            "translation": record["translation"],
            "example": example_entries[0]["english"] if example_entries else "",
            "examples": example_entries,
            "source": "local",
        }
    return {"english": query, "translation": "", "example": "", "examples": [], "source": "llm"}


def get_flashcard_display_content(card, display_mode: str):
    if display_mode == "chinese":
        return card.get("translation", "") or card.get("english", "")
    return card.get("english", "") or card.get("translation", "")


def build_quiz_question(practice_items):
    if not practice_items:
        return {
            "question": "hello",
            "options": ["你好", "再見", "早安", "謝謝"],
            "answer": "你好",
        }
    sample = random.choice(practice_items)
    distractors = [
        item.get("translation", "")
        for item in practice_items
        if item.get("translation") and item.get("translation") != sample.get("translation")
    ]
    if len(distractors) < 3:
        distractors += ["請重新練習", "這是測驗示例", "請稍後再試"]
    options = [sample.get("translation", "")]
    for candidate in random.sample(distractors, k=min(3, len(distractors))):
        if candidate not in options:
            options.append(candidate)
    random.shuffle(options)
    return {
        "question": sample.get("english", "hello"),
        "options": options,
        "answer": sample.get("translation", ""),
    }


def render_english_learning_tab():
    st.subheader(t("english_learning_title"))
    st.caption(t("english_learning_desc"))

    if "review_toast_shown" not in st.session_state:
        st.session_state.review_toast_shown = False
    if "flashcard_index" not in st.session_state:
        st.session_state.flashcard_index = 0
    if "flashcard_revealed" not in st.session_state:
        st.session_state.flashcard_revealed = False
    if "flashcard_display_mode" not in st.session_state:
        st.session_state.flashcard_display_mode = "english"
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "未分類"
    if "table_page_size" not in st.session_state:
        st.session_state.table_page_size = 10
    if "table_page" not in st.session_state:
        st.session_state.table_page = 0

    stats = get_learning_stats(db_path=st.session_state.db_path)
    today = datetime.utcnow().date().isoformat()
    review_date = load_daily_review_state(db_path=st.session_state.db_path)
    show_review = should_show_daily_review_reminder(today=today, db_path=st.session_state.db_path)

    if show_review and not st.session_state.review_toast_shown:
        st.toast("🔔 今日提醒：建議完成 5 分鐘複習，讓學習更穩定。", icon="🔔")
        st.session_state.review_toast_shown = True

    if show_review:
        st.warning("📅 今日還沒有完成複習，建議再看 5 個單字或做一次測驗。")
    else:
        st.success(f"✅ 今日已完成複習，最後一次：{review_date}")

    if st.button("🗓️ 標記今日複習完成"):
        save_daily_review_state(today, db_path=st.session_state.db_path)
        st.session_state.review_toast_shown = False
        st.success("已記錄今日複習")
        st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("單字數量", stats["total_items"])
    with col2:
        st.metric("測驗次次數", stats["total_sessions"])
    with col3:
        st.metric("最近準確率", f"{stats['latest_accuracy'] * 100:.0f}%")

    st.markdown("---")
    st.subheader("🧠 AI 一鍵生成生字集 (AI Auto-Vocabulary)")
    st.caption("選擇您想學習的主題與級別，由 AI 自動為您生成單字並匯入本機字庫，免去手動輸入！")
    
    col_gen_theme, col_gen_level, col_gen_count = st.columns([2, 1, 1])
    with col_gen_theme:
        gen_theme = st.selectbox(
            "選擇學習主題",
            ["TOEFL 核心字彙", "IELTS 雅思字彙", "生活常用英文", "職場商務英文", "旅遊情境英文", "科技資訊英文"]
        )
    with col_gen_level:
        gen_level = st.selectbox(
            "選擇字彙難度",
            ["初級 (Basic)", "中級 (Intermediate)", "高級 (Advanced)"]
        )
    with col_gen_count:
        gen_count = st.number_input(
            "生成數量",
            min_value=3,
            max_value=15,
            value=5,
            step=1
        )
        
    if st.button("⚡ 開始生成並自動匯入", width=True):
        with st.spinner("AI 正在為您量身打造字彙庫並寫入資料庫中..."):
            try:
                llm = LLMFactory.get_llm(
                    st.session_state.provider,
                    model_name=st.session_state.model,
                    temperature=0.7
                )
                
                prompt = f"""請生成 {gen_count} 個適合 {gen_level} 程度的「{gen_theme}」英文單字或常用片語。
請嚴格以下方的 JSON 陣列格式回傳，不可包含任何 markdown 標記（如 ```json）或任何額外的文字/引言。

[
  {{
    "english": "單字或片語",
    "translation": "中文意思說明",
    "example": "英文例句 ｜ 中文翻譯"
  }}
]
"""
                response = llm.invoke([HumanMessage(content=prompt)])
                
                raw_json = response.content.strip()
                if raw_json.startswith("```"):
                    lines = raw_json.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_json = "\n".join(lines).strip()
                    
                import json
                vocab_list = json.loads(raw_json)
                
                added_count = 0
                imported_words = []
                for item in vocab_list:
                    eng = item.get("english", "").strip()
                    trans = item.get("translation", "").strip()
                    ex = item.get("example", "").strip()
                    if eng and trans:
                        save_translation_entry(
                            eng,
                            trans,
                            ex,
                            category=gen_theme,
                            db_path=st.session_state.db_path
                        )
                        imported_words.append(f"• **{eng}** ({trans})")
                        added_count += 1
                
                if added_count > 0:
                    st.success(f"✅ 成功自動匯入 {added_count} 個單字至「{gen_theme}」分類中！")
                    st.markdown("\n".join(imported_words))
                    st.session_state.saved_categories = _load_saved_categories(st.session_state.db_path)
                    st.session_state.selected_category = gen_theme
                    st.rerun()
                else:
                    st.error("產生的單字為空，請重試一次。")
            except Exception as e:
                st.error(f"❌ 生成失敗，錯誤原因: {e}")
                st.info("💡 提示：請確保您選擇的 AI 模型 (如 Google Gemini) 連線金鑰正常。")

    st.markdown("---")
    st.subheader("🃏 單字卡片模式")
    practice_items = list_english_practice_items(limit=100, db_path=st.session_state.db_path)
    if practice_items:
        categories = sorted({item.get("category", "未分類") for item in practice_items})
        if st.session_state.saved_categories:
            categories = sorted(set(categories) | set(st.session_state.saved_categories))
        selected_category = st.selectbox(
            "單字本分類",
            options=categories,
            index=max(0, categories.index(st.session_state.selected_category)) if st.session_state.selected_category in categories else 0,
        )
        st.session_state.selected_category = selected_category
        filtered_items = [item for item in practice_items if item.get("category", "未分類") == selected_category]
        if not filtered_items:
            filtered_items = practice_items

        index, revealed = normalize_flashcard_state(
            filtered_items,
            st.session_state.flashcard_index,
            st.session_state.flashcard_revealed,
        )
        st.session_state.flashcard_index = index
        st.session_state.flashcard_revealed = revealed
        card = filtered_items[index]
        total_cards = len(filtered_items)

        display_mode_label = st.radio(
            "顯示方向",
            ["英文", "中文"],
            horizontal=True,
            index=0 if st.session_state.flashcard_display_mode == "english" else 1,
            key="flashcard_display_mode_radio",
        )
        st.session_state.flashcard_display_mode = "english" if display_mode_label == "英文" else "chinese"

        if not st.session_state.flashcard_revealed:
            display_content = card["english"] if st.session_state.flashcard_display_mode == "english" else card["translation"]
            helper_text = "點擊顯示答案"
        else:
            display_content = card["translation"] if st.session_state.flashcard_display_mode == "english" else card["english"]
            helper_text = "答案已顯示"

        col_mode, col_add = st.columns([2, 1])
        with col_add:
            if st.button("收藏到分類"):
                save_translation_entry(
                    card["english"],
                    card["translation"],
                    card.get("example", ""),
                    category=selected_category,
                    db_path=st.session_state.db_path,
                )
                st.success(f"已收藏到 {selected_category}")

        with st.expander("🗂️ 管理分類"):
            new_category = st.text_input("新增分類名稱", value=st.session_state.new_category_name)
            if st.button("新增分類") and new_category.strip():
                new_value = new_category.strip()
                categories = sorted(set(st.session_state.saved_categories + [new_value]))
                st.session_state.saved_categories = categories
                _save_saved_categories(categories, st.session_state.db_path)
                st.session_state.selected_category = new_value
                st.session_state.new_category_name = ""
                st.rerun()
            if st.session_state.saved_categories:
                st.write("目前分類：" + "、".join(st.session_state.saved_categories))

        with st.expander("📚 目前分類單字清單"):
            list_category = st.selectbox(
                "查看分類",
                options=sorted(set([item.get("category", "未分類") for item in practice_items]) | set(st.session_state.saved_categories)),
                index=max(0, sorted(set([item.get("category", "未分類") for item in practice_items]) | set(st.session_state.saved_categories)).index(selected_category)) if selected_category in sorted(set([item.get("category", "未分類") for item in practice_items]) | set(st.session_state.saved_categories)) else 0,
                key="word_list_category",
            )
            category_items = [item for item in practice_items if item.get("category", "未分類") == list_category]
            if category_items:
                for index, item in enumerate(category_items):
                    col_item, col_delete = st.columns([8, 1])
                    with col_item:
                        example_text = item.get("example", "")
                        if example_text:
                            st.markdown(f"- **{item['english']}** → {item['translation']}  \n  例句：{example_text}")
                        else:
                            st.markdown(f"- **{item['english']}** → {item['translation']}")
                    with col_delete:
                        if st.button("🗑️", key=f"delete_word_{index}_{item['english']}"):
                            delete_translation_entry(item["english"], db_path=st.session_state.db_path)
                            st.success(f"已刪除 {item['english']}")
                            st.rerun()
            else:
                st.info("這個分類目前沒有單字")

        st.markdown(
            f"<div style='border: 2px solid #4f46e5; border-radius: 18px; padding: 1.2rem; background: linear-gradient(135deg, #f8faff 0%, #eef2ff 100%); margin-bottom: 0.8rem; box-shadow: 0 6px 18px rgba(79,70,229,0.1);'>"
            f"<div style='font-size: 0.9rem; color: #6366f1;'>卡片 {index + 1}/{total_cards} · {selected_category}</div>"
            f"<div style='font-size: 1.8rem; font-weight: 700; margin-top: 0.5rem; color: #111827;'>{display_content}</div>"
            f"<div style='margin-top: 0.8rem; color: #374151;'>{helper_text}</div></div>",
            unsafe_allow_html=True,
        )

        if card.get("example") and st.session_state.flashcard_revealed:
            st.caption(f"例句：{card['example']}")

        col_prev, col_show, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("◀ 上一張"):
                st.session_state.flashcard_index = (index - 1) % total_cards
                st.session_state.flashcard_revealed = False
                st.rerun()
        with col_show:
            if st.button("👁️ 顯示答案"):
                st.session_state.flashcard_revealed = True
                st.rerun()
        with col_next:
            if st.button("下一張 ▶"):
                st.session_state.flashcard_index = (index + 1) % total_cards
                st.session_state.flashcard_revealed = False
                st.rerun()

        if st.session_state.flashcard_revealed:
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✅ 還記得"):
                    record_study_session("flashcard", 1, 1, db_path=st.session_state.db_path)
                    st.session_state.flashcard_revealed = False
                    st.session_state.flashcard_index = (index + 1) % total_cards
                    st.success("已記錄這張卡片的複習結果")
                    st.rerun()
            with btn_col2:
                if st.button("❌ 再複習"):
                    record_study_session("flashcard", 0, 1, db_path=st.session_state.db_path)
                    st.session_state.flashcard_revealed = False
                    st.session_state.flashcard_index = (index + 1) % total_cards
                    st.info("已標記為需要再複習")
                    st.rerun()

        card_key = card.get("english", "")
        is_favorite = card_key in st.session_state.favorite_cards
        if st.button("⭐ 收藏" if not is_favorite else "☆ 取消收藏"):
            if is_favorite:
                st.session_state.favorite_cards = [item for item in st.session_state.favorite_cards if item != card_key]
            else:
                st.session_state.favorite_cards = sorted(set(st.session_state.favorite_cards + [card_key]))
            st.rerun()
        if is_favorite:
            st.caption("目前卡片：已收藏")
        else:
            st.caption("目前卡片：未收藏")
    else:
        st.info("目前沒有可複習的單字，先新增幾個英文詞彙吧。")

    st.markdown("---")
    st.subheader("📖 字典式查詢")
    search_query = st.text_input("搜尋英文或中文", placeholder="例如：hello 或 你好")

    if "translation_result" not in st.session_state:
        st.session_state.translation_result = None
    if "example_candidates" not in st.session_state:
        st.session_state.example_candidates = []

    if search_query.strip() and st.session_state.get("last_search_query") != search_query.strip():
        st.session_state.last_search_query = search_query.strip()
        local_lookup = resolve_translation_lookup(search_query.strip(), db_path=st.session_state.db_path)
        if local_lookup["source"] == "local":
            st.session_state.translation_result = {
                "english": local_lookup["english"] or search_query.strip(),
                "translation": local_lookup["translation"] or "（尚未取得）",
                "example": local_lookup.get("example", "") or "",
                "examples": local_lookup.get("examples", []),
            }
            st.session_state.example_candidates = local_lookup.get("examples", [])
            st.rerun()

    if st.button("🔍 查詢翻譯") and search_query.strip():
        with st.spinner("正在查詢本機資料與生成內容..."):
            try:
                local_lookup = resolve_translation_lookup(search_query.strip(), db_path=st.session_state.db_path)
                if local_lookup["source"] == "local":
                    translation = local_lookup["translation"]
                    example_entries = local_lookup.get("examples", [])
                    first_example = example_entries[0]["english"] if example_entries else local_lookup.get("example", "")
                else:
                    llm = LLMFactory.get_llm(
                        st.session_state.provider,
                        model_name=st.session_state.model,
                        temperature=st.session_state.temperature,
                    )
                    prompt = (
                        f"請提供英文單字或片語 '{search_query.strip()}' 的中文意思，並附上 3 個自然的英文例句與對應中文翻譯。"
                        "格式請固定如下：\n中文意思：...\n例句1：...｜中文：...\n例句2：...｜中文：...\n例句3：...｜中文：..."
                    )
                    response = llm.invoke([HumanMessage(content=prompt)])
                    translation, _ = parse_llm_translation_response(response.content)
                    example_entries = parse_llm_example_items(response.content, fallback_translation=translation)
                    if not example_entries:
                        first_example = parse_llm_example_sentences(response.content)
                        example_entries = [{"english": item, "chinese": translation} for item in first_example]
                    first_example = example_entries[0]["english"] if example_entries else ""
                st.session_state.translation_result = {
                    "english": local_lookup["english"] or search_query.strip(),
                    "translation": translation or "（尚未取得）",
                    "example": first_example or "",
                    "examples": example_entries,
                }
                st.session_state.example_candidates = example_entries
                st.session_state.last_search_query = search_query.strip()
                st.rerun()
            except Exception as exc:
                st.error(f"查詢失敗：{exc}")

    if st.session_state.translation_result:
        result = st.session_state.translation_result
        with st.container():
            st.markdown("### 查詢結果")
            st.text_input("英文", value=result["english"], key="dictionary_english")
            st.text_area("中文意思", value=result["translation"], key="dictionary_translation")
            st.text_area("主要例句", value=result.get("example", ""), key="dictionary_example")
            st.text_area("例句中文翻譯", value=(result.get("examples", [{}])[0].get("chinese", "") if result.get("examples") else ""), key="dictionary_example_translation")
            if st.session_state.example_candidates:
                st.caption("例句與中文翻譯")
                for idx, example in enumerate(st.session_state.example_candidates, 1):
                    if isinstance(example, dict):
                        english = example.get("english", "")
                        chinese = example.get("chinese", "")
                    else:
                        english = example
                        chinese = ""
                    st.write(f"{idx}. {english}")
                    if chinese:
                        st.caption(f"中文翻譯：{chinese}")
            col_add, col_generate = st.columns(2)
            with col_add:
                if st.button("➕ 加入單字本"):
                    example_entries = merge_example_items(
                        {"english": st.session_state.dictionary_example, "chinese": st.session_state.dictionary_example_translation},
                        st.session_state.example_candidates,
                        fallback_translation=st.session_state.dictionary_translation,
                    )
                    example_text = serialize_example_items(example_entries)
                    save_translation_entry(
                        st.session_state.dictionary_english,
                        st.session_state.dictionary_translation,
                        example_text,
                        category=st.session_state.selected_category,
                        db_path=st.session_state.db_path,
                    )
                    st.session_state.translation_result = {
                        "english": st.session_state.dictionary_english,
                        "translation": st.session_state.dictionary_translation,
                        "example": example_entries[0]["english"] if example_entries else "",
                        "examples": example_entries,
                    }
                    st.session_state.example_candidates = example_entries
                    st.success("已加入單字本")
                    st.rerun()
            with col_generate:
                if st.button("🧠 生成多個例句"):
                    with st.spinner("正在追加更多例句..."):
                        try:
                            llm = LLMFactory.get_llm(
                                st.session_state.provider,
                                model_name=st.session_state.model,
                                temperature=st.session_state.temperature,
                            )
                            prompt = (
                                f"請為英文單字或片語 '{st.session_state.dictionary_english}' 生成 3 個自然且有助於學習的英文例句，"
                                "每行請直接輸出『例句：英文內容｜中文：中文翻譯』。"
                            )
                            response = llm.invoke([HumanMessage(content=prompt)])
                            generated_examples = parse_llm_example_items(response.content, fallback_translation=st.session_state.dictionary_translation)
                            if not generated_examples:
                                generated_examples = [{"english": item, "chinese": st.session_state.dictionary_translation} for item in parse_llm_example_sentences(response.content)]
                            merged_examples = merge_example_items(
                                {"english": st.session_state.dictionary_example, "chinese": st.session_state.dictionary_example_translation},
                                st.session_state.example_candidates + generated_examples,
                                fallback_translation=st.session_state.dictionary_translation,
                            )
                            st.session_state.example_candidates = merged_examples
                            st.session_state.translation_result["examples"] = merged_examples
                            st.session_state.translation_result["example"] = merged_examples[0]["english"] if merged_examples else ""
                            st.success("已生成新的例句")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"生成例句失敗：{exc}")

    with st.form("translation_form", clear_on_submit=True):
        categories = sorted(set(st.session_state.saved_categories + [st.session_state.selected_category]))
        selected_save_category = st.selectbox("分類", options=categories, index=max(0, categories.index(st.session_state.selected_category)) if st.session_state.selected_category in categories else 0)
        english_phrase = st.text_input("英文", value=(st.session_state.translation_result or {}).get("english", "") if st.session_state.translation_result else "", placeholder="Hello")
        translation_phrase = st.text_input("中文說明", value=(st.session_state.translation_result or {}).get("translation", "") if st.session_state.translation_result else "", placeholder="你好")
        example_sentence = st.text_input("例句", value=(st.session_state.translation_result or {}).get("example", "") if st.session_state.translation_result else "", placeholder="Hello, world!")
        example_translation = st.text_input("例句中文翻譯", placeholder="你好")
        submitted = st.form_submit_button("💾 儲存翻譯")
        if submitted and english_phrase.strip():
            example_entries = [{"english": example_sentence.strip(), "chinese": (example_translation.strip() or translation_phrase.strip())}]
            save_translation_entry(
                english_phrase.strip(),
                translation_phrase.strip(),
                serialize_example_items(example_entries),
                category=selected_save_category,
                db_path=st.session_state.db_path,
            )
            st.session_state.selected_category = selected_save_category
            st.success("✅ 已保存到本機資料庫")
            st.rerun()

    st.markdown("---")
    st.subheader("🧪 TOEFL 風格測驗")
    if "quiz_question" not in st.session_state:
        st.session_state.quiz_question = None
        st.session_state.quiz_options = []
        st.session_state.quiz_answer = None
        st.session_state.quiz_result = None

    if "quiz_submitted" not in st.session_state:
        st.session_state.quiz_submitted = False

    if not st.session_state.quiz_question:
        practice_items = list_english_practice_items(limit=8, db_path=st.session_state.db_path)
        quiz_data = build_quiz_question(practice_items)
        st.session_state.quiz_question = quiz_data["question"]
        st.session_state.quiz_options = quiz_data["options"]
        st.session_state.quiz_answer = quiz_data["answer"]
        st.session_state.quiz_result = None
        st.session_state.quiz_submitted = False

    if st.session_state.quiz_question:
        st.write(f"請選擇最適合的中文意思：**{st.session_state.quiz_question}**")
        selected_answer = st.radio("選項", st.session_state.quiz_options, key="quiz_choice")
        if not st.session_state.quiz_submitted:
            if st.button("提交答案"):
                is_correct = selected_answer == st.session_state.quiz_answer
                st.session_state.quiz_result = is_correct
                st.session_state.quiz_submitted = True
                score = 1 if is_correct else 0
                record_study_session("toefl", score, 1, db_path=st.session_state.db_path)
                if is_correct:
                    st.success("✅ 答對了")
                else:
                    st.error(f"❌ 答錯了，正確答案是：{st.session_state.quiz_answer}")
        else:
            if st.session_state.quiz_result:
                st.success("✅ 答對了")
            else:
                st.error(f"❌ 答錯了，正確答案是：{st.session_state.quiz_answer}")
            if st.button("下一題"):
                st.session_state.quiz_question = None
                st.session_state.quiz_options = []
                st.session_state.quiz_answer = None
                st.session_state.quiz_result = None
                st.session_state.quiz_submitted = False
                st.rerun()

    st.markdown("---")
    st.subheader("📈 學習成效")
    sessions = list_study_sessions(limit=8, db_path=st.session_state.db_path)
    if sessions:
        total_score = sum(item["score"] for item in sessions)
        total_tests = sum(item["total"] for item in sessions)
        average_accuracy = round(total_score / total_tests, 2) if total_tests else 0.0
        st.metric("最近準確率", f"{average_accuracy * 100:.0f}%")
        for item in sessions:
            st.caption(f"{item['created_at'][:10]}｜{item['test_type']}｜{item['score']}/{item['total']}｜準確率 {item['accuracy'] * 100:.0f}%")
    else:
        st.info("目前還沒有測驗成效紀錄。")

    st.markdown("---")
    st.subheader("📊 學習趨勢")
    trend_sessions = list_study_sessions(limit=30, db_path=st.session_state.db_path)
    if trend_sessions:
        trend_rows = []
        for item in trend_sessions:
            day = item["created_at"][:10]
            existing = next((row for row in trend_rows if row["date"] == day), None)
            if existing is None:
                trend_rows.append({"date": day, "score": item["score"], "total": item["total"], "accuracy": item["accuracy"]})
            else:
                existing["score"] += item["score"]
                existing["total"] += item["total"]
                existing["accuracy"] = round((existing["accuracy"] + item["accuracy"]) / 2, 2)

        trend_rows = sorted(trend_rows, key=lambda item: item["date"])
        st.line_chart({"每日準確率": [row["accuracy"] for row in trend_rows]})
        st.bar_chart({"每日題數": [row["total"] for row in trend_rows]})
        st.dataframe(
            [{"日期": row["date"], "答對": row["score"], "總題數": row["total"], "準確率": f"{row['accuracy'] * 100:.0f}%"} for row in trend_rows],
            width=True,
        )
    else:
        st.info("目前還沒有測驗成效紀錄，先做一次測驗即可看到趨勢圖表。")


def render_db_tab():
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

    if st.button(t("test_connection"), width=True):
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
            st.dataframe(table_summary, width=True)

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
                            st.dataframe(records, width=True)
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

        if st.button("🔄 重載資料表結構", width=True):
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
                # 解決按鈕與有標籤的 selectbox 垂直跑版對齊問題
                st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button(t("preview"), width=True):
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
            # 解決按鈕與有標籤的 number_input 垂直跑版對齊問題
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 重新載入", width=True):
                st.rerun()

        st.session_state.query_sql = st.text_area(
            t("sql_query_label"),
            value=st.session_state.query_sql,
            height=140,
            placeholder=t("sql_placeholder"),
        )
        if st.button(t("run_sql"), width=True):
            if not st.session_state.query_sql.strip():
                st.warning(t("sql_query_required"))
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
                            width=True,
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
                        if st.button("🗑️ 刪除單筆", width=True):
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
                    if st.button("💾 保存編輯結果", width=True):
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
                if st.button(t("crud_insert_button"), width=True):
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
                if st.button(t("crud_update_button"), width=True):
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
                if st.button(t("crud_delete_button"), width=True):
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
        if st.button(t("generate_sql"), width=True):
            if not st.session_state.sql_description.strip():
                st.session_state.sql_feedback = {"type": "warning", "message": t("sql_description_required")}
            elif not st.session_state.db_analysis:
                st.session_state.sql_feedback = {"type": "warning", "message": t("sql_analysis_required")}
            else:
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


def main():
    if not STREAMLIT_AVAILABLE:
        print("❌ Streamlit 未安裝或無法導入")
        print("\n若要使用 Web UI，請安裝 Streamlit:")
        print("  pip install streamlit")
        print("\n或者使用 CLI 版本:")
        print("  python cli.py")
        return

    initialize_session_state()
    header_left, header_right = st.columns([5, 2])
    with header_left:
        st.markdown(f"# {t('app_title')}")
    with header_right:
        st.empty()
    st.markdown("---")

    with st.sidebar:
        render_sidebar()

    tab_chat, tab_db, tab_english = st.tabs([t("chat_tab_title"), t("db_management"), t("english_learning_tab")])
    with tab_chat:
        render_chat_tab()
    with tab_db:
        render_db_tab()
    with tab_english:
        render_english_learning_tab()

if __name__ == "__main__":
    main()
