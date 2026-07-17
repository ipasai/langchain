# LangChain 多模型交互式應用

這是一個整合多模型 AI 對話、資料庫管理與英文學習的 Streamlit 應用，支援本機與雲端模型切換，並將學習資料保存到本機 SQLite。

## ✨ 目前功能總覽

- ✅ 支援 Ollama、OpenAI、Google Gemini 三種模型提供者
- ✅ 支援 AI 對話、提示詞輸入與對話歷史保存
- ✅ 支援資料庫連線測試與資料表結構分析
- ✅ 支援 SQLite / MySQL / PostgreSQL / MariaDB / Redis / MongoDB 連線
- ✅ 支援 SQL 查詢執行、資料表預覽、資料列 CRUD、單筆刪除與表格編輯
- ✅ 支援字典式查詢：先查詢本機資料庫，找不到時才呼叫大模型
- ✅ 支援翻譯結果、例句生成、例句合併與完整儲存
- ✅ 支援英文單字分類管理、單字卡片複習、測驗與學習統計
- ✅ 支援單字清單刪除與依分類排序管理

## 🚀 快速開始

### 環境要求
- Python 3.10+
- 安裝相依套件

### 安裝

```bash
### 建立虛擬環境在專案目錄下執行
python -m venv .venv

### 啟用虛擬環境
### Windows (Command Prompt)
.venv\Scripts\activate.bat

### Windows (PowerShell)
.venv\Scripts\Activate.ps1

### macOS / Linux
source .venv/bin/activate

### 啟用後，終端機提示字元前方會顯示 (.venv)，代表目前已處於隔離環境

### 安裝套件
pip install -r requirements.txt
```

### 啟動應用

```bash
python main.py
```

也可以直接啟動網頁版：

```bash
streamlit run app.py
```

## 🧭 功能分頁介紹

### 1. AI 對話頁籤
- 可選擇模型提供者與溫度
- 輸入提示詞後獲得 AI 回應
- 對話歷史會保存到本機資料庫

### 2. 資料庫管理頁籤
- 選擇資料庫類型並填入連線設定
- 點擊測試連線後可檢視資料表、欄位、關聯與預覽資料
- 支援 SQL 查詢、資料列新增/更新/刪除、CSV 下載與資料表編輯
- 重新載入按鈕會重整目前資料表結構

### 3. 英文學習頁籤
- 新增單字與中文翻譯
- 可為單字附加例句並儲存
- 支援分類管理與目前分類單字清單
- 可刪除單筆單字、查看例句與進行卡片式複習
- 提供 TOEFL 風格測驗與學習成效圖表

## 🔍 字典式查詢流程

1. 先在本機資料庫中查詢是否已有相同英文或中文記錄
2. 若有記錄，直接使用已保存的翻譯與例句
3. 若沒有，才請大模型生成中文意思與例句
4. 生成的例句可追加到原有例句清單中
5. 儲存時會把完整例句串接後寫入資料庫，方便之後查詢與顯示

## 📄 簡報檔

可直接開啟簡報檔：
- [APP_FEATURES_PRESENTATION.html](APP_FEATURES_PRESENTATION.html)

## 🧪 測試

已加入對以下功能的自動化測試：
- 資料庫查詢與 CRUD
- 英文學習資料儲存與搜尋
- 例句合併與單筆刪除
- 本機資料庫欄位遷移

執行方式：

```bash
python -m unittest discover -s tests -v
```

## ⚙️ .env 設定範例

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MODEL=gemini-2.5-flash
```

## 📦 專案結構

```text
langchain/
├── app.py
├── cli.py
├── db_utils.py
├── llm_factory.py
├── main.py
├── README.md
├── APP_FEATURES_PRESENTATION.html
└── tests/
```

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
# 建立虛擬環境在專案目錄下執行
python -m venv .venv

# 啟用虛擬環境
# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
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

