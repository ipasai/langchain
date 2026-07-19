import streamlit as st
from llm_factory import LLMFactory, ModelProvider
from db_utils import clear_chat_messages
from i18n import t

class Sidebar:
    def __init__(self):
        pass

    @staticmethod
    def handle_provider_change():
        """當模型提供者切換時，自動將 model 設為新提供者的預設值，避免狀態不一致導致跳回"""
        new_provider = st.session_state.temp_provider
        st.session_state.provider = new_provider
        
        # 取得新供應商的可選清單
        new_models = LLMFactory.get_available_models(new_provider)
        
        # 優先過濾掉含有 'embed' 關鍵字的向量模型，選取一般的對話模型
        chat_models = [m for m in new_models if "embed" not in m.lower()]
        
        # 更新 session_state 中的 model
        if chat_models:
            st.session_state.model = chat_models[0]
        elif new_models:
            st.session_state.model = new_models[0]
        else:
            st.session_state.model = ""

    def render(self):
        st.header(f"⚙️ {t('app_settings')}")
        
        provider_options = {
            t("provider_ollama"): ModelProvider.OLLAMA,
            t("provider_openai"): ModelProvider.OPENAI,
            t("provider_google"): ModelProvider.GOOGLE,
        }
        
        # 【安全檢查】確保 st.session_state.provider 的值存在於 provider_options 的 values 中
        # 如果它變成字串 (例如 "Google Gemini (雲端)" 或 "Ollama (本地)")，則自動更正為正確的 Enum 物件
        current_provider = st.session_state.get("provider")
        
        # 1. 如果 provider 是字串，嘗試轉換為 Enum
        if isinstance(current_provider, str):
            if current_provider in provider_options:  # 情況 A：它是中文標題
                st.session_state.provider = provider_options[current_provider]
            else:
                # 情況 B：它是 Enum 的 string value (例如 "ollama" 或 "google")
                try:
                    st.session_state.provider = ModelProvider(current_provider)
                except ValueError:
                    st.session_state.provider = ModelProvider.OLLAMA  # 終極降級
                    
        # 2. 如果根本不在可選的 values 內，安全降級為第一項
        if st.session_state.provider not in provider_options.values():
            st.session_state.provider = ModelProvider.OLLAMA

        # 3. 計算安全的 index (此時保證絕對不會報錯)
        provider_values = list(provider_options.values())
        default_provider_index = provider_values.index(st.session_state.provider)
        
        # 4. 渲染選單 (使用 temp_provider 並綁定 on_change 處理模型重設)
        st.selectbox(
            t("provider_label"),
            options=list(provider_options.keys()),
            index=default_provider_index,
            key="temp_provider",
            on_change=self.handle_provider_change
        )
        
        # 2. 取得當前供應商的所有可用模型
        available_models = LLMFactory.get_available_models(st.session_state.provider)
        
        # 強制排序
        available_models = sorted(available_models)
        
        # 3. 確保當前的 model 必須在 available_models 裡面
        if st.session_state.model not in available_models and available_models:
            # 優先選擇對話模型而非 embedding
            chat_models = [m for m in available_models if "embed" not in m.lower()]
            st.session_state.model = chat_models[0] if chat_models else available_models[0]
            
        # 4. 渲染模型選單：使用 key 直接雙向綁定 "model"
        st.selectbox(
            "選擇 AI 模型",
            options=available_models,
            key="model",
            format_func=LLMFactory.get_formatted_model_name
        )
        
        # 5. 溫度調整
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
            "資料庫專家 (Database Expert)": "你是一位世界級資料庫專家(Database Expert)，精通 SQL、MySQL、PostgreSQL、SQL Server、Oracle、SQLite、MariaDB、MongoDB、Redis 與資料庫架構設計。請協助使用者設計資料模型、ERD、正規化/反正規化、SQL 查詢、Stored Procedure、Trigger、View、Function、Index、Partition、Transaction、Lock、Isolation Level、Execution Plan、Query Optimization、Replication、Backup/Restore、HA、Sharding、資料遷移與效能調校。回答時請提供完整 SQL 範例、最佳實務、可能的效能瓶頸及改善建議，並使用繁體中文說明。",
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

        if st.button(f"🗑️ {t('clear_history')}", use_container_width=True):
            st.session_state.messages = []
            st.session_state.user_input = ""
            st.session_state.generated_sql = ""
            clear_chat_messages(db_path=st.session_state.db_path)
            st.rerun()
