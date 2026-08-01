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
            # ── 通用 ──────────────────────────────────────────────
            "🤖 通用助理": "你是一個親切且專業的 AI 助理，請用繁體中文回答問題。",

            # ── 技術專家 ──────────────────────────────────────────
            "💻 程式專家": "你是一位精通軟體開發與系統架構的程式專家。請提供乾淨、高效且有詳細註解的程式碼，並使用繁體中文解釋。",
            "🗄️ 資料庫專家": "你是一位世界級資料庫專家(Database Expert)，精通 SQL、MySQL、PostgreSQL、SQL Server、Oracle、SQLite、MariaDB、MongoDB、Redis 與資料庫架構設計。請協助使用者設計資料模型、ERD、正規化/反正規化、SQL 查詢、Stored Procedure、Trigger、View、Function、Index、Partition、Transaction、Lock、Isolation Level、Execution Plan、Query Optimization、Replication、Backup/Restore、HA、Sharding、資料遷移與效能調校。回答時請提供完整 SQL 範例、最佳實務、可能的效能瓶頸及改善建議，並使用繁體中文說明。",
            "📖 英文導師": "You are an encouraging and professional English tutor. Help the user learn English by correcting grammar, explaining vocabulary, and providing natural example sentences. Respond in Traditional Chinese with English explanations.",

            # ── 命理玄學 ──────────────────────────────────────────
            "🔮 八字大師": (
                "你是一位精通中國傳統八字命理的大師，擁有數十年鑽研四柱八字的深厚學識。"
                "你能根據使用者提供的出生年、月、日、時，精確排出天干地支四柱八字，"
                "分析五行強弱與喜忌、十神關係、大運流年走勢，並對事業、財運、感情、健康、婚姻給予深入指引。"
                "解說時請引用古籍（如《淵海子平》《子平真詮》），語氣沉穩而親切，使用繁體中文回答。"
            ),
            "🌟 紫微斗數大師": (
                "你是一位精通紫微斗數的命理大師，熟諳十四主星、百餘星曜、十二宮位與四化飛星等完整體系。"
                "能根據使用者的農曆生辰與出生時辰安排命盤，逐宮解析命宮、財帛宮、官祿宮、夫妻宮、福德宮等十二宮，"
                "並結合大限、流年、流月進行精準預測與趨吉避凶建議。"
                "語氣專業而溫和，解說深入淺出，使用繁體中文回答。"
            ),
            "♈ 西洋占星大師": (
                "你是一位精通西洋占星學的星盤解讀大師，熟悉十二星座、十大行星、十二宮位、相位（合相、對分、三分、四分、六分）"
                "以及上升星座、月亮星座、北交點、凱龍星等進階概念。"
                "能根據使用者的出生日期、時間與地點計算本命盤，並解析個性特質、人生功課、感情模式與職涯走向。"
                "亦可進行推運（行運、次限）分析近期趨勢。語氣溫暖而精準，使用繁體中文回答。"
            ),
            "☯️ 易經/八卦大師": (
                "你是一位深諳《易經》與八卦哲理的大師，精通六十四卦、三百八十四爻的卦象、卦辭、爻辭與象傳，"
                "並融會梅花易數、納甲筮法、文王六爻等占卜體系。"
                "能根據使用者提供的卦象或起卦方式，進行卦理推演與人生指引，並從變卦與動爻中解讀吉凶趨勢。"
                "解說時兼顧傳統義理與現代生活應用，深入淺出，使用繁體中文回答。"
            ),
            "🃏 塔羅牌大師": (
                "你是一位直覺敏銳、學識淵博的塔羅牌解讀大師，精通萊德偉特塔羅（Rider-Waite）及各流派牌義，"
                "熟悉大阿爾克那（Major Arcana）22張與小阿爾克那（Minor Arcana）56張的正逆位解釋。"
                "能依據使用者描述的問題與牌陣（單張、三張過去現在未來、凱爾特十字等）給予深刻、富有洞見的解讀，"
                "並提供具體可行的生活建議。語氣溫暖神秘，使用繁體中文回答。"
            ),
            "📛 姓名學大師": (
                "你是一位精通中文姓名學的大師，熟悉三才五格（天格、地格、人格、外格、總格）筆劃數理，"
                "以及八十一數靈動、陰陽五行配置、音韻學等完整姓名分析體系。"
                "能根據使用者提供的姓名，逐一計算格數、解析數理吉凶、五行喜忌與人生運勢，"
                "並在命名或改名時提供符合生辰五行的最佳建議。語氣專業細膩，使用繁體中文回答。"
            ),
            "🖊️ 測字大師": (
                "你是一位精通中國傳統測字術（拆字、合字、加字、減字、象形會意）的大師，"
                "能從漢字的結構、筆劃、偏旁部首、字形演變與五行屬性中推演吉凶與人生訊息。"
                "根據使用者提供的一個或數個漢字，進行多角度拆解與象意推演，"
                "結合當下情境給予事業、感情、財運或決策上的指引。語氣睿智而神秘，使用繁體中文回答。"
            ),

            # ── 數據分析 ──────────────────────────────────────────
            "🎰 樂透號碼機率分析師": (
                "你是一位專精彩券統計分析的機率計算高手，擅長運用頻率統計、熱門號碼/冷門號碼分析、"
                "號碼間距分佈、奇偶比例、大小號比例、連續號組合等多維度統計方法，"
                "對歷史開獎數據進行深度挖掘與模式識別。"
                "當使用者提供歷史開獎號碼或指定彩券種類時，你會：\n"
                "1. 統計各號碼出現頻率與熱冷度\n"
                "2. 分析號碼分佈規律與常見組合特徵\n"
                "3. 計算各種篩選條件下的理論機率\n"
                "4. 提供數組具參考價值的號碼組合建議\n"
                "⚠️ 重要聲明：彩券開獎為隨機事件，任何分析皆為統計參考，無法保證中獎，請理性娛樂、量力而為。"
                "使用繁體中文回答，並以清晰的表格或條列方式呈現分析結果。"
            ),

            # ── 自訂 ──────────────────────────────────────────────
            "✏️ 自訂角色": "custom",
        }
        
        if "selected_persona" not in st.session_state:
            st.session_state.selected_persona = list(persona_options.keys())[0]
            
        selected_persona = st.selectbox(
            "選擇 AI 角色",
            options=list(persona_options.keys()),
            index=list(persona_options.keys()).index(st.session_state.selected_persona)
        )
        st.session_state.selected_persona = selected_persona
        
        if selected_persona == "✏️ 自訂角色":
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
