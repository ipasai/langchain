import sqlite3
import os
import asyncio
import js
from pyodide.http import pyfetch
from pyodide.ffi import create_proxy

from i18n import update_language_labels, t
from sidebar import populate_models_dropdown, handle_temp_change, handle_persona_change, update_summary_card
from chat import refresh_chat_messages_ui, send_chat_message, clear_chat_history
from db import (
    render_db_config_fields,
    test_db_connection,
    preview_db_table,
    run_custom_sql_query,
    delete_sqlite_row,
    generate_sql_from_natural_language,
    copy_generated_sql,
    apply_generated_sql,
    export_query_results_csv,
)
from english_learning import (
    refresh_english_practice_metrics,
    mark_daily_review_complete,
    add_custom_category,
    refresh_category_words_list,
    refresh_flashcard_view,
    toggle_card_flip,
    reveal_card_answer,
    card_next,
    card_prev,
    handle_card_remember,
    handle_card_review_need,
    collect_card_to_category,
    run_dict_lookup,
    generate_multiple_examples,
    save_word_from_dict,
    save_single_word_manual,
    run_vocab_auto_generation,
    render_new_quiz_question,
    submit_quiz_answer,
)

conn = None

def init_local_db():
    global conn
    conn = sqlite3.connect("app_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS english_practice (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        english TEXT NOT NULL,
        translation TEXT NOT NULL,
        example TEXT,
        category TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_type TEXT NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        accuracy REAL NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_review (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_date TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()

async def load_env():
    try:
        response = await pyfetch(".env")
        if response.status == 200:
            content = await response.string()
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip().strip("'").strip('"')
                    os.environ[k.strip()] = v
    except Exception:
        pass

def show_toast(text, is_success=True):
    toast = js.document.getElementById("toast")
    toast_text = js.document.getElementById("toast-text")
    if not toast or not toast_text:
        return
        
    toast_text.innerText = text
    if is_success:
        toast.className = "toast toast-success show"
    else:
        toast.className = "toast toast-error show"
        
    async def hide_later():
        await asyncio.sleep(3.0)
        toast.className = toast.className.replace(" show", "")
    asyncio.ensure_future(hide_later())

def setup_tabs():
    btns = js.document.querySelectorAll(".tab-btn")
    def handle_tab_click(event):
        target_btn = event.currentTarget
        tab_id = target_btn.getAttribute("data-tab")
        for b in js.document.querySelectorAll(".tab-btn"):
            b.classList.remove("active")
        for c in js.document.querySelectorAll(".tab-content"):
            c.classList.remove("active")
            
        target_btn.classList.add("active")
        target_content = js.document.getElementById(tab_id)
        if target_content:
            target_content.classList.add("active")
            
    for btn in btns:
        btn.addEventListener("click", create_proxy(handle_tab_click))

async def main():
    try:
        init_local_db()
        await load_env()
        setup_tabs()
        
        await populate_models_dropdown()
        js.document.getElementById("ai-provider").addEventListener("change", create_proxy(lambda e: asyncio.ensure_future(populate_models_dropdown())))
        js.document.getElementById("ai-model").addEventListener("change", create_proxy(lambda e: update_summary_card()))
        js.document.getElementById("ai-temp").addEventListener("input", create_proxy(handle_temp_change))
        js.document.getElementById("ai-persona").addEventListener("change", create_proxy(handle_persona_change))
        
        js.document.getElementById("ui-locale").addEventListener("change", create_proxy(lambda e: [update_language_labels(), refresh_chat_messages_ui(conn)]))
        update_language_labels()
        
        js.document.getElementById("btn-clear-history-sidebar").addEventListener("click", create_proxy(lambda e: clear_chat_history(e, conn, show_toast)))
        
        refresh_chat_messages_ui(conn)
        js.document.getElementById("btn-send-chat").addEventListener("click", create_proxy(lambda e: asyncio.ensure_future(send_chat_message(e, conn, show_toast))))
        
        render_db_config_fields()
        js.document.getElementById("db-type-select").addEventListener("change", create_proxy(render_db_config_fields))
        js.document.getElementById("btn-test-db").addEventListener("click", create_proxy(lambda e: asyncio.ensure_future(test_db_connection(e))))
        js.document.getElementById("btn-db-table-preview").addEventListener("click", create_proxy(preview_db_table))
        js.document.getElementById("btn-db-table-reload").addEventListener("click", create_proxy(preview_db_table))
        js.document.getElementById("btn-db-run-sql").addEventListener("click", create_proxy(lambda e: asyncio.ensure_future(run_custom_sql_query(e))))
        js.document.getElementById("btn-db-delete-row").addEventListener("click", create_proxy(lambda e: delete_sqlite_row(e, show_toast)))
        js.document.getElementById("btn-db-generate-sql").addEventListener("click", create_proxy(lambda e: asyncio.ensure_future(generate_sql_from_natural_language(e))))
        js.document.getElementById("btn-db-copy-sql").addEventListener("click", create_proxy(lambda e: copy_generated_sql(e, show_toast)))
        js.document.getElementById("btn-db-apply-sql").addEventListener("click", create_proxy(apply_generated_sql))
        js.document.getElementById("btn-db-download-csv").addEventListener("click", create_proxy(lambda e: export_query_results_csv(e, show_toast)))
        
        refresh_english_practice_metrics(conn)
        js.document.getElementById("btn-mark-review-completed").addEventListener("click", create_proxy(lambda e: mark_daily_review_complete(e, conn, show_toast)))
        js.document.getElementById("btn-vocab-auto-generate").addEventListener("click", create_proxy(lambda e: asyncio.ensure_future(run_vocab_auto_generation(e, conn, show_toast))))
        
        refresh_flashcard_view(conn)
        js.document.getElementById("flashcard-perspective").addEventListener("click", create_proxy(toggle_card_flip))
        js.document.getElementById("btn-card-reveal").addEventListener("click", create_proxy(reveal_card_answer))
        js.document.getElementById("btn-card-next").addEventListener("click", create_proxy(lambda e: card_next(conn, e)))
        js.document.getElementById("btn-card-prev").addEventListener("click", create_proxy(lambda e: card_prev(conn, e)))
        js.document.getElementById("btn-card-remember").addEventListener("click", create_proxy(lambda e: handle_card_remember(e, conn, show_toast)))
        js.document.getElementById("btn-card-review-need").addEventListener("click", create_proxy(lambda e: handle_card_review_need(e, conn, show_toast)))
        js.document.getElementById("btn-card-collect-cat").addEventListener("click", create_proxy(lambda e: collect_card_to_category(e, conn, show_toast)))
        js.document.getElementById("vocab-card-category-select").addEventListener("change", create_proxy(lambda e: refresh_flashcard_view(conn)))
        
        def toggle_fav_card(e):
            btn = js.document.getElementById("btn-card-favorite")
            if "btn-secondary" in btn.className:
                btn.className = "btn btn-primary"
                btn.innerHTML = '<i class="fa-solid fa-star" style="color:var(--color-amber);"></i> 已收藏'
                show_toast("已收藏目前卡片！")
            else:
                btn.className = "btn btn-secondary"
                btn.innerHTML = '<i class="fa-solid fa-star"></i> 收藏'
                show_toast("已取消收藏目前卡片")
        js.document.getElementById("btn-card-favorite").addEventListener("click", create_proxy(toggle_fav_card))
        
        js.document.getElementById("btn-dict-search").addEventListener("click", create_proxy(lambda e: asyncio.ensure_future(run_dict_lookup(e, conn, show_toast))))
        js.document.getElementById("btn-dict-save-word").addEventListener("click", create_proxy(lambda e: save_word_from_dict(e, conn, show_toast)))
        js.document.getElementById("btn-dict-gen-examples").addEventListener("click", create_proxy(lambda e: asyncio.ensure_future(generate_multiple_examples(e, show_toast))))
        js.document.getElementById("btn-vocab-save-single").addEventListener("click", create_proxy(lambda e: save_single_word_manual(e, conn, show_toast)))
        js.document.getElementById("btn-cat-add").addEventListener("click", create_proxy(lambda e: add_custom_category(e, conn, show_toast)))
        js.document.getElementById("cat-view-list-select").addEventListener("change", create_proxy(lambda e: refresh_category_words_list(conn, e)))
        
        render_new_quiz_question(conn)
        js.document.getElementById("btn-quiz-submit").addEventListener("click", create_proxy(lambda e: submit_quiz_answer(e, conn, show_toast)))
        js.document.getElementById("btn-quiz-next").addEventListener("click", create_proxy(lambda e: render_new_quiz_question(conn)))
        
    except Exception as exc:
        print("Initialization Exception:", exc)
    finally:
        loader = js.document.getElementById("loading-overlay")
        if loader:
            loader.style.opacity = "0"
            async def remove_loader():
                await asyncio.sleep(0.5)
                loader.style.display = "none"
            asyncio.ensure_future(remove_loader())

asyncio.ensure_future(main())
