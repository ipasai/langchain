本機 Chroma 服務器說明

此專案包含一個簡易的本機 Chroma HTTP 服務（使用 `rag_utils.py` + `chromadb`），提供索引與相似度搜尋的 API，方便 Next.js 應用整合。

快速啟動

1. 建議使用 Python 3.10+ 的虛擬環境：

```bash
python -m venv .venv
source .venv/bin/activate
```

2. 安裝所需套件：

```bash
pip install -r requirements-chroma.txt
```

3. 啟動服務（開發模式）：

```bash
uvicorn chroma_server:app --host 127.0.0.1 --port 8001 --reload
```

4. 驗證：

```bash
curl http://127.0.0.1:8001/health
# 應回傳 {"ok":true}
```

環境變數

若要讓 Next.js API 自動使用本機 Chroma，預設會嘗試 `http://127.0.0.1:8001`，可透過 `CHROMA_SERVER_URL` 覆蓋。

注意事項

- 服務使用 `rag_utils.py` 中的 `chroma` 實作，需要安裝 `chromadb` 與 `sentence-transformers`。
- 本機 Chroma 將以 `data/chroma_db/` 做為磁碟儲存目錄。
- 建議在具有足夠記憶體與 CPU 的環境運行向量索引。
