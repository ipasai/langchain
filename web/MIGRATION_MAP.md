# Streamlit -> Next.js 功能對照

## 主頁籤

| Streamlit 功能 | 原始程式 | Next.js UI | API / 後端 |
| --- | --- | --- | --- |
| AI 對話 | `chat.py` | `components/Chat.jsx` | `pages/api/llm.js`、`pages/api/db.js` |
| 資料庫管理 | `db.py` | `components/DBManager.jsx` | `pages/api/db.js` |
| 英文學習 | `english_learning.py` | `components/EnglishLearning.jsx` | `pages/api/db.js` |
| 智慧文件分析 | `doc_analyzer.py` | `components/DocAnalyzer.jsx`、`components/MermaidRenderer.jsx` | `pages/api/doc.js`、`lib/docHandlers.js`、本機 Chroma |
| Markdown 語音學習助教 | 文件學習與 TTS 流程 | `components/MarkdownToSpeech.jsx` | `pages/api/learning.js`、`lib/learningDocument.js`、`lib/learningWorkflow.js`、`lib/learningStore.js`、`lib/ttsHandlers.js` |
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

## Markdown 語音學習助教

主頁籤 `Markdown 轉 MP3` 使用下列管線：

1. `lib/learningDocument.js` 以 Unified / remark AST 解析標題、段落、表格、清單、引用與程式碼區塊，配置 block ID 與原文行號。
2. `lib/learningWorkflow.js` 逐章呼叫所選 LLM，執行文件分析、初學者教學稿生成及內容驗證。
3. 程式檢查關鍵數字、單位、條件詞、來源 block 對應與來源區塊覆蓋；critical/major 或章節驗證失敗時禁止音訊合成。
4. `lib/learningStore.js` 儲存已驗證 job。`pages/api/learning.js?action=audio` 只接受 job ID 與教學 block ID，不接受任意未驗證文字。
5. 前端依 teaching block 分段合成，提供章節播放、單段重聽、MP3 下載、來源行號及原文對照。

目前是第一版 P0 管線：品質驗證包含 LLM 審查與數字/條件/來源追溯程式檢查。尚未提供對所有 Markdown/數學/程式碼語義的形式化正確性證明，也尚未有精準音訊時間戳同步；正式驗收仍需使用標準文件集與人工試聽、理解度測驗。

## 後端模組邊界

- `pages/api/doc.js` 只負責 HTTP action dispatch 與回應狀態。
- `lib/docHandlers.js` 負責文件儲存、文字抽取、索引、搜尋與心智圖。
- `pages/api/llm.js` 負責 Ollama、OpenAI、Google provider。
- `pages/api/db.js` 負責本機 SQLite 的資料存取。
- `pages/api/data.js` 負責 CSV、JSON、XLSX 分析。
- `pages/api/learning.js` 負責教學工作流程與經驗證區塊的音訊產生。
- `lib/learningStore.js` 保存短期 learning job，供音訊 API 驗證來源與狀態。

新增功能時，請優先新增對應元件或 handler 檔案，不要把功能直接堆回 `pages/index.js`。
