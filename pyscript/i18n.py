import js

CURRENT_LOCALE = "zh-tw"

TRANSLATIONS = {
    "zh-tw": {
        "app_title": "🤖 LangChain 多模型交互式應用",
        "chat_tab_title": "💬 AI 對話",
        "db_management": "🗄️ 資料庫管理",
        "english_learning_tab": "📘 英文學習",
        "app_settings": "系統設定",
        "provider_label": "選擇 AI 模型提供者",
        "provider_ollama": "Ollama (本地)",
        "provider_openai": "OpenAI (雲端)",
        "provider_google": "Google Gemini (雲端)",
        "temperature_label": "溫度 (Temperature)",
        "current_settings": "目前配置摘要",
        "database_settings": "資料庫連線狀態",
        "clear_history": "清除對話歷史",
        "chat_welcome": " 👋 歡迎使用 LangChain 多模型 AI 助理！請在下方輸入您想與 AI 對話的內容。",
        "prompt_input_title": "發送訊息",
        "prompt_placeholder": "請輸入您想詢問 AI 的問題或任務...",
        "submit": "送出",
        "sqlite_path": "SQLite 檔案路徑",
        "test_connection": "🔍 測試資料庫連線",
        "analysis_results": "📊 資料庫分析結果",
    },
    "en": {
        "app_title": "🤖 LangChain Multi-Model Workspace",
        "chat_tab_title": "💬 AI Chat",
        "db_management": "🗄️ Database Management",
        "english_learning_tab": "📘 English Practice",
        "app_settings": "System Settings",
        "provider_label": "Select Provider",
        "provider_ollama": "Ollama (Local)",
        "provider_openai": "OpenAI (Cloud)",
        "provider_google": "Google Gemini (Cloud)",
        "temperature_label": "Temperature",
        "current_settings": "Current Settings",
        "database_settings": "Database Status",
        "clear_history": "Clear History",
        "chat_welcome": "👋 Welcome to LangChain AI Assistant! Type a message below to get started.",
        "prompt_input_title": "Send Message",
        "prompt_placeholder": "Type your message or task here...",
        "submit": "Send",
        "sqlite_path": "SQLite File Path",
        "test_connection": "🔍 Test Connection",
        "analysis_results": "📊 Database Analysis",
    }
}

def t(key):
    locale = js.document.getElementById("ui-locale").value if js.document.getElementById("ui-locale") else CURRENT_LOCALE
    return TRANSLATIONS.get(locale, TRANSLATIONS["zh-tw"]).get(key, key)

def update_language_labels():
    locale = js.document.getElementById("ui-locale").value
    global CURRENT_LOCALE
    CURRENT_LOCALE = locale
    
    dict_trans = TRANSLATIONS.get(locale, TRANSLATIONS["zh-tw"])
    
    # Update HTML Element Texts
    elem_mappings = {
        "lbl-app-title": "app_title",
        "btn-tab-chat": "chat_tab_title",
        "btn-tab-db": "db_management",
        "btn-tab-english": "english_learning_tab",
        "lbl-provider": "provider_label",
        "lbl-temp": "temperature_label",
        "lbl-clear-history": "clear_history",
        "lbl-chat-title": "chat_tab_title",
        "lbl-submit": "submit",
        "lbl-test-connection": "test_connection",
        "lbl-analysis-results": "analysis_results",
    }
    
    for elem_id, trans_key in elem_mappings.items():
        el = js.document.getElementById(elem_id)
        if el and trans_key in dict_trans:
            # Preserve icons if present
            if elem_id == "btn-tab-chat":
                el.innerHTML = f'<i class="fa-solid fa-comments"></i> {dict_trans[trans_key]}'
            elif elem_id == "btn-tab-db":
                el.innerHTML = f'<i class="fa-solid fa-database"></i> {dict_trans[trans_key]}'
            elif elem_id == "btn-tab-english":
                el.innerHTML = f'<i class="fa-solid fa-book-open"></i> {dict_trans[trans_key]}'
            elif elem_id == "lbl-chat-title":
                el.innerHTML = f'<i class="fa-solid fa-comments" style="color: var(--color-purple);"></i> {dict_trans[trans_key]}'
            else:
                el.innerText = dict_trans[trans_key]
