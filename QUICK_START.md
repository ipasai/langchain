# 🤖 LangChain 多模型應用 - 快速開始指南

## 🚀 三種快速開始方式

### 方式 1: 主菜單模式（推薦新手）
```bash
python main.py
```
會顯示一個友善的菜單，讓你選擇：
- 1️⃣ 使用 CLI 命令行
- 2️⃣ 使用 Web UI 網頁界面
- 3️⃣ 測試模型連線
- 0️⃣ 退出

---

### 方式 2: 直接使用 CLI（快速測試）
```bash
python cli.py
```
特點：
- ✅ 快速啟動，無須等待網頁加載
- ✅ 支持多輪對話
- ✅ 易於集成到腳本中
- ✅ 命令行純文本操作

操作流程：
1. 選擇 AI 提供者（1=Ollama, 2=OpenAI, 3=Google）
2. 選擇模型
3. 設定溫度參數 (0.0-1.0)
4. 輸入提示詞
5. 獲取 AI 回應
6. 繼續提問或退出

---

### 方式 3: 啟動 Web UI（推薦高級用戶）
```bash
streamlit run app.py
```
特點：
- 🎨 漂亮的網頁介面
- 💾 對話歷史自動保存（session 內）
- 🎛️ 側邊欄設定面板
- 🌡️ 溫度滑塊調整
- 📱 手機友善設計

自動打開瀏覽器，訪問 http://localhost:8501

---

## 🎯 使用場景

| 場景 | 推薦方式 | 原因 |
|------|--------|------|
| 快速提問 | CLI | 快速、輕量 |
| 對話練習 | CLI 或 Web UI | 持續互動 |
| 展示/演示 | Web UI | 視覺效果好 |
| 批量處理 | Python 腳本 | 可編程 |
| 模型測試 | 主菜單選項3 | 快速驗證 |

---

## ⚙️ 配置模型參數

### 選擇模型提供者

#### 🏠 Ollama（本地）- 最推薦初學者
```
需求: 電腦上已安裝 Ollama
費用: 免費
優點: 不需要 API 金鑰，完全本地
缺點: 需要本地計算資源
```

模型列表：
- llama3 ⭐ 推薦
- mistral
- neural-chat
- dolphin-mixtral

#### ☁️ OpenAI（雲端）- 功能最強
```
需求: 設定 OPENAI_API_KEY
費用: 按使用量付費
優點: 最強大的模型，質量最高
缺點: 需要付費，受網路限制
```

模型列表：
- gpt-4o ⭐ 最新推薦
- gpt-4o-mini（便宜版本）
- gpt-4-turbo
- gpt-3.5-turbo（經濟版本）

#### 🔵 Google Gemini（雲端）- 免費試用
```
需求: 設定 GOOGLE_API_KEY
費用: 免費試用可用
優點: 可免費使用，多模態支持
缺點: 免費配額有限，受網路限制
```

模型列表：
- gemini-2.5-flash ⭐ 推薦
- gemini-1.5-pro
- gemini-1.5-flash

---

## 🌡️ 溫度參數調整建議

```
溫度 = 輸出的隨機性程度

0.0 ━━━━━━━━━━━━━━━━━ 1.0
冷酷精準          創意隨意

推薦設定:
┌─────────────────────────┐
│ 精確任務: 0.0-0.3      │
│ • 翻譯、程式設計       │
│ • 數據分析、事實查詢    │
│ • 數學計算              │
│                       │
│ 一般對話: 0.5-0.7      │
│ • 日常問答              │
│ • 信息檢索              │
│ • 普通對話              │
│                       │
│ 創意寫作: 0.8-1.0      │
│ • 故事創作              │
│ • 詩歌、廣告文案       │
│ • 腦力激盪              │
└─────────────────────────┘
```

---

## 📝 Python 程式碼範例

### 簡單使用
```python
from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage

# 創建 LLM
llm = LLMFactory.get_llm(ModelProvider.OLLAMA)

# 提問
response = llm.invoke([HumanMessage(content="你好")])
print(response.content)
```

