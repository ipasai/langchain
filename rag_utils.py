"""
rag_utils.py
RAG（Retrieval-Augmented Generation）核心工具
- 支援多種檔案格式：PDF、DOCX、TXT、CSV、XLSX、MD、Python、程式碼等
- 文字切塊（chunking）
- 向量化並存入 ChromaDB
- 語意查詢（similarity search）
"""

from __future__ import annotations

import hashlib
import io
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 延遲匯入（避免未安裝時整個模組掛掉）─────────────────────────

def _require(pkg: str, install_hint: str = ""):
    try:
        return __import__(pkg)
    except ImportError:
        hint = install_hint or pkg
        raise ImportError(f"缺少套件 '{pkg}'，請執行：pip install {hint}")


# ── 常數 ─────────────────────────────────────────────────────────

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
COLLECTION_NAME = "doc_knowledge"
CHUNK_SIZE = 800          # 每個 chunk 的字元數
CHUNK_OVERLAP = 100       # 前後 overlap
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # sentence-transformers 輕量模型


# ── 檔案讀取 ─────────────────────────────────────────────────────

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """從上傳的檔案 bytes 中提取純文字內容。"""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return _extract_docx(file_bytes)
    elif ext in (".xlsx", ".xls"):
        return _extract_excel(file_bytes)
    elif ext == ".csv":
        return _extract_csv(file_bytes)
    elif ext in (".txt", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp",
                 ".h", ".go", ".rs", ".rb", ".php", ".html", ".css",
                 ".json", ".yaml", ".yml", ".xml", ".sh", ".bat"):
        return _extract_text(file_bytes)
    else:
        # 嘗試當作 UTF-8 文字
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception:
            raise ValueError(f"不支援的檔案類型：{ext}")


def _extract_pdf(data: bytes) -> str:
    pypdf = _require("pypdf", "pypdf==5.1.0")
    reader = pypdf.PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages)


def _extract_docx(data: bytes) -> str:
    docx = _require("docx", "python-docx==1.1.2")
    doc = docx.Document(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_excel(data: bytes) -> str:
    openpyxl = _require("openpyxl", "openpyxl==3.1.5")
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        lines.append(f"=== 工作表：{sheet_name} ===")
        for row in ws.iter_rows(values_only=True):
            row_str = "\t".join(str(v) if v is not None else "" for v in row)
            if row_str.strip():
                lines.append(row_str)
    return "\n".join(lines)


def _extract_csv(data: bytes) -> str:
    import csv
    text = data.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = ["\t".join(row) for row in reader]
    return "\n".join(rows)


def _extract_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "big5", "gbk", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


# ── 文字切塊 ─────────────────────────────────────────────────────

def split_text_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """將長文字切割成帶有 overlap 的 chunks。"""
    text = text.strip()
    if not text:
        return []

    # 優先在段落/句子邊界切割
    paragraphs = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= chunk_size:
            current = current + "\n\n" + para if current else para
        else:
            if current:
                chunks.append(current.strip())
                # overlap：帶入前一段的後半
                tail = current[-overlap:] if len(current) > overlap else current
                current = tail + "\n\n" + para
            else:
                # 單段超過 chunk_size，強制切割
                while len(para) > chunk_size:
                    chunks.append(para[:chunk_size])
                    para = para[chunk_size - overlap:]
                current = para

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c.strip()]


# ── 內容雜湊 ─────────────────────────────────────────────────────

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ── ChromaDB 向量庫操作 ───────────────────────────────────────────

def _get_chroma_collection():
    """取得 ChromaDB collection（lazy init）。"""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def index_document(
    doc_id: int,
    filename: str,
    chunks: List[str],
) -> int:
    """將文件 chunks 向量化並存入 ChromaDB，回傳成功數量。"""
    collection = _get_chroma_collection()

    # 先刪除同一 doc_id 的舊資料
    try:
        existing = collection.get(where={"doc_id": doc_id})
        if existing and existing.get("ids"):
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    ids, documents, metadatas = [], [], []
    for i, chunk in enumerate(chunks):
        chunk_id = f"doc_{doc_id}_chunk_{i}"
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({"doc_id": doc_id, "filename": filename, "chunk_index": i})

    if ids:
        # 批次分批上傳（避免超過 ChromaDB 單次限制）
        batch_size = 100
        for start in range(0, len(ids), batch_size):
            collection.add(
                ids=ids[start:start + batch_size],
                documents=documents[start:start + batch_size],
                metadatas=metadatas[start:start + batch_size],
            )

    return len(ids)


def query_knowledge(
    question: str,
    n_results: int = 5,
    doc_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    根據問題在向量庫中進行語意搜尋。
    若指定 doc_id，只在該文件的 chunks 中搜尋。
    回傳 [{"text": ..., "filename": ..., "chunk_index": ..., "distance": ...}]
    """
    collection = _get_chroma_collection()

    where_filter = {"doc_id": doc_id} if doc_id is not None else None

    try:
        result = collection.query(
            query_texts=[question],
            n_results=min(n_results, collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        # collection 為空時會拋錯
        return []

    if not result or not result.get("documents"):
        return []

    hits = []
    docs = result["documents"][0]
    metas = result["metadatas"][0]
    dists = result["distances"][0]
    for doc_text, meta, dist in zip(docs, metas, dists):
        hits.append({
            "text": doc_text,
            "filename": meta.get("filename", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "distance": round(float(dist), 4),
        })
    return hits


def delete_document_from_chroma(doc_id: int) -> None:
    """從 ChromaDB 中刪除指定 doc_id 的所有 chunks。"""
    try:
        collection = _get_chroma_collection()
        existing = collection.get(where={"doc_id": doc_id})
        if existing and existing.get("ids"):
            collection.delete(ids=existing["ids"])
    except Exception:
        pass


def get_chroma_stats() -> Dict[str, Any]:
    """取得向量庫統計資訊。"""
    try:
        collection = _get_chroma_collection()
        return {
            "total_chunks": collection.count(),
            "collection_name": COLLECTION_NAME,
            "chroma_dir": CHROMA_DIR,
        }
    except Exception as e:
        return {"total_chunks": 0, "error": str(e)}


# ── RAG 問答 ─────────────────────────────────────────────────────

def build_rag_prompt(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """根據查詢到的 chunks 建構 RAG 提示詞。"""
    context_text = "\n\n---\n\n".join(
        f"[來源：{c['filename']} 第{c['chunk_index']+1}段]\n{c['text']}"
        for c in context_chunks
    )
    return (
        f"請根據以下文件內容回答問題。\n\n"
        f"【文件內容】\n{context_text}\n\n"
        f"【問題】\n{question}\n\n"
        f"請用繁體中文給出詳細、準確的回答，若文件內容不足以回答請說明。"
    )
