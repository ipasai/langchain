# Streamlit -> Next.js 功能對照

## 主頁籤

| Streamlit 功能 | 原始程式 | Next.js UI | API / 後端 |
| --- | --- | --- | --- |
| AI 對話 | `chat.py` | `components/Chat.jsx` | `pages/api/llm.js`、`pages/api/db.js` |
| 資料庫管理 | `db.py` | `components/DBManager.jsx` | `pages/api/db.js` |
| 英文學習 | `english_learning.py` | `components/EnglishLearning.jsx` | `pages/api/db.js` |
| 智慧文件分析 | `doc_analyzer.py` | `components/DocAnalyzer.jsx`、`components/MermaidRenderer.jsx` | `pages/api/doc.js`、`lib/docHandlers.js`、本機 Chroma |
| 資料分析 | `data_analysis_page.py` | `components/DataAnalysis.jsx` | `pages/api/data.js` |

## 共用設定

- Streamlit `sidebar.py` 對應 `components/SettingsSidebar.jsx`。
- Streamlit `app.py` 的 `st.tabs(...)` 對應 `components/AppTabs.jsx`。
- 主頁組裝在 `pages/index.js`，各功能維持獨立元件。

## 文件分析內層頁籤

`DocAnalyzer.jsx` 內對應原始文件分析流程：

- `上傳分析`：檔案上傳、摘要、索引、文件清單、心智圖產生。
- `知識模式`：摘要閱讀與瀏覽器 TTS。
- `考題測驗`：考題流程入口。
- `RAG 問答`：本機 Chroma 語意搜尋。
- `題庫管理`：題庫流程入口。
- `歷史紀錄`：上傳與索引紀錄入口。

## 後端模組邊界

- `pages/api/doc.js` 只負責 HTTP action dispatch 與回應狀態。
- `lib/docHandlers.js` 負責文件儲存、文字抽取、索引、搜尋與心智圖。
- `pages/api/llm.js` 負責 Ollama、OpenAI、Google provider。
- `pages/api/db.js` 負責本機 SQLite 的資料存取。
- `pages/api/data.js` 負責 CSV、JSON、XLSX 分析。

新增功能時，請優先新增對應元件或 handler 檔案，不要把功能直接堆回 `pages/index.js`。
