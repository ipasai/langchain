"""
doc_analyzer.py
智慧文件分析模組
- 上傳任意格式檔案（PDF / DOCX / XLSX / CSV / TXT / 程式碼…）
- AI 分析 → 摘要 + 心智圖（Mermaid 語法渲染）
- RAG 向量化 → 存入 ChromaDB 供後續問答強化
- 知識模式：重點摘要 + TTS 語音朗讀
- 考題模式：AI 出題 + 選擇題作答 + 計分
- 知識反饋：將 RAG 問答結果寫回系統知識庫
"""

from __future__ import annotations

import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import HumanMessage

from db_utils import (
    delete_rag_document,
    list_rag_documents,
    list_quiz_records,
    list_rag_knowledge,
    save_quiz_record,
    save_rag_document,
    save_rag_knowledge,
    save_quiz_bank_questions,
    list_quiz_bank_sets,
    list_quiz_bank_questions,
    delete_quiz_bank_set,
    delete_quiz_bank_question,
    save_doc_unit,
    list_doc_units,
    update_doc_unit_teaching,
    update_doc_unit_quiz,
    delete_doc_units,
    save_unit_quiz_record,
    list_unit_quiz_records,
)
from llm_factory import LLMFactory
from rag_utils import (
    build_rag_prompt,
    compute_hash,
    delete_document_from_chroma,
    extract_text_from_file,
    get_chroma_stats,
    index_document,
    query_knowledge,
    split_text_into_chunks,
)

# ── 樣式常數 ──────────────────────────────────────────────────────
_CARD = (
    "background:linear-gradient(135deg,#f8faff 0%,#eef2ff 100%);"
    "border:1.5px solid #c7d2fe;border-radius:16px;"
    "padding:1.2rem 1.4rem;margin-bottom:0.8rem;"
    "box-shadow:0 4px 16px rgba(99,102,241,0.08);"
)
_HDR = (
    "font-size:1.15rem;font-weight:700;color:#4f46e5;"
    "margin-bottom:0.3rem;letter-spacing:0.01em;"
)
_DIV = "<hr style='border:none;border-top:1.5px solid #e0e7ff;margin:1.4rem 0;'/>"

ALLOWED_TYPES = [
    "pdf", "docx", "doc", "txt", "md",
    "xlsx", "xls", "csv",
    "py", "js", "ts", "java", "c", "cpp", "go", "rs",
    "json", "yaml", "yml", "xml", "html", "css", "sh",
]


# ── Helper ────────────────────────────────────────────────────────

def _hdr(icon: str, title: str) -> None:
    st.markdown(f"<div style='{_HDR}'>{icon} {title}</div>", unsafe_allow_html=True)


def _div() -> None:
    st.markdown(_DIV, unsafe_allow_html=True)


def _card(html: str) -> None:
    st.markdown(f"<div style='{_CARD}'>{html}</div>", unsafe_allow_html=True)


def _get_llm():
    return LLMFactory.get_llm(
        st.session_state.provider,
        model_name=st.session_state.model,
        temperature=0.4,
    )


def _tts_component(text: str, height: int = 60) -> None:
    """
    瀏覽器 TTS 朗讀 component，含播放／停止切換。
    文字透過 data-text 屬性傳入，避免長文本/特殊字元造成 JS 語法錯誤。
    """
    import html as _html
    safe_attr = _html.escape(text, quote=True)
    components.html(
        f"""<!DOCTYPE html><html><head>
        <meta charset="utf-8">
        <style>
          body {{ margin:0; padding:4px; font-family:sans-serif; background:transparent; }}
          .btn {{
            border:none; border-radius:20px;
            padding:0.3rem 1.1rem; font-size:0.85rem;
            cursor:pointer; font-weight:600;
            box-shadow:0 2px 8px rgba(99,102,241,0.25);
            transition:opacity 0.15s;
          }}
          .btn:active {{ opacity:0.75; }}
          #playBtn  {{ background:linear-gradient(135deg,#6366f1,#818cf8); color:#fff; }}
          #stopBtn  {{ background:linear-gradient(135deg,#ef4444,#f87171); color:#fff; display:none; }}
        </style>
        </head><body>
        <button id="playBtn" class="btn" data-text="{safe_attr}">🔊 朗讀內容</button>
        <button id="stopBtn" class="btn">⏹ 停止朗讀</button>
        <script>
          (function() {{
            var synth = window.speechSynthesis || (window.parent && window.parent.speechSynthesis);
            var playBtn = document.getElementById('playBtn');
            var stopBtn = document.getElementById('stopBtn');

            function setSpeaking(on) {{
              playBtn.style.display = on ? 'none'   : 'inline-block';
              stopBtn.style.display = on ? 'inline-block' : 'none';
            }}

            playBtn.addEventListener('click', function() {{
              if (!synth) {{ alert('您的瀏覽器不支援語音合成'); return; }}
              synth.cancel();
              var u = new SpeechSynthesisUtterance(this.getAttribute('data-text'));
              u.lang = 'zh-TW';
              u.rate = 0.9;
              u.onstart = function() {{ setSpeaking(true); }};
              u.onend   = function() {{ setSpeaking(false); }};
              u.onerror = function() {{ setSpeaking(false); }};
              synth.speak(u);
            }});

            stopBtn.addEventListener('click', function() {{
              if (synth) synth.cancel();
              setSpeaking(false);
            }});
          }})();
        </script>
        </body></html>""",
        height=height,
    )