### 切換模型
```python
# 使用不同提供者
ollama_llm = LLMFactory.get_llm(ModelProvider.OLLAMA, model_name="mistral")
openai_llm = LLMFactory.get_llm(ModelProvider.OPENAI, model_name="gpt-4o")
google_llm = LLMFactory.get_llm(ModelProvider.GOOGLE, model_name="gemini-2.5-flash")
```

### 調整參數
```python
# 低溫度 - 精確
precise = LLMFactory.get_llm(ModelProvider.OLLAMA, temperature=0.1)

# 中等溫度 - 平衡
balanced = LLMFactory.get_llm(ModelProvider.OLLAMA, temperature=0.5)

# 高溫度 - 創意
creative = LLMFactory.get_llm(ModelProvider.OLLAMA, temperature=0.9)
```

---

## 🔧 故障排除

### ❌ "Ollama 無法連線"
```
解決方案:
1. 確保 Ollama 正在運行
   → 終端運行: ollama serve
2. 確保模型已下載
   → 終端運行: ollama pull llama3
3. 檢查 .env 中的 OLLAMA_BASE_URL
```

### ❌ "OpenAI API Key 無效"
```
解決方案:
1. 確保 API Key 正確設定在 .env
2. 訪問 https://platform.openai.com/account/api-keys 驗證
3. 確保 API Key 尚未過期
```

### ❌ "Streamlit 無法啟動"
```
解決方案:
1. 重新安裝 streamlit
   → pip install --upgrade streamlit
2. 清除 streamlit 快取
   → rm -rf ~/.streamlit/cache
3. 確保端口 8501 未被占用
```

---

## 💾 .env 配置文件範例

編輯 `.env` 檔案並設定你的配置：

```env
# ============ OpenAI 配置 ============
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_MODEL=gpt-4o-mini

# ============ Ollama 配置 ============
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# ============ Google Gemini 配置 ============
GOOGLE_API_KEY=...your-api-key-here...
GOOGLE_MODEL=gemini-2.5-flash
```

---

## 📚 進階功能

### 獲取支持的模型列表
```python
from llm_factory import LLMFactory, ModelProvider

# 列出所有 Ollama 模型
ollama_models = LLMFactory.get_available_models(ModelProvider.OLLAMA)
print(f"Ollama 模型: {ollama_models}")

# 列出所有 OpenAI 模型
openai_models = LLMFactory.get_available_models(ModelProvider.OPENAI)
print(f"OpenAI 模型: {openai_models}")
```

### 自訂 API 參數
```python
llm = LLMFactory.get_ollama_llm(
    model_name="mistral",
    temperature=0.5,
    top_p=0.95,           # 其他參數
    top_k=40              # 其他參數
)
```

---

## ✨ 特色功能預覽

### CLI 特色
```
✅ 彩色輸出和 emoji 提示
✅ 友善的選擇菜單
✅ 實時連線測試
✅ 錯誤信息提示
✅ 多輪對話支持
```

### Web UI 特色
```
✅ 實時對話歷史
✅ 側邊欄設定面板
✅ 溫度滑塊調整
✅ 一鍵清除歷史
✅ 響應式設計
```

---

## 🎓 進階建議

1. **開始使用**: 用 Ollama 本地模型試玩
2. **試試看**: 對比不同模型的輸出質量
3. **調整參數**: 根據任務調整溫度
4. **擴展功能**: 添加自訂模型提供者
5. **自動化**: 在你的腳本中集成

---

## 📞 需要幫助？

1. 查看 `README.md` 了解詳細文檔
2. 運行 `python main.py` 中的選項 3 測試連線
3. 檢查 `.env` 檔案配置
4. 查看終端錯誤訊息獲取詳細信息

---

**開始體驗多模型 AI 應用吧！** 🚀

```bash
# 最快開始
python main.py
```
