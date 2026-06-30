# LangChain 多模型交互式應用

用 LangChain 寫的 AI 專案，支援多模型切換和直觀的使用者介面。

## ✨ 功能特性

1. ✅ 使用本機的 Ollama AI 模型
2. ✅ 建立 `.env` 來儲存相關設定
3. ✅ 產生了一個專門用來使用 Ollama、OpenAI 與 Google AI 連線的物件
4. ✅ **可以切換參數方式來呼叫使用不同的模型**
5. ✅ **增加使用者介面來輸入提示詞內容並呼叫模型進行操作**
6. 可以再幫我加上連接資料庫的功能設定頁面功能 並且可以選擇連結的資料庫為 mysql sqlite postgres redis mongodb mariadb 等類型 並且將在輸入相關選車與設定後進行式資料庫的測試連結 並進行資料庫的相關分析並且輸出到畫面上可以初步了解目前所連結的DB相關資訊 且許要有一個介面可以用自然語言輸入想要查詢該資料庫的任何敘述後讓AI模型協助產出sql語法並顯示在畫面上

## 🚀 快速開始

### 環境要求
- Python 3.10+
- 已安裝的相依套件（見下方安裝步驟）

### 安裝

```bash
# 1. 激活虛擬環境
source .venv/bin/activate

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 配置 .env 檔案（如有需要）
# 編輯 .env 檔案並設定相應的 API 金鑰
```

### 運行應用

```bash
# 啟動主菜單，選擇運行模式
python main.py
```

## 🎯 使用指南

### 模式選擇

當運行 `python main.py` 時，會出現以下選項：

#### 1️⃣ CLI 模式（命令行交互）

最簡單直接的使用方式：

```bash
python cli.py
```

特點：
- 命令行交互式界面
- 易於腳本集成
- 無須安裝額外依賴

過程：
1. 選擇 AI 模型提供者（Ollama、OpenAI、Google Gemini）
2. 選擇具體模型
3. 配置溫度參數（0.0-1.0）
4. 輸入提示詞並獲取回應
5. 支援多輪對話

#### 2️⃣ Web UI 模式（Streamlit 網頁應用）

功能豐富的圖形界面：

```bash
streamlit run app.py
```

特點：
- 漂亮的 Web 界面
- 實時對話歷史顯示
- 側邊欄設定面板
- 支援清除對話歷史
- 自動重新整理

功能：
- 🎛️ 模型選擇下拉菜單
- 🌡️ 溫度滑塊調整
- 💬 對話歷史記錄
- 🗑️ 一鍵清除歷史

#### 3️⃣ 測試連線

測試所有模型提供者的連線狀態：

```bash
# 在主菜單中選擇選項 3
python main.py
```

或直接在 Python 程式碼中測試：

```python
from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage

llm = LLMFactory.get_llm(ModelProvider.OLLAMA)
messages = [HumanMessage(content="你好")]
response = llm.invoke(messages)
print(response.content)
```

## 🔧 配置 .env 檔案

編輯 `.env` 檔案以配置不同的模型和 API 金鑰：

```env
# OpenAI 設定
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Ollama 本地設定
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Google AI Studio 設定
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MODEL=gemini-2.5-flash
```

## 📦 支援的模型

### Ollama（本地）
- llama3
- mistral
- neural-chat
- dolphin-mixtral
- 其他本地模型

### OpenAI（雲端）
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo
- gpt-3.5-turbo

### Google Gemini（雲端）
- gemini-2.5-flash
- gemini-1.5-pro
- gemini-1.5-flash

## 🏗️ 項目結構

```
langchain/
├── llm_factory.py      # LLM 工廠類別，支援多種模型
├── main.py             # 主入口點，提供菜單選擇
├── cli.py              # 命令行交互應用
├── app.py              # Streamlit Web UI 應用
├── .env                # 環境變數配置
├── requirements.txt    # Python 相依套件
└── README.md           # 本檔案
```

## 📚 核心類別說明

### LLMFactory

工廠類別，提供統一介面來建立不同的 LLM 實例。