def _render_mindmap(mermaid_code: str) -> None:
    """
    用 Mermaid 渲染心智圖。
    - 動態建立 script 標籤，確保在 iframe sandbox 內可執行
    - 清理常見非法字元，防止 Mermaid 解析失敗
    - 提供原始語法展示作為 fallback
    """
    # ── 清理 AI 產生的 mermaid 語法 ───────────────────────────
    code = mermaid_code.strip()
    # 移除 markdown 包裹
    code = re.sub(r'^```[a-z]*\s*', '', code, flags=re.MULTILINE)
    code = re.sub(r'```\s*$', '', code, flags=re.MULTILINE)
    code = code.strip()
    # 移除節點文字中的括號類字元（Mermaid mindmap 節點不支援圓括號外其他括號）
    # 保留 root((...)) 的雙括號，其他節點的括號改為空格
    lines = []
    for line in code.splitlines():
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        # root 節點保留原樣
        if stripped.lower().startswith("root"):
            lines.append(line)
        else:
            # 移除方括號、大括號、引號，避免 Mermaid 解析錯誤
            cleaned = re.sub(r'[\[\]{}"\'`]', '', stripped)
            # 節點文字超過 20 字截斷
            if len(cleaned) > 30:
                cleaned = cleaned[:30] + "…"
            lines.append(indent + cleaned)
    code = "\n".join(lines)

    # 對整段程式碼做 HTML 實體編碼，放進 <pre> 再用 JS 讀出
    import html as _html
    safe_code = _html.escape(code, quote=True)

    components.html(
        f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin:0; padding:8px; background:#f8faff; font-family:sans-serif; }}
    #mermaid-container {{ width:100%; min-height:400px; }}
    #error-box {{
      display:none; background:#fef2f2; border:1px solid #fca5a5;
      border-radius:8px; padding:0.8rem; font-size:0.82rem; color:#991b1b;
      white-space:pre-wrap; word-break:break-all;
    }}
    #fallback {{
      display:none; background:#f8faff; border:1px solid #c7d2fe;
      border-radius:8px; padding:0.8rem; font-size:0.8rem; color:#374151;
      white-space:pre-wrap; font-family:monospace;
    }}
    .toggle-btn {{
      font-size:0.78rem; color:#6366f1; cursor:pointer;
      background:none; border:none; text-decoration:underline; margin-top:4px;
    }}
  </style>
</head>
<body>
  <div id="mermaid-container">
    <pre id="mermaid-src" class="mermaid">{safe_code}</pre>
  </div>
  <div id="error-box"></div>
  <button class="toggle-btn" id="toggleBtn" style="display:none"
    onclick="document.getElementById('fallback').style.display='block';
             this.style.display='none';">查看原始語法</button>
  <pre id="fallback">{safe_code}</pre>

  <script>
    (function() {{
      // 動態載入 Mermaid，避免 CSP 問題
      var script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js';
      script.onload = function() {{
        try {{
          mermaid.initialize({{
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            mindmap: {{ padding: 20 }}
          }});
          mermaid.run({{
            nodes: [document.getElementById('mermaid-src')],
            suppressErrors: false
          }}).then(function() {{
            // 成功渲染
          }}).catch(function(err) {{
            showFallback(err.toString());
          }});
        }} catch(e) {{
          showFallback(e.toString());
        }}
      }};
      script.onerror = function() {{
        showFallback('無法載入 Mermaid CDN，請確認網路連線。');
      }};
      document.head.appendChild(script);

      function showFallback(msg) {{
        document.getElementById('error-box').style.display = 'block';
        document.getElementById('error-box').textContent = '⚠️ 心智圖渲染失敗：' + msg;
        document.getElementById('toggleBtn').style.display = 'inline-block';
        document.getElementById('fallback').style.display = 'block';
        document.getElementById('mermaid-container').style.display = 'none';
      }}
    }})();
  </script>
