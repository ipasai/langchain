import streamlit as st
from llm_factory import LLMFactory
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from db_utils import save_chat_message
from i18n import t

class ChatPage:
    def __init__(self):
        pass

    def render(self):
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
            submit_button = st.button(t("submit"), use_container_width=True)

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