```python
from llm_factory import LLMFactory, ModelProvider

# 使用 Ollama
llm = LLMFactory.get_ollama_llm(model_name="llama3", temperature=0.7)

# 使用 OpenAI
llm = LLMFactory.get_openai_llm(model_name="gpt-4o-mini", temperature=0.5)

# 使用 Google Gemini
llm = LLMFactory.get_google_llm(model_name="gemini-2.5-flash", temperature=0.8)

# 通用方法（推薦）
llm = LLMFactory.get_llm(ModelProvider.OLLAMA, model_name="llama3")
```

### ModelProvider（列舉）

定義支援的模型提供者：
- `ModelProvider.OLLAMA` - 本地 Ollama 模型
- `ModelProvider.OPENAI` - OpenAI 雲端服務
- `ModelProvider.GOOGLE` - Google Gemini 雲端服務

## 💡 使用示例

### Python 腳本中使用

```python
from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage

# 創建 LLM 實例
llm = LLMFactory.get_llm(
    ModelProvider.OLLAMA,
    model_name="llama3",
    temperature=0.7
)

# 準備訊息
messages = [HumanMessage(content="請解釋什麼是機器學習")]

# 調用模型
response = llm.invoke(messages)
print(response.content)
```

### 切換不同模型

```python
from llm_factory import LLMFactory, ModelProvider

# 創意寫作 - 使用較高溫度
creative_llm = LLMFactory.get_llm(
    ModelProvider.OPENAI,
    model_name="gpt-4o",
    temperature=0.9
)

# 精確任務 - 使用較低溫度
precise_llm = LLMFactory.get_llm(
    ModelProvider.OLLAMA,
    model_name="llama3",
    temperature=0.2
)
```

## 🔄 溫度參數說明

溫度參數（Temperature）控制模型輸出的隨機性：

- **0.0** - 最確定，輸出最一致但可能重複
- **0.5** - 平衡，兼具多樣性和穩定性
- **1.0** - 最隨機，輸出最有創意但不可預測

建議設定：
- 翻譯、程式設計、精確分析：0.0-0.3
- 一般對話、內容生成：0.5-0.7
- 創意寫作、腦力激盪：0.8-1.0

## ⚙️ 故障排除

### Ollama 連線失敗
- 確保 Ollama 已在後台運行：`ollama serve`
- 檢查 `OLLAMA_BASE_URL` 是否正確配置
- 確保模型已下載：`ollama pull llama3`

### OpenAI 連線失敗
- 檢查 `OPENAI_API_KEY` 是否正確設定
- 確保 API 金鑰有效且未過期
- 檢查網路連線

### Google Gemini 連線失敗
- 檢查 `GOOGLE_API_KEY` 是否正確設定
- 確保在 Google AI Studio 創建了 API 金鑰
- 檢查網路連線

### Streamlit 應用無法啟動
```bash
# 重新安裝 streamlit
pip install --upgrade streamlit
```

## 📖 相關文件

- [LangChain 文檔](https://python.langchain.com/)
- [Ollama 文檔](https://ollama.ai/)
- [Streamlit 文檔](https://docs.streamlit.io/)

## 📝 版本要求

```
Python >= 3.10
langchain >= 0.3.0
streamlit >= 1.28.0
python-dotenv >= 1.0.0
```

## 🎓 進階使用

### 自訂模型連線

如需添加新的模型提供者，可以修改 `llm_factory.py`：

```python
@staticmethod
def get_custom_llm(model_name: str = None, temperature: float = 0.7):
    """你的自訂 LLM"""
    # 實現邏輯
    pass
```

### 擴展 CLI 應用

`cli.py` 可以進一步擴展以支援更多功能，如：
- 儲存對話歷史
- 批量處理提示詞
- 自訂系統提示

## 📄 授權

此專案採用 MIT 授權。

---

**快速命令參考**

```bash
# 激活虛擬環境
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 運行主菜單
python main.py

# 直接運行 CLI 模式
python cli.py

# 直接運行 Web UI
streamlit run app.py

# 測試模型連線
python -c "from main import test_connections; test_connections()"
```

---

**最後更新**: 2026-06-28

