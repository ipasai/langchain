import streamlit as st
from llm_factory import LLMFactory
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from db_utils import save_chat_message, delete_chat_message
from i18n import t

# ── 共用樣式常數 ───────────────────────────────────────────────
_DIVIDER = "<hr style='border:none;border-top:1.5px solid #e0e7ff;margin:1.2rem 0;'/>"


def _divider():
    st.markdown(_DIVIDER, unsafe_allow_html=True)


class ChatPage:
    def __init__(self):
        pass

    def render(self):
        # ── 頁面標題 ──────────────────────────────────────────────
        st.markdown(
            "<h2 style='color:#4f46e5;margin-bottom:0.1rem;'>💬 AI 對話</h2>"
            "<p style='color:#6b7280;font-size:0.92rem;margin-top:0;'>"
            "支援 Ollama・OpenAI・Google Gemini，對話記憶自動保存</p>",
            unsafe_allow_html=True,
        )

        # ════════════════════════════════════════════════════════
        # 區塊 1：輸入框（置頂）
        # ════════════════════════════════════════════════════════
        # 用 CSS 注入為輸入列加上視覺卡片效果，不用 HTML div 包 widget
        st.markdown(
            "<style>"
            ".input-card-row > div { background:linear-gradient(135deg,#f8faff 0%,#eef2ff 100%);"
            "border:1.5px solid #c7d2fe;border-radius:16px;padding:0.6rem 1rem;"
            "box-shadow:0 4px 14px rgba(99,102,241,0.07); }"
            "</style>",
            unsafe_allow_html=True,
        )

        input_col, btn_col = st.columns([9, 1])
        with input_col:
            # 僅用 key 綁定，不同時傳 value（避免 Streamlit widget 衝突）
            user_input = st.text_input(
                t("prompt_label"),
                placeholder=t("prompt_placeholder"),
                label_visibility="collapsed",
                key="user_input_input",
            )
        with btn_col:
            submit_button = st.button("✈️", use_container_width=True, help="送出訊息")

        # ── 送出處理 ──────────────────────────────────────────────
        if submit_button and user_input.strip():
            user_message = user_input.strip()
            st.session_state.messages.append({"role": "user", "content": user_message})
            save_chat_message("user", user_message, db_path=st.session_state.db_path)

            try:
                llm = LLMFactory.get_llm(
                    st.session_state.provider,
                    model_name=st.session_state.model,
                    temperature=st.session_state.temperature,
                )
                api_messages = []
                if st.session_state.get("system_prompt"):
                    api_messages.append(SystemMessage(content=st.session_state.system_prompt))
                recent = (
                    st.session_state.messages[-10:]
                    if len(st.session_state.messages) > 10
                    else st.session_state.messages
                )
                for msg in recent:
                    if msg["role"] == "user":
                        api_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        api_messages.append(AIMessage(content=msg["content"]))

                # 串流回應（顯示在暫存區）
                with st.chat_message("assistant", avatar="🤖"):
                    placeholder = st.empty()
                    assistant_reply = ""
                    for chunk in llm.stream(api_messages):
                        assistant_reply += chunk.content
                        placeholder.markdown(assistant_reply)

                st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
                save_chat_message("assistant", assistant_reply, db_path=st.session_state.db_path)
                st.rerun()

            except Exception as e:
                st.error(f"❌ {t('error_title')}: {e}")
                st.warning(t("check_list"))
                st.markdown(
                    f"- {t('provider_label')} 的連線設定\n"
                    "- API 金鑰是否正確設定在 .env 檔案\n"
                    "- 網路連線是否正常\n"
                    "- 若使用 Ollama，請確保 Ollama 服務已啟動"
                )

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 2：對話歷史（最新在上）
        # ════════════════════════════════════════════════════════
        msg_count = len(st.session_state.messages)
        st.markdown(
            f"<div style='font-size:1rem;font-weight:700;color:#4f46e5;margin-bottom:0.6rem;'>"
            f"🗂️ 對話歷史"
            f"<span style='font-size:0.78rem;font-weight:400;color:#9ca3af;margin-left:0.6rem;'>"
            f"共 {msg_count} 則，最新在上</span></div>",
            unsafe_allow_html=True,
        )

        if st.session_state.messages:
            # 反轉讓最新訊息排在最上面
            for i, message in enumerate(reversed(st.session_state.messages)):
                # 原始 index（未反轉前）
                orig_idx = len(st.session_state.messages) - 1 - i
                role = message["role"]
                avatar = "👤" if role == "user" else "🤖"
                msg_col, del_col = st.columns([11, 1])
                with msg_col:
                    with st.chat_message(role, avatar=avatar):
                        st.markdown(message["content"])
                with del_col:
                    # 讓刪除按鈕垂直置中對齊訊息泡泡
                    st.markdown("<div style='padding-top:0.6rem;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_msg_{orig_idx}", help="刪除此則對話"):
                        # 從 session_state 移除
                        removed = st.session_state.messages.pop(orig_idx)
                        # 若有資料庫 id 則同步刪除 DB 紀錄
                        msg_id = removed.get("id")
                        if msg_id:
                            delete_chat_message(msg_id, db_path=st.session_state.db_path)
                        st.rerun()
        else:
            st.markdown(
                "<div style='background:#f8faff;border:1.5px dashed #c7d2fe;border-radius:14px;"
                "padding:1.5rem;text-align:center;color:#9ca3af;font-size:0.92rem;'>"
                "🤖 還沒有對話紀錄，輸入訊息開始聊天吧！</div>",
                unsafe_allow_html=True,
            )

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 3：快速提示（三欄資訊卡）
        # ════════════════════════════════════════════════════════
        c1, c2, c3 = st.columns(3)
        info_cards = [
            (c1, "🌐", t("support_providers"), t("provider_list")),
            (c2, "💡", t("quick_tips"), t("tips_list")),
            (c3, "⚙️", t("settings_hint"), t("settings_list")),
        ]
        for col, icon, title, body in info_cards:
            with col:
                st.markdown(
                    f"<div style='background:#fff;border:1.5px solid #e0e7ff;border-radius:14px;"
                    f"padding:0.9rem 1rem;box-shadow:0 2px 8px rgba(99,102,241,0.06);height:100%;'>"
                    f"<div style='font-size:1.1rem;font-weight:700;color:#4f46e5;margin-bottom:0.4rem;'>"
                    f"{icon} {title}</div>"
                    f"<div style='font-size:0.85rem;color:#374151;line-height:1.6;'>{body}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
