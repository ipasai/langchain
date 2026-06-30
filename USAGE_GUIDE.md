# 🎉 LangChain 多模型應用 - 使用指南

## ✅ 改進完成

你的 LangChain 專案已成功改進，現在支援：

### ✨ 核心功能
- ✅ **多模型支持**: Ollama、OpenAI、Google Gemini
- ✅ **參數切換**: 支援選擇不同模型和調整溫度參數
- ✅ **使用者介面**: CLI 和 Web UI 兩種操作方式
- ✅ **動態呼叫**: 根據選擇動態切換 LLM 模型
- ✅ **完整文檔**: 詳細的使用文檔和快速參考

---

## 🚀 快速開始

### 一鍵啟動（推薦）
```bash
cd /Users/autoclaw/Documents/langchain
source .venv/bin/activate
python main.py
```

然後選擇：
- **1** = CLI 模式（推薦快速測試）
- **2** = Web UI 模式（推薦長時間使用）
- **3** = 測試所有模型連線
- **0** = 退出

### 直接運行 CLI
```bash
python cli.py
```

最簡單直接的命令行交互方式。

---

## 📋 功能詳解

### 1️⃣ CLI 應用 (cli.py)

**特點：**
- 快速啟動，無須安裝額外包
- 支援多輪對話
- 友善的菜單選擇界面
- 完善的錯誤提示

**操作流程：**
```
1. 選擇模型提供者
   1 = Ollama（本地）
   2 = OpenAI（雲端）
   3 = Google Gemini（雲端）

2. 選擇具體模型
   從可用模型列表選擇，或輸入自訂模型名稱

3. 設定溫度參數
   0.0-1.0 之間，控制輸出的隨機性

4. 輸入提示詞
   問問題或給予任務

5. 獲取回應
   AI 會給出回應

6. 繼續對話或退出
   輸入 quit 結束，或繼續提問
```

**範例對話：**
```
【系統】正在初始化本地 Ollama 物件 (模型: llama3)...
>>> 請解釋什麼是機器學習
[AI 回應...]
>>> 那深度學習呢？
[AI 回應...]
>>> quit
👋 感謝使用 LangChain CLI 應用!
```

### 2️⃣ Web UI 應用 (app.py) - 可選

**特點（如果 Streamlit 已安裝）：**
- 漂亮的網頁界面
- 側邊欄設定面板
- 對話歷史自動保存
- 溫度滑塊調整
- 一鍵清除歷史

**安裝 Streamlit：**
```bash
pip install streamlit
streamlit run app.py
```

### 3️⃣ 模型工廠類 (llm_factory.py)

**在你的代碼中使用：**
```python
from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage

# 方法 1: 使用預設模型
llm = LLMFactory.get_ollama_llm()

# 方法 2: 指定模型
llm = LLMFactory.get_openai_llm(model_name="gpt-4o", temperature=0.5)

# 方法 3: 通用方法（推薦）
llm = LLMFactory.get_llm(
    provider=ModelProvider.GOOGLE,
    model_name="gemini-2.5-flash",
    temperature=0.7
)

# 調用模型
response = llm.invoke([HumanMessage(content="你好")])
print(response.content)
```

---

## 🔧 配置說明

### .env 環境變數

編輯 `.env` 檔案配置：

```env
# ============ OpenAI ============
OPENAI_API_KEY=sk-...你的金鑰...
OPENAI_MODEL=gpt-4o-mini

# ============ Ollama ============
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# ============ Google Gemini ============
GOOGLE_API_KEY=...你的金鑰...
GOOGLE_MODEL=gemini-2.5-flash
```

### 模型選擇建議

| 場景 | 推薦提供者 | 推薦模型 | 溫度 |
|------|----------|--------|------|
| 本地測試 | Ollama | llama3 | 0.7 |
| 精確翻譯 | OpenAI | gpt-4o-mini | 0.2 |
| 創意寫作 | OpenAI | gpt-4o | 0.9 |
| 一般對話 | 任何 | 預設 | 0.7 |
| 免費試用 | Google | gemini-2.5-flash | 0.7 |

---

## 🌡️ 溫度參數指南

