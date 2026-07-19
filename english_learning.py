import json
import os
import random
from datetime import datetime
import streamlit as st
from llm_factory import LLMFactory
from langchain_core.messages import HumanMessage
from i18n import t
from db_utils import (
    delete_translation_entry,
    get_learning_stats,
    list_english_practice_items,
    list_study_sessions,
    load_daily_review_state,
    record_study_session,
    save_daily_review_state,
    save_setting,
    load_setting,
    save_translation_entry,
    search_translation_entries,
    should_show_daily_review_reminder,
)

def _load_saved_categories(db_path):
    raw_value = load_setting("english_categories", "[]", db_path=db_path) or "[]"
    try:
        categories = json.loads(raw_value)
    except Exception:
        categories = []
    return [item for item in categories if isinstance(item, str) and item.strip()] or ["未分類"]


def _save_saved_categories(categories, db_path):
    save_setting("english_categories", json.dumps(categories, ensure_ascii=False), db_path=db_path)


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

class EnglishLearningPage:
    def __init__(self):
        pass

    def render(self):
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
            
        if st.button("⚡ 開始生成並自動匯入", use_container_width=True):
            with st.spinner("AI 正在為您量身打造字彙庫並寫入資料庫中..."):
                try:
                    llm = LLMFactory.get_llm(
                        st.session_state.provider,
                        model_name=st.session_state.model,
                        temperature=0.7
                    )
                    
                    prompt = f"""請生成 {gen_count} 個適合 {gen_level} 程度的「{gen_theme}」英文單字或常用片語。
請嚴格以下方的 JSON 陣列格式回傳，不可包含 any markdown 標記（如 ```json）或 any 額外的文字/引言。

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
                category_options = sorted(set([item.get("category", "未分類") for item in practice_items]) | set(st.session_state.saved_categories))
                default_index = 0
                if selected_category in category_options:
                    default_index = category_options.index(selected_category)
                list_category = st.selectbox(
                    "查看分類",
                    options=category_options,
                    index=default_index,
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
                use_container_width=True,
            )
        else:
            st.info("目前還沒有測驗成效紀錄，先做一次測驗即可看到趨勢圖表。")
