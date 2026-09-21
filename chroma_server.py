from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import base64
import os
from typing import Optional

app = FastAPI(title="Local Chroma Server for LangChain")

# lazy import rag_utils to provide helpful error if missing
try:
    import rag_utils
except Exception as e:
    rag_utils = None

class IndexRequest(BaseModel):
    id: str
    filename: str
    content_base64: str

class SearchRequest(BaseModel):
    q: str
    n: Optional[int] = 5

class DeleteRequest(BaseModel):
    id: str

@app.get('/health')
async def health():
    return {"ok": True}

@app.post('/index')
async def index(req: IndexRequest):
    if rag_utils is None:
        raise HTTPException(status_code=500, detail="rag_utils not available; install Python deps")
    try:
        doc_id = int(req.id)
    except Exception:
        # try hashing
        doc_id = abs(hash(req.id)) % (10 ** 9)
    data = base64.b64decode(req.content_base64)
    text = rag_utils.extract_text_from_file(data, req.filename)
    chunks = rag_utils.split_text_into_chunks(text)
    count = rag_utils.index_document(doc_id, req.filename, chunks)
    return {"ok": True, "indexed_chunks": count, "doc_id": doc_id}

@app.post('/search')
async def search(req: SearchRequest):
    if rag_utils is None:
        raise HTTPException(status_code=500, detail="rag_utils not available; install Python deps")
    hits = rag_utils.query_knowledge(req.q, n_results=req.n)
    return {"ok": True, "results": hits}

@app.post('/delete')
async def delete(req: DeleteRequest):
    if rag_utils is None:
        raise HTTPException(status_code=500, detail="rag_utils not available; install Python deps")
    try:
        doc_id = int(req.id)
    except Exception:
        doc_id = abs(hash(req.id)) % (10 ** 9)
    rag_utils.delete_document_from_chroma(doc_id)
    return {"ok": True}

@app.get('/stats')
async def stats():
    if rag_utils is None:
        raise HTTPException(status_code=500, detail="rag_utils not available; install Python deps")
    return {"ok": True, "stats": rag_utils.get_chroma_stats()}