```
溫度 = 輸出的隨機性程度

0.0 ━━━━━━━━━━━━━━━━━ 1.0
冷酷精準          創意隨意

使用建議：

0.0-0.3: 冷酷精準
  - 翻譯、程式設計
  - 事實查詢、數據分析
  - 數學計算
  - 最重複但正確

0.4-0.6: 平衡
  - 一般問答
  - 信息檢索
  - 日常對話

0.7-0.9: 創意
  - 故事寫作、詩歌
  - 廣告文案
  - 腦力激盪
  - 最隨意但有創意

1.0: 完全隨意
  - 實驗性使用
  - 最不可預測
```

---

## 📚 支援的模型清單

### 🏠 Ollama（本地）- 推薦初學者
需要先在電腦上安裝 Ollama：https://ollama.ai/

可用模型：
- llama3 ⭐ 推薦，中文支援好
- mistral - 快速，質量不錯
- neural-chat - 對話優化
- dolphin-mixtral - 較大的模型

### ☁️ OpenAI（雲端）- 功能最強
需要 API 金鑰：https://platform.openai.com/account/api-keys

可用模型：
- gpt-4o ⭐ 最新推薦
- gpt-4o-mini ⭐ 便宜且快
- gpt-4-turbo - 高性能
- gpt-3.5-turbo - 經濟版本

### 🔵 Google Gemini（雲端）- 免費試用
需要 API 金鑰：https://makersuite.google.com/app/apikey

可用模型：
- gemini-2.5-flash ⭐ 推薦，快速
- gemini-1.5-pro - 高質量
- gemini-1.5-flash - 快速

---

## 🎯 常見使用場景

### 場景 1: 快速提問（推薦 CLI）
```bash
python cli.py
# 1 (Ollama)
# 1 (llama3)
# 0.7 (溫度)
# 你的問題
```

### 場景 2: 多輪對話（推薦 CLI）
```bash
python cli.py
# 配置相同的模型
# 第一個問題
# 第二個問題
# ...
# quit
```

### 場景 3: 在 Python 腳本中使用
```python
from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage

# 創建 LLM
llm = LLMFactory.get_llm(ModelProvider.OLLAMA)

# 多次調用
for question in ["what is AI?", "explain ML"]:
    response = llm.invoke([HumanMessage(content=question)])
    print(f"Q: {question}")
    print(f"A: {response.content}\n")
```

### 場景 4: 批量處理提示詞
```python
from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage

prompts = [
    "翻譯成英文：你好",
    "翻譯成中文：Hello",
    "寫一首詩："
]

llm = LLMFactory.get_llm(ModelProvider.OPENAI, temperature=0.9)
for prompt in prompts:
    response = llm.invoke([HumanMessage(content=prompt)])
    print(response.content)
    print("-" * 50)
```

---

## ⚙️ 故障排除

### ❌ "Ollama 無法連線"
```
解決方案：
1. 確保 Ollama 已啟動
   → 打開新終端，運行：ollama serve

2. 確保模型已下載
   → ollama pull llama3

3. 驗證連線設定
   → 檢查 .env 中 OLLAMA_BASE_URL 是否正確
```

### ❌ "OpenAI API Key 無效"
```
解決方案：
1. 檢查 .env 中 API Key 是否正確
2. 訪問 https://platform.openai.com 驗證
3. 確保 API Key 未過期
4. 確保賬戶有額度
```

### ❌ "Streamlit 無法啟動"
```
解決方案：
1. 安裝 Streamlit
   → pip install streamlit

2. 清除快取
   → rm -rf ~/.streamlit/cache

3. 使用 CLI 版本代替
   → python cli.py
```

### ❌ "Python 版本錯誤"
```
提示：請使用 Python 3.10+

檢查版本：
python --version

如果版本太舊，使用虛擬環境或升級 Python
```

---

## 📂 文件結構

```
langchain/
├── llm_factory.py           # ✅ LLM 工廠類別
├── main.py                  # ✅ 主入口點（菜單）
├── cli.py                   # ✅ CLI 應用
├── app.py                   # ⭐ Web UI（可選）
├── .env                     # 設定檔案
├── requirements.txt         # ✅ 已更新
├── README.md                # ✅ 完整文檔
├── QUICK_START.md           # ⭐ 快速參考
└── .venv/                   # Python 虛擬環境
```

---

## 🔄 更新和升級

