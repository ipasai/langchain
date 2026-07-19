#!/usr/bin/env python3
"""
LangChain Streamlit Web UI 應用
提供漂亮的網頁介面來選擇模型、調整參數並與 AI 進行對話
"""

import os

try:
    import streamlit as st
    from llm_factory import LLMFactory, ModelProvider
    from db_utils import (
        DBType,
        ensure_local_memory_database,
        load_recent_chat_messages,
    )
    from i18n import t, TRANSLATIONS, DEFAULT_LOCALE, get_current_locale
    from sidebar import Sidebar
    from chat import ChatPage
    from db import DatabasePage
    from english_learning import (
        EnglishLearningPage,
        get_flashcard_display_content,
        merge_example_sentences,
        normalize_flashcard_state,
        parse_llm_example_sentences,
        parse_llm_translation_response,
        resolve_translation_lookup,
        _load_saved_categories,
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
        sidebar = Sidebar()
        sidebar.render()

    tab_chat, tab_db, tab_english = st.tabs([t("chat_tab_title"), t("db_management"), t("english_learning_tab")])
    with tab_chat:
        chat_page = ChatPage()
        chat_page.render()
    with tab_db:
        db_page = DatabasePage()
        db_page.render()
    with tab_english:
        english_page = EnglishLearningPage()
        english_page.render()


if __name__ == "__main__":
    main()