</body>
</html>""",
        height=500,
        scrolling=True,
    )


# ── AI 分析函式 ───────────────────────────────────────────────────

def _ai_summarize(text: str, filename: str) -> str:
    """產生文件摘要。"""
    llm = _get_llm()
    prompt = (
        f"請分析以下文件「{filename}」的內容，用繁體中文提供：\n"
        "1. 核心主題（1-2句）\n"
        "2. 主要內容摘要（3-5個重點，每點用•開頭）\n"
        "3. 文件類型判斷（學術論文/技術文件/考試題目/一般知識/程式碼/其他）\n\n"
        f"文件內容（前3000字）：\n{text[:3000]}"
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    return resp.content.strip()


def _ai_mindmap(text: str, filename: str) -> str:
    """產生 Mermaid mindmap 語法。"""
    llm = _get_llm()
    prompt = (
        f"請根據文件「{filename}」的內容，產生一個 Mermaid mindmap 心智圖。\n\n"
        "【嚴格規則】\n"
        "1. 第一行必須是 mindmap，第二行必須是 root((主題名稱))\n"
        "2. 使用空格縮排（每層 2 個空格），不要用 Tab\n"
        "3. 最多 3 層，每層最多 5 個節點\n"
        "4. 節點文字只能用純文字，不超過 15 個字\n"
        "5. 節點文字不可包含：( ) [ ] { } \" ' ` / \\ | < > & % @ # 等特殊符號\n"
        "6. 根節點用雙括號 root((主題))，其他節點直接寫文字不加任何括號\n"
        "7. 只輸出 mermaid 程式碼，不要 ``` 標記，不要任何說明\n\n"
        "範例：\n"
        "mindmap\n"
        "  root((機器學習))\n"
        "    監督式學習\n"
        "      分類\n"
        "      迴歸\n"
        "    非監督式學習\n"
        "      聚類\n"
        "    深度學習\n"
        "      神經網路\n\n"
        f"文件內容（前2000字）：\n{text[:2000]}"
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    raw = resp.content.strip()
    # 移除 markdown 包裹
    raw = re.sub(r'^```[a-z]*\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
    return raw.strip()


def _ai_detect_doc_type(text: str) -> str:
    """自動偵測文件類型：quiz / knowledge。"""
    lower = text[:1000].lower()
    quiz_keywords = ["題", "答案", "選項", "（a）", "（b）", "（c）", "( a)", "( b)",
                     "q1", "q2", "question", "answer", "correct", "選擇題", "填空"]
    score = sum(1 for kw in quiz_keywords if kw in lower)
    return "quiz" if score >= 3 else "knowledge"


def _ai_generate_knowledge_points(text: str, filename: str) -> List[Dict[str, str]]:
    """從文件中提取知識點，每個知識點含標題與說明。"""
    llm = _get_llm()
    prompt = (
        f"請從以下文件「{filename}」中提取 5-8 個核心知識點。\n"
        "每個知識點格式（嚴格 JSON 陣列）：\n"
        '[{"title":"知識點標題","content":"詳細說明（2-4句）"}]\n'
        "只輸出 JSON，不要任何說明。\n\n"
        f"文件內容（前4000字）：\n{text[:4000]}"
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    raw = resp.content.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
    try:
        return json.loads(raw)
    except Exception:
        # fallback：嘗試用正則抓取
        items = re.findall(r'"title"\s*:\s*"([^"]+)".*?"content"\s*:\s*"([^"]+)"', raw, re.DOTALL)
        return [{"title": t, "content": c} for t, c in items] if items else []


def _ai_generate_quiz(text: str, filename: str, count: int = 5) -> List[Dict[str, Any]]:
    """從文件內容產生選擇題。"""
    llm = _get_llm()
    prompt = (
        f"請根據文件「{filename}」內容出 {count} 道四選一選擇題。\n"
        "嚴格輸出 JSON 陣列格式，每題包含：\n"
        "question（題目）、options（4個選項陣列）、answer（正確選項，如 A/B/C/D）、"
        "explanation（解題說明）\n"
        "範例：\n"
        '[{"question":"...","options":["A. 選項一","B. 選項二","C. 選項三","D. 選項四"],'
        '"answer":"A","explanation":"..."}]\n'
        "只輸出 JSON，不要 markdown。\n\n"
        f"文件內容（前4000字）：\n{text[:4000]}"
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    raw = resp.content.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
    try:
        questions = json.loads(raw)
        # 正規化 options 欄位
        for q in questions:
            if "options" not in q or not isinstance(q["options"], list):
                q["options"] = ["A. 選項一", "B. 選項二", "C. 選項三", "D. 選項四"]
        return questions
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# 主頁面類別
# ═══════════════════════════════════════════════════════════════

class DocAnalyzerPage:
    def __init__(self):
        pass

    def render(self):
        st.markdown(
            "<h2 style='color:#4f46e5;margin-bottom:0.1rem;'>📄 智慧文件分析</h2>"
            "<p style='color:#6b7280;font-size:0.95rem;margin-top:0;'>"
            "上傳任意文件 → AI 分析 · 心智圖 · 向量知識庫 · 知識朗讀 · 考題測驗</p>",
            unsafe_allow_html=True,
        )

        # session state 初始化
        defaults = {
            "doc_text": "",
            "doc_filename": "",
            "doc_id": None,
            "doc_summary": "",
            "doc_mindmap": "",
            "doc_type": "knowledge",
            "doc_knowledge_points": [],
            "doc_quiz_questions": [],
            "doc_quiz_answers": {},
            "doc_quiz_submitted": False,
            "doc_quiz_score": None,
            "doc_rag_answer": "",
            "doc_rag_question": "",
            "doc_tab": "upload",
            # 題庫測驗狀態
            "bank_quiz_questions": [],
            "bank_quiz_answers": {},
            "bank_quiz_submitted": False,
            "bank_quiz_score": None,
            "bank_quiz_set_name": "",
        }
        for k, v in defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v

        # 頂部 Tab
        tab_upload, tab_knowledge, tab_quiz, tab_rag, tab_bank, tab_history = st.tabs([
            "📤 上傳分析", "🧠 知識模式", "📝 考題測驗", "🔍 RAG 問答", "🗂️ 題庫管理", "📊 歷史紀錄"
        ])

        with tab_upload:
            self._render_upload_section()
        with tab_knowledge:
            self._render_knowledge_section()
        with tab_quiz:
            self._render_quiz_section()
        with tab_rag:
            self._render_rag_section()
        with tab_bank:
            self._render_quiz_bank_section()
        with tab_history:
            self._render_history_section()

    # ── 上傳 & 分析 ───────────────────────────────────────────

    def _render_upload_section(self):
        _hdr("📤", "上傳文件")
        st.caption("支援格式：PDF · DOCX · XLSX · CSV · TXT · MD · 程式碼（py/js/java…）等")

        uploaded = st.file_uploader(
            "選擇或拖放檔案",
            type=ALLOWED_TYPES,
            label_visibility="collapsed",
        )

        if uploaded:
            file_bytes = uploaded.read()
            filename = uploaded.name

            col_info, col_btn = st.columns([3, 1])
            with col_info:
                size_kb = len(file_bytes) / 1024
                st.markdown(
                    f"<div style='background:#f0fdf4;border:1px solid #86efac;"
                    f"border-radius:10px;padding:0.6rem 1rem;font-size:0.9rem;'>"
                    f"📎 <b>{filename}</b> &nbsp;·&nbsp; {size_kb:.1f} KB</div>",
                    unsafe_allow_html=True,
                )
            with col_btn:
                do_analyze = st.button(
                    "🚀 開始分析",
                    type="primary",
                    use_container_width=True,
                    disabled=st.session_state.is_processing,
                )

            if do_analyze:
                st.session_state.is_processing = True
                st.rerun()

            if st.session_state.is_processing and uploaded:
                with st.spinner("讀取文件內容…"):
                    try:
                        text = extract_text_from_file(file_bytes, filename)
                    except Exception as e:
                        st.error(f"❌ 讀取失敗：{e}")
                        return

                if not text.strip():
                    st.warning("⚠️ 文件內容為空，請確認檔案格式是否正確。")
                    return

                content_hash = compute_hash(text)
                doc_type = _ai_detect_doc_type(text)

                with st.spinner("AI 分析中（摘要 + 心智圖）…"):
                    try:
                        summary = _ai_summarize(text, filename)
                        mindmap = _ai_mindmap(text, filename)
                    except Exception as e:
                        st.error(f"❌ AI 分析失敗：{e}")
                        return

                with st.spinner("向量化並建立知識庫…"):
                    try:
                        chunks = split_text_into_chunks(text)
                        doc_id = save_rag_document(
                            filename=filename,
                            file_type=Path(filename).suffix.lower().lstrip("."),
                            content_hash=content_hash,
                            chunk_count=len(chunks),
                            doc_type=doc_type,
                            summary=summary,
                            mindmap_json=mindmap,
                            db_path=st.session_state.db_path,
                        )
                        indexed = index_document(doc_id, filename, chunks)
                    except Exception as e:
                        st.error(f"❌ 向量化失敗：{e}")
                        return

                # 儲存到 session
                st.session_state.doc_text = text
                st.session_state.doc_filename = filename
                st.session_state.doc_id = doc_id
                st.session_state.doc_summary = summary
                st.session_state.doc_mindmap = mindmap
                st.session_state.doc_type = doc_type
                st.session_state.doc_knowledge_points = []
                st.session_state.doc_quiz_questions = []
                st.session_state.doc_quiz_answers = {}
                st.session_state.doc_quiz_submitted = False
                st.session_state.doc_quiz_score = None

                st.success(f"✅ 分析完成！已建立 {indexed} 個知識向量塊。")
                st.rerun()

        # 顯示分析結果
        if st.session_state.doc_filename:
            _div()
            _hdr("📋", "分析結果")

            doc_type_label = "🎯 考題類型" if st.session_state.doc_type == "quiz" else "📚 知識類型"
            st.markdown(
                f"<div style='background:#ede9fe;border-radius:10px;"
                f"padding:0.5rem 1rem;font-size:0.9rem;margin-bottom:0.7rem;'>"
                f"<b>📎 {st.session_state.doc_filename}</b>"
                f"&nbsp;·&nbsp;{doc_type_label}"
                f"&nbsp;·&nbsp;🔢 {len(split_text_into_chunks(st.session_state.doc_text))} 個向量塊"
                f"</div>",
                unsafe_allow_html=True,
            )

            with st.expander("📝 AI 摘要", expanded=True):
                st.markdown(st.session_state.doc_summary)
                _tts_component(st.session_state.doc_summary)

            with st.expander("🗺️ 心智圖", expanded=False):
                if st.session_state.doc_mindmap:
                    _render_mindmap(st.session_state.doc_mindmap)
                else:
                    st.info("心智圖尚未生成。")

            # 向量庫統計
            stats = get_chroma_stats()
            st.caption(
                f"📦 向量庫：共 {stats.get('total_chunks', 0)} 個 chunks"
                f"（存放於 {stats.get('chroma_dir', '')}）"
            )

        # 已索引文件清單
        _div()
        _hdr("📚", "已索引文件")
        docs = list_rag_documents(db_path=st.session_state.db_path)
        if not docs:
            st.info("尚無已分析的文件，請先上傳。")
        else:
            for doc in docs:
                c1, c2, c3 = st.columns([5, 2, 1])
                with c1:
                    badge = "🎯 考題" if doc["doc_type"] == "quiz" else "📚 知識"
                    st.markdown(
                        f"<div style='padding:0.3rem 0;'>"
                        f"<b style='color:#4f46e5;'>{doc['filename']}</b>"
                        f" <span style='color:#9ca3af;font-size:0.82rem;'>"
                        f"{badge} · {doc['chunk_count']} chunks · {doc['created_at'][:10]}"
                        f"</span></div>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("📂 載入", key=f"load_{doc['id']}"):
                        st.session_state.doc_id = doc["id"]
                        st.session_state.doc_filename = doc["filename"]
                        st.session_state.doc_summary = doc["summary"]
                        st.session_state.doc_mindmap = doc["mindmap_json"]
                        st.session_state.doc_type = doc["doc_type"]
                        st.session_state.doc_text = ""
                        st.session_state.doc_knowledge_points = []
                        st.session_state.doc_quiz_questions = []
                        st.session_state.doc_quiz_answers = {}
                        st.session_state.doc_quiz_submitted = False
                        st.session_state.doc_quiz_score = None
                        st.success(f"已載入 {doc['filename']}")
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_doc_{doc['id']}"):
                        delete_rag_document(doc["id"], db_path=st.session_state.db_path)
                        delete_document_from_chroma(doc["id"])
                        st.success("已刪除")
                        st.rerun()

    # ── 知識模式 ──────────────────────────────────────────────

    def _render_knowledge_section(self):
        _hdr("🧠", "知識模式")
        if not st.session_state.doc_filename:
            st.info("請先在「上傳分析」分頁上傳並分析文件。")
            return

        st.caption(f"文件：{st.session_state.doc_filename}")

        # 顯示摘要與 TTS
        if st.session_state.doc_summary:
            st.markdown(
                "<div style='font-weight:600;color:#4f46e5;margin-bottom:0.3rem;'>📋 文件摘要</div>",
                unsafe_allow_html=True,
            )
            st.markdown(st.session_state.doc_summary)
            _tts_component(st.session_state.doc_summary)
            _div()

        # 心智圖
        if st.session_state.doc_mindmap:
            with st.expander("🗺️ 心智圖", expanded=False):
                _render_mindmap(st.session_state.doc_mindmap)
            _div()

        # 知識點產生
        _hdr("💡", "核心知識點")
        if not st.session_state.doc_knowledge_points:
            if not st.session_state.doc_text:
                st.warning("請重新上傳文件以載入內容，或使用 RAG 問答。")
            else:
                if st.button("🤖 AI 提取知識點", type="primary", use_container_width=True):
                    with st.spinner("AI 提取知識點中…"):
                        try:
                            kps = _ai_generate_knowledge_points(
                                st.session_state.doc_text,
                                st.session_state.doc_filename,
                            )
                            st.session_state.doc_knowledge_points = kps
                            st.rerun()
                        except Exception as e:
                            st.error(f"提取失敗：{e}")
        else:
            kps = st.session_state.doc_knowledge_points
            for i, kp in enumerate(kps, 1):
                with st.expander(f"{i}. {kp.get('title', '知識點')}"):
                    content = kp.get("content", "")
                    st.markdown(content)
                    col_tts, col_rag = st.columns([1, 1])
                    with col_tts:
                        _tts_component(content, height=52)
                    with col_rag:
                        if st.button("💾 存入知識庫", key=f"save_kp_{i}"):
                            save_rag_knowledge(
                                question=kp.get("title", ""),
                                answer=content,
                                doc_id=st.session_state.doc_id,
                                db_path=st.session_state.db_path,
                            )
                            st.success("已儲存到知識庫 ✓")

            if st.button("🔄 重新提取", use_container_width=True):
                st.session_state.doc_knowledge_points = []
                st.rerun()

    # ── 考題測驗 ──────────────────────────────────────────────

    def _render_quiz_section(self):
        _hdr("📝", "考題測驗")
        if not st.session_state.doc_filename:
            st.info("請先在「上傳分析」分頁上傳並分析文件。")
            return

        st.caption(f"文件：{st.session_state.doc_filename}")

        # 出題設定
        if not st.session_state.doc_quiz_questions:
            if not st.session_state.doc_text:
                st.warning("請重新上傳文件以載入原始內容後再出題。")
                return
            col_n, col_btn = st.columns([2, 2])
            with col_n:
                quiz_count = st.number_input("出題數量", min_value=3, max_value=15, value=5, step=1)
            with col_btn:
                st.markdown("<div style='height:1.8rem;'></div>", unsafe_allow_html=True)
                if st.button("🤖 AI 出題", type="primary", use_container_width=True):
                    with st.spinner("AI 正在根據文件出題…"):
                        try:
                            questions = _ai_generate_quiz(
                                st.session_state.doc_text,
                                st.session_state.doc_filename,
                                count=quiz_count,
                            )
                            if not questions:
                                st.error("AI 出題失敗，請重試或換一個文件。")
                                return
                            st.session_state.doc_quiz_questions = questions
                            st.session_state.doc_quiz_answers = {}
                            st.session_state.doc_quiz_submitted = False
                            st.session_state.doc_quiz_score = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"出題失敗：{e}")
            return

        questions = st.session_state.doc_quiz_questions
        total = len(questions)

        # 考試進行中
        if not st.session_state.doc_quiz_submitted:
            st.markdown(
                f"<div style='background:#ede9fe;border-radius:10px;padding:0.5rem 1rem;"
                f"font-size:0.9rem;margin-bottom:0.8rem;'>"
                f"共 <b>{total}</b> 題，請作答後提交。</div>",
                unsafe_allow_html=True,
            )

            # 作答前也可儲存至題庫
            with st.expander("💾 儲存這批題目至題庫"):
                with st.form("save_bank_before_quiz"):
                    default_set_pre = (
                        f"{st.session_state.doc_filename[:20]}_"
                        f"{datetime.utcnow().strftime('%m%d_%H%M')}"
                    )
                    set_name_pre = st.text_input("題組名稱", value=default_set_pre)
                    if st.form_submit_button("💾 儲存", use_container_width=True):
                        saved = save_quiz_bank_questions(
                            set_name=set_name_pre.strip() or default_set_pre,
                            questions=questions,
                            filename=st.session_state.doc_filename,
                            doc_id=st.session_state.doc_id,
                            db_path=st.session_state.db_path,
                        )
                        st.success(f"✅ 已儲存 {saved} 道題目至題庫「{set_name_pre.strip()}」")
            for i, q in enumerate(questions):
                with st.container():
                    st.markdown(
                        f"<div style='font-weight:600;color:#1e1b4b;margin:0.8rem 0 0.3rem;'>"
                        f"Q{i+1}. {q.get('question','')}</div>",
                        unsafe_allow_html=True,
                    )
                    opts = q.get("options", [])
                    chosen = st.radio(
                        f"q_{i}",
                        options=opts,
                        key=f"quiz_radio_{i}",
                        label_visibility="collapsed",
                    )
                    st.session_state.doc_quiz_answers[i] = chosen

            _div()
            if st.button("📋 提交答案", type="primary", use_container_width=True):
                correct = 0
                for i, q in enumerate(questions):
                    ans_letter = q.get("answer", "A").strip().upper()
                    user_choice = st.session_state.doc_quiz_answers.get(i, "")
                    # 比對選項首字母
                    user_letter = user_choice[0].upper() if user_choice else ""
                    if user_letter == ans_letter:
                        correct += 1
                st.session_state.doc_quiz_submitted = True
                st.session_state.doc_quiz_score = correct
                # 儲存紀錄
                answers_snapshot = {
                    str(i): {
                        "question": q.get("question", ""),
                        "user": st.session_state.doc_quiz_answers.get(i, ""),
                        "answer": q.get("answer", ""),
                        "correct": (st.session_state.doc_quiz_answers.get(i, "")[:1].upper()
                                    == q.get("answer", "A").strip().upper()),
                        "explanation": q.get("explanation", ""),
                    }
                    for i, q in enumerate(questions)
                }
                save_quiz_record(
                    total_questions=total,
                    correct_count=correct,
                    answers_json=json.dumps(answers_snapshot, ensure_ascii=False),
                    doc_id=st.session_state.doc_id,
                    filename=st.session_state.doc_filename,
                    db_path=st.session_state.db_path,
                )
                st.rerun()

        # 顯示成績
        else:
            correct = st.session_state.doc_quiz_score
            pct = round(correct / total * 100) if total else 0
            badge_color = "#10b981" if pct >= 80 else "#f59e0b" if pct >= 60 else "#ef4444"
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#f0fdf4,#dcfce7);"
                f"border:2px solid #86efac;border-radius:16px;padding:1.2rem 1.4rem;"
                f"text-align:center;margin-bottom:1rem;'>"
                f"<div style='font-size:2.5rem;font-weight:800;color:{badge_color};'>{pct}%</div>"
                f"<div style='color:#374151;'>答對 {correct} / {total} 題</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # 逐題解析
            for i, q in enumerate(questions):
                ans_letter = q.get("answer", "A").strip().upper()
                user_choice = st.session_state.doc_quiz_answers.get(i, "")
                user_letter = user_choice[0].upper() if user_choice else ""
                is_correct = user_letter == ans_letter
                icon = "✅" if is_correct else "❌"
                bg = "#f0fdf4" if is_correct else "#fef2f2"
                border = "#86efac" if is_correct else "#fca5a5"
                opts_html = "".join(
                    f"<div style='color:{'#15803d' if opt.startswith(ans_letter) else '#374151'};'>"
                    f"{'★ ' if opt.startswith(ans_letter) else '　'}{opt}</div>"
                    for opt in q.get("options", [])
                )
                st.markdown(
                    f"<div style='background:{bg};border:1.5px solid {border};"
                    f"border-radius:12px;padding:0.9rem 1.1rem;margin-bottom:0.7rem;'>"
                    f"<div style='font-weight:600;'>{icon} Q{i+1}. {q.get('question','')}</div>"
                    f"<div style='margin:0.4rem 0 0.2rem;font-size:0.88rem;'>{opts_html}</div>"
                    f"<div style='font-size:0.85rem;color:#374151;'>"
                    f"你的答案：{user_choice} &nbsp;·&nbsp; 正確答案：{ans_letter}</div>"
                    f"<div style='font-size:0.83rem;color:#6b7280;margin-top:0.3rem;'>"
                    f"💡 {q.get('explanation','')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # 儲存至題庫 + 重新出題
            _div()
            save_col, retry_col = st.columns(2)
            with save_col:
                with st.form("save_to_bank_form"):
                    default_set = (
                        f"{st.session_state.doc_filename[:20]}_"
                        f"{datetime.utcnow().strftime('%m%d_%H%M')}"
                    )
                    set_name_input = st.text_input(
                        "題組名稱", value=default_set, key="bank_set_name_input"
                    )
                    if st.form_submit_button("💾 儲存至題庫", use_container_width=True):
                        saved = save_quiz_bank_questions(
                            set_name=set_name_input.strip() or default_set,
                            questions=questions,
                            filename=st.session_state.doc_filename,
                            doc_id=st.session_state.doc_id,
                            db_path=st.session_state.db_path,
                        )
                        st.success(f"✅ 已儲存 {saved} 道題目至題庫「{set_name_input.strip()}」")
            with retry_col:
                st.markdown("<div style='height:3.5rem;'></div>", unsafe_allow_html=True)
                if st.button("🔄 重新出題", use_container_width=True):
                    st.session_state.doc_quiz_questions = []
                    st.session_state.doc_quiz_answers = {}
                    st.session_state.doc_quiz_submitted = False
                    st.session_state.doc_quiz_score = None
                    st.rerun()

    def _render_quiz_bank_section(self):
        _hdr("🗂️", "題庫管理")
        st.caption("所有 AI 出題結果都可儲存至此，隨時取出重新測驗。")

        sets = list_quiz_bank_sets(db_path=st.session_state.db_path)

        if not sets:
            st.info("📭 題庫目前是空的。請先在「📝 考題測驗」分頁出題並點擊「💾 儲存至題庫」。")
            return

        # ── 模式切換：瀏覽 / 測驗 ────────────────────────────────
        mode = st.radio(
            "功能",
            ["📚 瀏覽題庫", "🎯 從題庫測驗"],
            horizontal=True,
            key="bank_mode_radio",
        )

        if mode == "📚 瀏覽題庫":
            self._render_bank_browse(sets)
        else:
            self._render_bank_exam(sets)

    def _render_bank_browse(self, sets: list):
        """瀏覽並管理題庫組別與題目。"""
        set_names = [s["set_name"] for s in sets]
        selected_set = st.selectbox(
            "選擇題組",
            options=set_names,
            format_func=lambda n: next(
                f"{n}（{s['total']} 題 · {s['filename']} · {s['created_at'][:10]}）"
                for s in sets if s["set_name"] == n
            ),
            key="bank_browse_select",
        )

        if not selected_set:
            return

        questions = list_quiz_bank_questions(set_name=selected_set, db_path=st.session_state.db_path)
        set_info = next((s for s in sets if s["set_name"] == selected_set), {})

        # 組別資訊
        st.markdown(
            f"<div style='background:#ede9fe;border-radius:10px;padding:0.5rem 1rem;"
            f"font-size:0.9rem;margin-bottom:0.7rem;'>"
            f"📦 <b>{selected_set}</b> &nbsp;·&nbsp; 共 {len(questions)} 題"
            f"&nbsp;·&nbsp; 來源：{set_info.get('filename','—')}"
            f"&nbsp;·&nbsp; {set_info.get('created_at','')[:10]}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # 刪除整組按鈕
        if st.button(f"🗑️ 刪除整組「{selected_set}」", key="del_bank_set"):
            deleted = delete_quiz_bank_set(selected_set, db_path=st.session_state.db_path)
            st.success(f"已刪除 {deleted} 道題目")
            st.rerun()

        _div()

        # 逐題顯示
        for i, q in enumerate(questions, 1):
            with st.expander(f"Q{i}. {q['question'][:60]}{'…' if len(q['question'])>60 else ''}"):
                opts_html = "".join(
                    f"<div style='color:{'#15803d' if opt.startswith(q['answer']) else '#374151'};'>"
                    f"{'✓ ' if opt.startswith(q['answer']) else '　'}{opt}</div>"
                    for opt in q.get("options", [])
                )
                st.markdown(
                    f"<div style='font-size:0.92rem;'>{q['question']}</div>"
                    f"<div style='margin:0.4rem 0;font-size:0.88rem;'>{opts_html}</div>"
                    f"<div style='font-size:0.83rem;color:#6b7280;'>💡 {q.get('explanation','')}</div>",
                    unsafe_allow_html=True,
                )
                if st.button("🗑️ 刪除此題", key=f"del_q_{q['id']}"):
                    delete_quiz_bank_question(q["id"], db_path=st.session_state.db_path)
                    st.success("已刪除")
                    st.rerun()

    def _render_bank_exam(self, sets: list):
        """從題庫選題並進行測驗。"""
        set_names = [s["set_name"] for s in sets]

        # ── 組題設定（尚未開始測驗）────────────────────────────
        if not st.session_state.bank_quiz_questions:
            col_set, col_n = st.columns([3, 1])
            with col_set:
                exam_sets = st.multiselect(
                    "選擇題組（可多選混合）",
                    options=set_names,
                    default=[set_names[0]] if set_names else [],
                    key="bank_exam_sets",
                )
            with col_n:
                max_q = sum(
                    s["total"] for s in sets if s["set_name"] in exam_sets
                ) if exam_sets else 0
                exam_count = st.number_input(
                    "出題數量",
                    min_value=1,
                    max_value=max(max_q, 1),
                    value=min(10, max(max_q, 1)),
                    step=1,
                    key="bank_exam_count",
                )

            shuffle = st.checkbox("🔀 隨機排序題目", value=True, key="bank_exam_shuffle")

            if st.button("🚀 開始測驗", type="primary", use_container_width=True):
                if not exam_sets:
                    st.warning("請至少選擇一個題組。")
                    return
                # 從選定題組抓題
                all_qs: list = []
                for sn in exam_sets:
                    all_qs.extend(list_quiz_bank_questions(set_name=sn, db_path=st.session_state.db_path))
                if shuffle:
                    import random as _random
                    _random.shuffle(all_qs)
                selected_qs = all_qs[:exam_count]
                if not selected_qs:
                    st.error("題組內無題目，請先儲存題目。")
                    return
                st.session_state.bank_quiz_questions = selected_qs
                st.session_state.bank_quiz_answers = {}
                st.session_state.bank_quiz_submitted = False
                st.session_state.bank_quiz_score = None
                st.session_state.bank_quiz_set_name = "、".join(exam_sets)
                st.rerun()
            return

        # ── 測驗進行中 ───────────────────────────────────────────
        questions = st.session_state.bank_quiz_questions
        total = len(questions)

        if not st.session_state.bank_quiz_submitted:
            st.markdown(
                f"<div style='background:#ede9fe;border-radius:10px;padding:0.5rem 1rem;"
                f"font-size:0.9rem;margin-bottom:0.8rem;'>"
                f"題組：<b>{st.session_state.bank_quiz_set_name}</b>"
                f" &nbsp;·&nbsp; 共 <b>{total}</b> 題</div>",
                unsafe_allow_html=True,
            )
            for i, q in enumerate(questions):
                st.markdown(
                    f"<div style='font-weight:600;color:#1e1b4b;margin:0.8rem 0 0.3rem;'>"
                    f"Q{i+1}. {q.get('question','')}</div>",
                    unsafe_allow_html=True,
                )
                opts = q.get("options", [])
                chosen = st.radio(
                    f"bank_q_{i}",
                    options=opts,
                    key=f"bank_radio_{i}",
                    label_visibility="collapsed",
                )
                st.session_state.bank_quiz_answers[i] = chosen

            _div()
            if st.button("📋 提交答案", type="primary", use_container_width=True):
                correct = 0
                for i, q in enumerate(questions):
                    ans_letter = q.get("answer", "A").strip().upper()
                    user_choice = st.session_state.bank_quiz_answers.get(i, "")
                    if user_choice[:1].upper() == ans_letter:
                        correct += 1
                st.session_state.bank_quiz_submitted = True
                st.session_state.bank_quiz_score = correct
                # 儲存成績紀錄
                save_quiz_record(
                    total_questions=total,
                    correct_count=correct,
                    answers_json=json.dumps(
                        {str(i): {
                            "question": q.get("question", ""),
                            "user": st.session_state.bank_quiz_answers.get(i, ""),
                            "answer": q.get("answer", ""),
                            "correct": (st.session_state.bank_quiz_answers.get(i, "")[:1].upper()
                                        == q.get("answer", "A").strip().upper()),
                        } for i, q in enumerate(questions)},
                        ensure_ascii=False,
                    ),
                    filename=st.session_state.bank_quiz_set_name,
                    db_path=st.session_state.db_path,
                )
                st.rerun()

        # ── 顯示成績 ─────────────────────────────────────────────
        else:
            correct = st.session_state.bank_quiz_score
            pct = round(correct / total * 100) if total else 0
            badge_color = "#10b981" if pct >= 80 else "#f59e0b" if pct >= 60 else "#ef4444"
            grade = "🏆 優秀" if pct >= 80 else "📈 良好" if pct >= 60 else "💪 加油"

            st.markdown(
                f"<div style='background:linear-gradient(135deg,#f0fdf4,#dcfce7);"
                f"border:2px solid #86efac;border-radius:16px;padding:1.4rem 1.6rem;"
                f"text-align:center;margin-bottom:1rem;'>"
                f"<div style='font-size:2.8rem;font-weight:800;color:{badge_color};'>{pct}%</div>"
                f"<div style='font-size:1.1rem;color:#374151;'>{grade} &nbsp;·&nbsp; 答對 {correct} / {total} 題</div>"
                f"<div style='font-size:0.85rem;color:#6b7280;margin-top:0.3rem;'>"
                f"題組：{st.session_state.bank_quiz_set_name}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # 逐題解析
            for i, q in enumerate(questions):
                ans_letter = q.get("answer", "A").strip().upper()
                user_choice = st.session_state.bank_quiz_answers.get(i, "")
                is_correct = user_choice[:1].upper() == ans_letter
                icon = "✅" if is_correct else "❌"
                bg = "#f0fdf4" if is_correct else "#fef2f2"
                border = "#86efac" if is_correct else "#fca5a5"
                opts_html = "".join(
                    f"<div style='color:{'#15803d' if opt.startswith(ans_letter) else '#374151'};'>"
                    f"{'★ ' if opt.startswith(ans_letter) else '　'}{opt}</div>"
                    for opt in q.get("options", [])
                )
                st.markdown(
                    f"<div style='background:{bg};border:1.5px solid {border};"
                    f"border-radius:12px;padding:0.9rem 1.1rem;margin-bottom:0.7rem;'>"
                    f"<div style='font-weight:600;'>{icon} Q{i+1}. {q.get('question','')}</div>"
                    f"<div style='margin:0.4rem 0 0.2rem;font-size:0.88rem;'>{opts_html}</div>"
                    f"<div style='font-size:0.85rem;color:#374151;'>"
                    f"你的答案：{user_choice} &nbsp;·&nbsp; 正確答案：{ans_letter}</div>"
                    f"<div style='font-size:0.83rem;color:#6b7280;margin-top:0.3rem;'>"
                    f"💡 {q.get('explanation','')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if st.button("🔄 再測一次", use_container_width=True):
                st.session_state.bank_quiz_questions = []
                st.session_state.bank_quiz_answers = {}
                st.session_state.bank_quiz_submitted = False
                st.session_state.bank_quiz_score = None
                st.rerun()

    def _render_rag_section(self):
        _hdr("🔍", "RAG 問答")
        st.caption("根據已索引的文件內容回答問題，並自動強化系統知識庫。")

        docs = list_rag_documents(db_path=st.session_state.db_path)
        if not docs:
            st.info("尚未索引任何文件，請先上傳分析。")
            return

        # 選擇文件範圍
        scope_opts = ["全部文件"] + [d["filename"] for d in docs]
        scope = st.selectbox("問答範圍", scope_opts, key="rag_scope")
        scope_doc_id = None
        if scope != "全部文件":
            matched = next((d for d in docs if d["filename"] == scope), None)
            if matched:
                scope_doc_id = matched["id"]

        question = st.text_area(
            "輸入問題",
            placeholder="例如：這份文件的主要論點是什麼？",
            key="rag_question_input",
            height=90,
        )

        if st.button("🔍 提問", type="primary", use_container_width=True) and question.strip():
            with st.spinner("搜尋相關知識片段…"):
                try:
                    hits = query_knowledge(question.strip(), n_results=5, doc_id=scope_doc_id)
                except Exception as e:
                    st.error(f"向量查詢失敗：{e}")
                    return

            if not hits:
                st.warning("未找到相關知識片段，請嘗試換個問法或先上傳相關文件。")
                return

            with st.spinner("AI 根據知識片段生成回答…"):
                try:
                    llm = _get_llm()
                    prompt = build_rag_prompt(question.strip(), hits)
                    resp = llm.invoke([HumanMessage(content=prompt)])
                    answer = resp.content.strip()
                except Exception as e:
                    st.error(f"AI 回答失敗：{e}")
                    return

            st.session_state.doc_rag_answer = answer
            st.session_state.doc_rag_question = question.strip()

            # 自動儲存到知識庫（強化反饋）
            source_summary = " | ".join(h["filename"] for h in hits[:3])
            save_rag_knowledge(
                question=question.strip(),
                answer=answer,
                source_chunks=source_summary,
                doc_id=scope_doc_id,
                db_path=st.session_state.db_path,
            )
            st.rerun()

        # 顯示回答
        if st.session_state.doc_rag_answer:
            st.markdown(
                "<div style='font-weight:600;color:#4f46e5;margin:0.8rem 0 0.3rem;'>🤖 AI 回答</div>",
                unsafe_allow_html=True,
            )
            _card(f"<div style='color:#1e1b4b;font-size:0.95rem;'>"
                  f"{st.session_state.doc_rag_answer.replace(chr(10), '<br>')}</div>")
            _tts_component(st.session_state.doc_rag_answer)

            st.caption("✅ 此問答已自動儲存至知識庫，強化系統未來回答的正確性。")

    # ── 歷史紀錄 ──────────────────────────────────────────────

    def _render_history_section(self):
        _hdr("📊", "歷史紀錄")

        col_quiz, col_rag = st.columns(2)

        with col_quiz:
            st.markdown(
                "<div style='font-weight:600;color:#4f46e5;margin-bottom:0.5rem;'>🏆 測驗紀錄</div>",
                unsafe_allow_html=True,
            )
            records = list_quiz_records(limit=15, db_path=st.session_state.db_path)
            if not records:
                st.info("尚無測驗紀錄。")
            else:
                for r in records:
                    badge_color = (
                        "#10b981" if r["score"] >= 80
                        else "#f59e0b" if r["score"] >= 60
                        else "#ef4444"
                    )
                    st.markdown(
                        f"<div style='background:#f8faff;border:1px solid #e0e7ff;"
                        f"border-radius:10px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;"
                        f"font-size:0.88rem;'>"
                        f"<b style='color:#4f46e5;'>{r['filename'] or '—'}</b><br>"
                        f"答對 {r['correct_count']}/{r['total_questions']} 題 &nbsp;"
                        f"<span style='background:{badge_color};color:#fff;"
                        f"border-radius:8px;padding:0.1rem 0.5rem;font-size:0.8rem;'>"
                        f"{r['score']:.0f}%</span>"
                        f"&nbsp; <span style='color:#9ca3af;'>{r['created_at'][:10]}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        with col_rag:
            st.markdown(
                "<div style='font-weight:600;color:#4f46e5;margin-bottom:0.5rem;'>🧠 知識強化紀錄</div>",
                unsafe_allow_html=True,
            )
            knowledge_records = list_rag_knowledge(limit=15, db_path=st.session_state.db_path)
            if not knowledge_records:
                st.info("尚無知識強化紀錄。")
            else:
                for r in knowledge_records:
                    st.markdown(
                        f"<div style='background:#f8faff;border:1px solid #e0e7ff;"
                        f"border-radius:10px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;"
                        f"font-size:0.88rem;'>"
                        f"<b>Q：{r['question'][:60]}{'…' if len(r['question'])>60 else ''}</b><br>"
                        f"<span style='color:#6b7280;'>A：{r['answer'][:80]}{'…' if len(r['answer'])>80 else ''}</span><br>"
                        f"<span style='color:#9ca3af;font-size:0.8rem;'>{r['created_at'][:10]}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