### 更新 OpenAI 模型列表
```python
# llm_factory.py 中修改
AVAILABLE_MODELS[ModelProvider.OPENAI] = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    # 新增你想要的模型
]
```

### 添加新的模型提供者
```python
# 在 llm_factory.py 中添加

class ModelProvider(Enum):
    # ...
    CUSTOM = "custom"

# 添加對應的方法
@staticmethod
def get_custom_llm(model_name=None, temperature=0.7):
    # 實現你的連線邏輯
    pass
```

---

## 💡 提示和技巧

### 技巧 1: 保存常用的 Prompt
```python
# 創建 prompts.py
DEFAULT_PROMPTS = {
    "translate_en": "請翻譯成英文：{}",
    "summarize": "請用 100 字概括：{}",
    "code_review": "請檢查這段代碼：{}",
}

# 在腳本中使用
from prompts import DEFAULT_PROMPTS
response = llm.invoke([HumanMessage(
    content=DEFAULT_PROMPTS["translate_en"].format(text)
)])
```

### 技巧 2: 並行調用多個模型
```python
from concurrent.futures import ThreadPoolExecutor
from langchain_core.messages import HumanMessage

llm_ollama = LLMFactory.get_llm(ModelProvider.OLLAMA)
llm_openai = LLMFactory.get_llm(ModelProvider.OPENAI)

question = "解釋人工智能"

with ThreadPoolExecutor(max_workers=2) as executor:
    future_ollama = executor.submit(
        lambda: llm_ollama.invoke([HumanMessage(content=question)])
    )
    future_openai = executor.submit(
        lambda: llm_openai.invoke([HumanMessage(content=question)])
    )
    
    response_ollama = future_ollama.result()
    response_openai = future_openai.result()
    
    print("Ollama:", response_ollama.content)
    print("OpenAI:", response_openai.content)
```

### 技巧 3: 批量生成
```python
from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage

# 生成 10 個創意標題
llm = LLMFactory.get_llm(
    ModelProvider.OPENAI,
    model_name="gpt-4o",
    temperature=0.9  # 高溫度 = 更創意
)

for i in range(10):
    response = llm.invoke([HumanMessage(
        content="請生成一個有創意的產品名稱"
    )])
    print(f"{i+1}. {response.content}")
```

---

## 📞 需要幫助？

### 查看文檔
```bash
# 完整文檔
cat README.md

# 快速參考
cat QUICK_START.md
```

### 運行測試
```bash
# 測試連線
python main.py
# 選擇 3 測試所有模型
```

### 調試模式
```bash
# 打印 LLM 配置
python -c "from llm_factory import LLMFactory; llm = LLMFactory.get_llm(__import__('llm_factory').ModelProvider.OLLAMA); print(llm)"
```

---

## 🎓 進階主題

### 主題 1: 自訂 System Prompt
```python
from langchain_core.messages import SystemMessage, HumanMessage

system_prompt = SystemMessage(
    content="你是一個專業的 Python 開發者，請用中文回答所有問題"
)

response = llm.invoke([
    system_prompt,
    HumanMessage(content="怎樣寫一個好的 Python 函數？")
])
```

### 主題 2: 使用 Chain
```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template("Explain {topic} in simple terms")
chain = prompt | llm | StrOutputParser()

result = chain.invoke({"topic": "machine learning"})
print(result)
```

### 主題 3: 記憶和上下文
```python
from langchain_core.messages import HumanMessage, AIMessage

# 保留對話歷史
messages = [
    HumanMessage(content="我叫 Alice"),
    AIMessage(content="很高興認識你，Alice！"),
    HumanMessage(content="我叫什麼名字？"),
]

response = llm.invoke(messages)
# 模型應該回答：你叫 Alice
```

---

## ✨ 功能展望

未來可以添加的功能：
- [ ] 對話歷史保存到文件
- [ ] 流式回應（Streaming）
- [ ] 語音輸入/輸出
- [ ] 文件上傳和分析
- [ ] 提示詞模板庫
- [ ] 模型性能對比
- [ ] 自訂系統提示設定
- [ ] API 服務模式

---

**現在你可以開始使用了！** 🚀

```bash
# 一鍵啟動
python main.py
```

---

**最後更新**: 2026-06-28  
**狀態**: ✅ 所有功能已完成並測試通過
