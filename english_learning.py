import json
import os
import random
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from llm_factory import LLMFactory
from langchain_core.messages import HumanMessage
from i18n import t
from db_utils import (
    delete_translation_entry,
    get_learning_stats,
    list_english_practice_items,
    list_study_sessions,
    load_daily_review_state,
    record_study_session,
    save_daily_review_state,
    save_setting,
    load_setting,
    save_translation_entry,
    search_translation_entries,
    should_show_daily_review_reminder,
)

# ── 共用樣式常數 ───────────────────────────────────────────────
CARD_STYLE = (
    "background:linear-gradient(135deg,#f8faff 0%,#eef2ff 100%);"
    "border:1.5px solid #c7d2fe;"
    "border-radius:16px;"
    "padding:1.2rem 1.4rem;"
    "margin-bottom:0.8rem;"
    "box-shadow:0 4px 16px rgba(99,102,241,0.08);"
)
STAT_CARD_STYLE = (
    "background:linear-gradient(135deg,#ffffff 0%,#f0fdf4 100%);"
    "border:1.5px solid #bbf7d0;"
    "border-radius:14px;"
    "padding:1rem 1.2rem;"
    "text-align:center;"
    "box-shadow:0 2px 10px rgba(34,197,94,0.07);"
)
SECTION_HEADER_STYLE = (
    "font-size:1.15rem;font-weight:700;color:#4f46e5;"
    "margin-bottom:0.2rem;letter-spacing:0.01em;"
)
DIVIDER_HTML = "<hr style='border:none;border-top:1.5px solid #e0e7ff;margin:1.6rem 0;'/>"


def _card(content_html: str, extra_style: str = "") -> None:
    st.markdown(
        f"<div style='{CARD_STYLE}{extra_style}'>{content_html}</div>",
        unsafe_allow_html=True,
    )


def _section_header(icon: str, title: str) -> None:
    st.markdown(
        f"<div style='{SECTION_HEADER_STYLE}'>{icon} {title}</div>",
        unsafe_allow_html=True,
    )


def _divider() -> None:
    st.markdown(DIVIDER_HTML, unsafe_allow_html=True)


# ── TTS 發音按鈕 Component ────────────────────────────────────

def _tts_button_html(word: str, btn_id: str = "tts_btn", size: str = "small") -> str:
    """產生內嵌 Web Speech API TTS 按鈕的 HTML 字串（直接嵌入 st.markdown）。"""
    font_size = "0.8rem" if size == "small" else "0.95rem"
    padding = "0.2rem 0.7rem" if size == "small" else "0.35rem 1rem"
    word_escaped = word.replace("'", "\\'").replace('"', "&quot;")
    return (
        f"<button id='{btn_id}' onclick=\"(function(){{"
        f"var u=new SpeechSynthesisUtterance('{word_escaped}');"
        f"u.lang='en-US';u.rate=0.85;"
        f"window.speechSynthesis.cancel();"
        f"window.speechSynthesis.speak(u);"
        f"}})()\" style='background:linear-gradient(135deg,#6366f1,#818cf8);"
        f"color:#fff;border:none;border-radius:20px;padding:{padding};"
        f"font-size:{font_size};cursor:pointer;font-weight:600;"
        f"box-shadow:0 2px 8px rgba(99,102,241,0.25);letter-spacing:0.02em;'>"
        f"🔊 發音</button>"
    )


def _render_tts_component(word: str, component_key: str = "tts", height: int = 50) -> None:
    """用 st.components 渲染 TTS 按鈕（獨立 iframe，確保 JS 可執行）。"""
    word_escaped = word.replace("'", "\\'").replace("`", "\\`").replace('"', "&quot;")
    html = f"""
    <button onclick="(function(){{
        var u=new SpeechSynthesisUtterance('{word_escaped}');
        u.lang='en-US'; u.rate=0.85;
        window.parent.speechSynthesis ? window.parent.speechSynthesis.cancel() : window.speechSynthesis.cancel();
        (window.parent.speechSynthesis || window.speechSynthesis).speak(u);
    }})()" style="
        background:linear-gradient(135deg,#6366f1,#818cf8);
        color:#fff; border:none; border-radius:20px;
        padding:0.3rem 1rem; font-size:0.88rem;
        cursor:pointer; font-weight:600;
        box-shadow:0 2px 8px rgba(99,102,241,0.25);
    ">🔊 朗讀發音</button>
    """
    components.html(html, height=height)


# ── 發音測驗 Component ────────────────────────────────────────

def _render_pronunciation_test(word: str, component_key: str = "pron_test") -> None:
    """渲染發音測驗區塊：TTS 示範 + Web Speech API 錄音辨識 + 比對結果。"""
    word_escaped = word.replace("'", "\\'").replace("`", "\\`").replace('"', "&quot;")
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin:0; padding:8px; font-family:'Segoe UI',sans-serif; background:transparent; }}
  .container {{ background:linear-gradient(135deg,#fefce8,#fef9c3); border:1.5px solid #fcd34d;
    border-radius:14px; padding:1rem 1.2rem; }}
  .word-display {{ font-size:1.6rem; font-weight:800; color:#1c1917; margin-bottom:0.3rem; }}
  .hint {{ font-size:0.82rem; color:#78350f; margin-bottom:0.8rem; }}
  .btn-row {{ display:flex; gap:0.6rem; flex-wrap:wrap; margin-bottom:0.8rem; }}
  button {{ border:none; border-radius:20px; padding:0.35rem 1rem; font-size:0.85rem;
    font-weight:600; cursor:pointer; transition:opacity 0.2s; }}
  button:hover {{ opacity:0.85; }}
  #btnDemo {{ background:linear-gradient(135deg,#6366f1,#818cf8); color:#fff; }}
  #btnRecord {{ background:linear-gradient(135deg,#10b981,#34d399); color:#fff; }}
  #btnRecord.recording {{ background:linear-gradient(135deg,#ef4444,#f87171); animation:pulse 1s infinite; }}
  #btnRetry {{ background:#e0e7ff; color:#4338ca; display:none; }}
  @keyframes pulse {{ 0%,100%{{transform:scale(1)}} 50%{{transform:scale(1.04)}} }}
  .result-box {{ border-radius:10px; padding:0.6rem 0.9rem; font-size:0.9rem; margin-top:0.4rem; display:none; }}
  .result-correct {{ background:#dcfce7; border:1.5px solid #86efac; color:#166534; }}
  .result-partial {{ background:#fef3c7; border:1.5px solid #fcd34d; color:#92400e; }}
  .result-wrong {{ background:#fee2e2; border:1.5px solid #fca5a5; color:#991b1b; }}
  .recognized {{ font-size:0.82rem; color:#6b7280; margin-top:0.3rem; }}
  .score-badge {{ display:inline-block; background:#4f46e5; color:#fff; border-radius:12px;
    padding:0.1rem 0.6rem; font-size:0.78rem; font-weight:700; margin-left:0.4rem; }}
  .no-support {{ background:#fee2e2; border:1.5px solid #fca5a5; color:#991b1b;
    border-radius:10px; padding:0.5rem 0.9rem; font-size:0.85rem; }}
</style>
</head>
<body>
<div class="container">
  <div class="word-display" id="targetWord">{word_escaped}</div>
  <div class="hint">📌 先聽示範發音，再點「開始錄音」跟著說出這個單字</div>
  <div class="btn-row">
    <button id="btnDemo" onclick="playDemo()">🔊 示範發音</button>
    <button id="btnRecord" onclick="toggleRecord()">🎤 開始錄音</button>
    <button id="btnRetry" onclick="retryTest()">🔄 重試</button>
  </div>
  <div id="resultBox" class="result-box"></div>
  <div id="recognizedText" class="recognized"></div>
  <div id="noSupport" style="display:none" class="no-support">
    ⚠️ 您的瀏覽器不支援語音辨識，請使用 Chrome 或 Edge。
  </div>
</div>

<script>
const TARGET = '{word_escaped}'.toLowerCase().trim();
let recognition = null;
let isRecording = false;

function playDemo() {{
  var u = new SpeechSynthesisUtterance(TARGET);
  u.lang = 'en-US'; u.rate = 0.85;
  (window.parent.speechSynthesis || window.speechSynthesis).speak(u);
}}

function calcSimilarity(a, b) {{
  // 簡單字串相似度：Levenshtein 距離
  a = a.toLowerCase().trim(); b = b.toLowerCase().trim();
  if (a === b) return 1.0;
  const la = a.length, lb = b.length;
  if (!la || !lb) return 0;
  const dp = Array.from({{length:la+1}}, (_,i) => Array.from({{length:lb+1}}, (_,j) => j===0?i:0));
  for (let j=1;j<=lb;j++) dp[0][j]=j;
  for (let i=1;i<=la;i++) for (let j=1;j<=lb;j++) {{
    dp[i][j] = a[i-1]===b[j-1] ? dp[i-1][j-1] :
      1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
  }}
  return 1 - dp[la][lb] / Math.max(la, lb);
}}

function showResult(recognizedWords) {{
  // 比對辨識的每個詞與目標
  const words = recognizedWords.toLowerCase().trim().split(/\\s+/);
  let bestScore = 0;
  let bestWord = '';
  for (const w of words) {{
    const score = calcSimilarity(w, TARGET);
    if (score > bestScore) {{ bestScore = score; bestWord = w; }}
  }}

  const pct = Math.round(bestScore * 100);
  const resultBox = document.getElementById('resultBox');
  const recText = document.getElementById('recognizedText');
  resultBox.style.display = 'block';
  recText.style.display = 'block';
  recText.textContent = '🎧 辨識到：「' + recognizedWords + '」（最佳匹配：' + bestWord + '）';

  if (bestScore >= 0.9) {{
    resultBox.className = 'result-box result-correct';
    resultBox.innerHTML = '✅ 發音正確！非常標準！<span class="score-badge">' + pct + ' 分</span>';
  }} else if (bestScore >= 0.6) {{
    resultBox.className = 'result-box result-partial';
    resultBox.innerHTML = '🔶 接近正確，可以再練習。<span class="score-badge">' + pct + ' 分</span><br><small>目標：' + TARGET + '，辨識：' + bestWord + '</small>';
  }} else {{
    resultBox.className = 'result-box result-wrong';
    resultBox.innerHTML = '❌ 發音需要加強，請再試試。<span class="score-badge">' + pct + ' 分</span><br><small>目標：' + TARGET + '，辨識：' + bestWord + '</small>';
  }}
  document.getElementById('btnRetry').style.display = 'inline-block';
}}

function retryTest() {{
  document.getElementById('resultBox').style.display = 'none';
  document.getElementById('recognizedText').style.display = 'none';
  document.getElementById('btnRetry').style.display = 'none';
}}

function toggleRecord() {{
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {{
    document.getElementById('noSupport').style.display = 'block';
    return;
  }}

  if (isRecording) {{
    recognition && recognition.stop();
    return;
  }}

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 3;

  const btn = document.getElementById('btnRecord');
  recognition.onstart = function() {{
    isRecording = true;
    btn.textContent = '⏹ 停止錄音';
    btn.classList.add('recording');
  }};
  recognition.onend = function() {{
    isRecording = false;
    btn.textContent = '🎤 開始錄音';
    btn.classList.remove('recording');
  }};
  recognition.onerror = function(e) {{
    isRecording = false;
    btn.textContent = '🎤 開始錄音';
    btn.classList.remove('recording');
    if (e.error !== 'aborted') {{
      document.getElementById('resultBox').style.display = 'block';
      document.getElementById('resultBox').className = 'result-box result-wrong';
      document.getElementById('resultBox').textContent = '⚠️ 錄音失敗：' + e.error + '，請確認麥克風權限。';
    }}
  }};
  recognition.onresult = function(event) {{
    let recognized = '';
    // 取所有候選結果中最佳匹配
    let bestScore = 0, bestText = '';
    for (let i = 0; i < event.results[0].length; i++) {{
      const txt = event.results[0][i].transcript;
      const score = calcSimilarity(txt.toLowerCase().trim(), TARGET);
      if (score > bestScore) {{ bestScore = score; bestText = txt; }}
      if (i === 0) recognized = txt;
    }}
    showResult(bestText || recognized);
  }};
  recognition.start();
}}
</script>
</body>
</html>
"""
    components.html(html, height=280, scrolling=False)


# ── Helper functions（原有邏輯，完整保留）─────────────────────

def _load_saved_categories(db_path):
    raw_value = load_setting("english_categories", "[]", db_path=db_path) or "[]"
    try:
        categories = json.loads(raw_value)
    except Exception:
        categories = []
    return [item for item in categories if isinstance(item, str) and item.strip()] or ["未分類"]


def _save_saved_categories(categories, db_path):
    save_setting("english_categories", json.dumps(categories, ensure_ascii=False), db_path=db_path)


def normalize_flashcard_state(practice_items, flashcard_index, flashcard_revealed):
    if not practice_items:
        return 0, False
    total_cards = len(practice_items)
    safe_index = max(0, min(int(flashcard_index), total_cards - 1))
    return safe_index, bool(flashcard_revealed)


def parse_llm_translation_response(response_text: str):
    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    translation = ""
    example = ""
    for line in lines:
        if line.lower().startswith("中文意思") or line.lower().startswith("意思"):
            translation = line.split("：", 1)[-1].strip() if "：" in line else line.split(":", 1)[-1].strip()
        elif line.lower().startswith("例句"):
            example = line.split("：", 1)[-1].strip() if "：" in line else line.split(":", 1)[-1].strip()
    if not translation and lines:
        translation = lines[0]
    if not example and lines and len(lines) > 1:
        example = lines[1]
    return translation, example


def parse_llm_phonetic_response(response_text: str) -> str:
    """從 LLM 回應中解析 IPA 音標（格式：音標：/.../ 或 IPA：/.../）。"""
    for line in response_text.splitlines():
        text = line.strip()
        if not text:
            continue
        lower = text.lower()
        if lower.startswith("音標") or lower.startswith("ipa") or lower.startswith("phonetic"):
            value = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
            if value:
                return value.strip()
        # 直接辨識 /.../ 格式
        if text.startswith("/") and text.endswith("/"):
            return text
        # 辨識 [...]格式
        if text.startswith("[") and text.endswith("]"):
            return text
    return ""


def parse_llm_example_sentences(response_text: str):
    examples = []
    for line in response_text.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.lower().startswith(("例句", "example", "例句1", "例句2", "例句3")):
            value = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
            if value:
                examples.append(value)
    return examples


def parse_llm_example_items(response_text: str, fallback_translation: str = ""):
    items = []
    for line in response_text.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.lower().startswith(("例句", "example", "例句1", "例句2", "例句3")):
            raw_value = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
            english = raw_value
            chinese = fallback_translation
            if "｜" in raw_value:
                parts = [p.strip() for p in raw_value.split("｜") if p.strip()]
                if parts:
                    english = parts[0]
                    chinese = parts[1] if len(parts) > 1 else fallback_translation
            elif "|" in raw_value:
                parts = [p.strip() for p in raw_value.split("|") if p.strip()]
                if parts:
                    english = parts[0]
                    chinese = parts[1] if len(parts) > 1 else fallback_translation
            elif "中文翻譯：" in raw_value:
                english, chinese = raw_value.split("中文翻譯：", 1)
                english = english.strip()
                chinese = chinese.strip() or fallback_translation
            elif "中文：" in raw_value:
                english, chinese = raw_value.split("中文：", 1)
                english = english.strip()
                chinese = chinese.strip() or fallback_translation
            if english:
                items.append({"english": english, "chinese": chinese or fallback_translation})
    return items


def serialize_example_items(example_items: list) -> str:
    lines = []
    for item in example_items or []:
        if isinstance(item, dict):
            english = (item.get("english") or "").strip()
            chinese = (item.get("chinese") or "").strip()
        else:
            english = (item or "").strip()
            chinese = ""
        if not english:
            continue
        if chinese:
            lines.append(f"{english}｜{chinese}")
        else:
            lines.append(english)
    return "\n".join(lines)


def parse_stored_examples(example_text: str):
    items = []
    if not example_text:
        return items
    for line in example_text.splitlines():
        text = line.strip()
        if not text:
            continue
        english = text
        chinese = ""
        if "｜" in text:
            parts = [p.strip() for p in text.split("｜") if p.strip()]
            if parts:
                english = parts[0]
                chinese = parts[1] if len(parts) > 1 else ""
        elif "|" in text:
            parts = [p.strip() for p in text.split("|") if p.strip()]
            if parts:
                english = parts[0]
                chinese = parts[1] if len(parts) > 1 else ""
        elif "中文翻譯：" in text:
            english, chinese = text.split("中文翻譯：", 1)
            english = english.strip()
            chinese = chinese.strip()
        elif "中文：" in text:
            english, chinese = text.split("中文：", 1)
            english = english.strip()
            chinese = chinese.strip()
        if english:
            items.append({"english": english, "chinese": chinese})
    return items


def merge_example_sentences(primary_example: str, candidate_examples: list) -> list:
    merged = []
    seen = set()
    for example in [primary_example] + list(candidate_examples or []):
        normalized = (example or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def merge_example_items(primary_example, candidate_examples: list, fallback_translation: str = "") -> list:
    merged = []
    seen = set()
    source_items = []
    if isinstance(primary_example, dict):
        source_items.append(primary_example)
    elif primary_example:
        source_items.append({"english": primary_example, "chinese": fallback_translation})
    for item in list(candidate_examples or []):
        if isinstance(item, dict):
            source_items.append(item)
        elif item:
            source_items.append({"english": item, "chinese": fallback_translation})
    for item in source_items:
        english = (item.get("english") if isinstance(item, dict) else item or "").strip()
        chinese = (item.get("chinese") if isinstance(item, dict) else fallback_translation or "").strip()
        if not english:
            continue
        key = english.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append({"english": english, "chinese": chinese or fallback_translation})
    return merged


def resolve_translation_lookup(query: str, db_path: str = None):
    local_records = search_translation_entries(query, db_path=db_path)
    if local_records:
        record = local_records[0]
        example_entries = parse_stored_examples(record.get("example", ""))
        if not example_entries and record.get("example"):
            example_entries = [{"english": record.get("example", ""), "chinese": record.get("translation", "")}]
        return {
            "english": record["english"],
            "translation": record["translation"],
            "example": example_entries[0]["english"] if example_entries else "",
            "examples": example_entries,
            "phonetic": record.get("phonetic", ""),
            "source": "local",
        }
    return {"english": query, "translation": "", "example": "", "examples": [], "phonetic": "", "source": "llm"}


def get_flashcard_display_content(card, display_mode: str):
    if display_mode == "chinese":
        return card.get("translation", "") or card.get("english", "")
    return card.get("english", "") or card.get("translation", "")


def build_quiz_question(practice_items):
    if not practice_items:
        return {
            "question": "hello",
            "options": ["你好", "再見", "早安", "謝謝"],
            "answer": "你好",
        }
    sample = random.choice(practice_items)
    distractors = [
        item.get("translation", "")
        for item in practice_items
        if item.get("translation") and item.get("translation") != sample.get("translation")
    ]
    if len(distractors) < 3:
        distractors += ["請重新練習", "這是測驗示例", "請稍後再試"]
    options = [sample.get("translation", "")]
    for candidate in random.sample(distractors, k=min(3, len(distractors))):
        if candidate not in options:
            options.append(candidate)
    random.shuffle(options)
    return {
        "question": sample.get("english", "hello"),
        "options": options,
        "answer": sample.get("translation", ""),
    }


class EnglishLearningPage:
    def __init__(self):
        pass

    def render(self):
        # ── 頁面標題 ────────────────────────────────────────────
        st.markdown(
            "<h2 style='color:#4f46e5;margin-bottom:0.2rem;'>📚 英文學習中心</h2>"
            "<p style='color:#6b7280;font-size:0.95rem;margin-top:0;'>字典查詢・單字卡片・AI 生字集・測驗成效</p>",
            unsafe_allow_html=True,
        )

        # ── Session state 初始化 ─────────────────────────────────
        defaults = {
            "review_toast_shown": False,
            "flashcard_index": 0,
            "flashcard_revealed": False,
            "flashcard_display_mode": "english",
            "selected_category": "未分類",
            "table_page_size": 10,
            "table_page": 0,
            "translation_result": None,
            "example_candidates": [],
            "last_search_query": "",
            "quiz_question": None,
            "quiz_options": [],
            "quiz_answer": None,
            "quiz_result": None,
            "quiz_submitted": False,
            # 發音測驗
            "pron_test_word": "",
            "show_pron_test": False,
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

        # ── 統計資料 ─────────────────────────────────────────────
        stats = get_learning_stats(db_path=st.session_state.db_path)
        today = datetime.utcnow().date().isoformat()
        review_date = load_daily_review_state(db_path=st.session_state.db_path)
        show_review = should_show_daily_review_reminder(today=today, db_path=st.session_state.db_path)

        if show_review and not st.session_state.review_toast_shown:
            st.toast("🔔 今日提醒：建議完成 5 分鐘複習！", icon="🔔")
            st.session_state.review_toast_shown = True

        # ── 統計卡片列 ───────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        stat_items = [
            (c1, "📖", "單字總數", str(stats["total_items"]), "#6366f1"),
            (c2, "🎯", "測驗次數", str(stats["total_sessions"]), "#0ea5e9"),
            (c3, "✅", "最近準確率", f"{stats['latest_accuracy'] * 100:.0f}%", "#10b981"),
            (c4, "🔥", "累計答對", str(stats["total_score"]), "#f59e0b"),
        ]
        for col, icon, label, value, color in stat_items:
            with col:
                st.markdown(
                    f"<div style='background:#fff;border:1.5px solid #e0e7ff;border-radius:14px;"
                    f"padding:0.9rem 1rem;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.05);'>"
                    f"<div style='font-size:1.5rem;'>{icon}</div>"
                    f"<div style='font-size:1.6rem;font-weight:700;color:{color};line-height:1.2;'>{value}</div>"
                    f"<div style='font-size:0.8rem;color:#6b7280;margin-top:0.15rem;'>{label}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

        # ── 複習提醒 ─────────────────────────────────────────────
        if show_review:
            st.warning("📅 今日還未完成複習，建議再看 5 個單字或做一次測驗。")
        else:
            st.success(f"✅ 今日已完成複習，最後一次：{review_date}")

        if st.button("🗓️ 標記今日複習完成", use_container_width=False):
            save_daily_review_state(today, db_path=st.session_state.db_path)
            st.session_state.review_toast_shown = False
            st.success("已記錄今日複習 🎉")
            st.rerun()

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 1：AI 一鍵生成生字集
        # ════════════════════════════════════════════════════════
        _section_header("⚡", "AI 一鍵生成生字集")
        st.caption("選擇主題與難度，由 AI 自動生成單字並匯入字庫，免去手動輸入。")

        col_theme, col_level, col_count = st.columns([2, 1, 1])
        with col_theme:
            gen_theme = st.selectbox(
                "學習主題",
                ["TOEFL 核心字彙", "IELTS 雅思字彙", "生活常用英文", "職場商務英文", "旅遊情境英文", "科技資訊英文"],
                label_visibility="collapsed",
            )
        with col_level:
            gen_level = st.selectbox(
                "字彙難度",
                ["初級 (Basic)", "中級 (Intermediate)", "高級 (Advanced)"],
                label_visibility="collapsed",
            )
        with col_count:
            gen_count = st.number_input("生成數量", min_value=3, max_value=15, value=5, step=1, label_visibility="collapsed")

        if st.button("⚡ 開始生成並自動匯入", use_container_width=True, type="primary"):
            with st.spinner("AI 正在量身打造字彙庫並寫入資料庫…"):
                try:
                    llm = LLMFactory.get_llm(
                        st.session_state.provider,
                        model_name=st.session_state.model,
                        temperature=0.7,
                    )
                    prompt = (
                        f"請生成 {gen_count} 個適合 {gen_level} 程度的「{gen_theme}」英文單字或常用片語。\n"
                        "請嚴格以下方 JSON 陣列格式回傳，不可包含任何 markdown 標記或額外文字。\n\n"
                        '[\n  {"english":"單字","translation":"中文意思","example":"英文例句｜中文翻譯"}\n]'
                    )
                    response = llm.invoke([HumanMessage(content=prompt)])
                    raw_json = response.content.strip()
                    if raw_json.startswith("```"):
                        lines = raw_json.splitlines()
                        lines = lines[1:] if lines[0].startswith("```") else lines
                        lines = lines[:-1] if lines[-1].startswith("```") else lines
                        raw_json = "\n".join(lines).strip()
                    vocab_list = json.loads(raw_json)
                    added_count = 0
                    imported_words = []
                    for item in vocab_list:
                        eng = item.get("english", "").strip()
                        trans = item.get("translation", "").strip()
                        ex = item.get("example", "").strip()
                        if eng and trans:
                            save_translation_entry(eng, trans, ex, category=gen_theme, db_path=st.session_state.db_path)
                            imported_words.append(f"<b>{eng}</b> — {trans}")
                            added_count += 1
                    if added_count > 0:
                        st.success(f"✅ 成功匯入 {added_count} 個單字至「{gen_theme}」！")
                        words_html = "".join(
                            f"<span style='display:inline-block;background:#eef2ff;border-radius:8px;"
                            f"padding:0.2rem 0.6rem;margin:0.2rem;font-size:0.88rem;'>{w}</span>"
                            for w in imported_words
                        )
                        st.markdown(f"<div style='margin-top:0.5rem;'>{words_html}</div>", unsafe_allow_html=True)
                        st.session_state.saved_categories = _load_saved_categories(st.session_state.db_path)
                        st.session_state.selected_category = gen_theme
                        st.rerun()
                    else:
                        st.error("產生的單字為空，請重試。")
                except Exception as e:
                    st.error(f"❌ 生成失敗：{e}")
                    st.info("💡 請確認所選 AI 模型的 API 金鑰是否正常。")

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 2：單字卡片模式
        # ════════════════════════════════════════════════════════
        _section_header("🃏", "單字卡片複習")

        practice_items = list_english_practice_items(limit=100, db_path=st.session_state.db_path)
        if practice_items:
            self._render_flashcard_section(practice_items)
        else:
            st.info("目前沒有可複習的單字，先用 AI 生成或手動新增幾個吧。")

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 3：字典式查詢
        # ════════════════════════════════════════════════════════
        _section_header("📖", "字典式查詢")
        self._render_dictionary_section()

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 4：TOEFL 風格測驗
        # ════════════════════════════════════════════════════════
        _section_header("🧪", "TOEFL 風格測驗")
        self._render_quiz_section()

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 5：發音測驗
        # ════════════════════════════════════════════════════════
        _section_header("🎤", "發音測驗")
        self._render_pronunciation_section()

        _divider()

        # ════════════════════════════════════════════════════════
        # 區塊 5：學習成效 & 趨勢
        # ════════════════════════════════════════════════════════
        _section_header("📊", "學習成效與趨勢")
        self._render_stats_section()

    # ── 單字卡片區塊 ────────────────────────────────────────────
    def _render_flashcard_section(self, practice_items):
        categories = sorted({item.get("category", "未分類") for item in practice_items})
        if st.session_state.saved_categories:
            categories = sorted(set(categories) | set(st.session_state.saved_categories))

        col_cat, col_mode = st.columns([3, 2])
        with col_cat:
            selected_category = st.selectbox(
                "單字本分類",
                options=categories,
                index=max(0, categories.index(st.session_state.selected_category))
                if st.session_state.selected_category in categories else 0,
                key="flashcard_category_select",
            )
            st.session_state.selected_category = selected_category

        with col_mode:
            display_mode_label = st.radio(
                "顯示方向",
                ["英文→中文", "中文→英文"],
                horizontal=True,
                index=0 if st.session_state.flashcard_display_mode == "english" else 1,
                key="flashcard_display_mode_radio",
            )
            st.session_state.flashcard_display_mode = "english" if display_mode_label == "英文→中文" else "chinese"

        filtered_items = [i for i in practice_items if i.get("category", "未分類") == selected_category] or practice_items

        index, revealed = normalize_flashcard_state(
            filtered_items,
            st.session_state.flashcard_index,
            st.session_state.flashcard_revealed,
        )
        st.session_state.flashcard_index = index
        st.session_state.flashcard_revealed = revealed
        card = filtered_items[index]
        total_cards = len(filtered_items)

        if not revealed:
            front = card["english"] if st.session_state.flashcard_display_mode == "english" else card["translation"]
            badge_color, badge_text = "#6366f1", "點擊顯示答案 ↓"
        else:
            front = card["translation"] if st.session_state.flashcard_display_mode == "english" else card["english"]
            badge_color, badge_text = "#10b981", "✓ 答案已顯示"

        # 音標
        phonetic = card.get("phonetic", "")
        phonetic_html = (
            f"<span style='font-size:0.95rem;color:#818cf8;font-family:serif;"
            f"margin-left:0.5rem;letter-spacing:0.04em;'>{phonetic}</span>"
            if phonetic else ""
        )

        # 卡片主體
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#f8faff 0%,#e0e7ff 100%);"
            f"border:2px solid #a5b4fc;border-radius:20px;padding:1.6rem 1.8rem;"
            f"margin:0.6rem 0 0.8rem;box-shadow:0 8px 24px rgba(99,102,241,0.12);'>"
            f"<div style='font-size:0.82rem;color:#818cf8;font-weight:600;letter-spacing:0.05em;'>"
            f"卡片 {index + 1} / {total_cards} &nbsp;·&nbsp; {selected_category}</div>"
            f"<div style='font-size:2rem;font-weight:800;color:#1e1b4b;margin:0.5rem 0 0.2rem;'>"
            f"{front}{phonetic_html}</div>"
            f"<span style='background:{badge_color};color:#fff;border-radius:20px;"
            f"padding:0.2rem 0.8rem;font-size:0.78rem;font-weight:600;'>{badge_text}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # TTS 發音按鈕（永遠顯示在卡片下方）
        tts_word = card["english"]
        _render_tts_component(tts_word, component_key=f"tts_flash_{index}")

        if card.get("example") and revealed:
            st.markdown(
                f"<div style='background:#f0fdf4;border-left:3px solid #34d399;border-radius:8px;"
                f"padding:0.6rem 0.9rem;margin-bottom:0.7rem;font-size:0.88rem;color:#065f46;'>"
                f"💬 <i>{card['example']}</i></div>",
                unsafe_allow_html=True,
            )

        # 操作按鈕列
        btn_prev, btn_show, btn_next = st.columns([1, 2, 1])
        with btn_prev:
            if st.button("◀ 上一張", use_container_width=True):
                st.session_state.flashcard_index = (index - 1) % total_cards
                st.session_state.flashcard_revealed = False
                st.rerun()
        with btn_show:
            if st.button("👁️ 顯示答案", use_container_width=True, type="primary"):
                st.session_state.flashcard_revealed = True
                st.rerun()
        with btn_next:
            if st.button("下一張 ▶", use_container_width=True):
                st.session_state.flashcard_index = (index + 1) % total_cards
                st.session_state.flashcard_revealed = False
                st.rerun()

        if revealed:
            r1, r2 = st.columns(2)
            with r1:
                if st.button("✅ 記得了", use_container_width=True):
                    record_study_session("flashcard", 1, 1, db_path=st.session_state.db_path)
                    st.session_state.flashcard_revealed = False
                    st.session_state.flashcard_index = (index + 1) % total_cards
                    st.success("已記錄 ✓")
                    st.rerun()
            with r2:
                if st.button("🔁 再複習", use_container_width=True):
                    record_study_session("flashcard", 0, 1, db_path=st.session_state.db_path)
                    st.session_state.flashcard_revealed = False
                    st.session_state.flashcard_index = (index + 1) % total_cards
                    st.info("已標記需再複習")
                    st.rerun()

            # 發音測驗快速入口
            if st.button("🎤 練習此單字發音", use_container_width=True):
                st.session_state.pron_test_word = card["english"]
                st.session_state.show_pron_test = True
                st.rerun()

            if st.session_state.show_pron_test and st.session_state.pron_test_word == card["english"]:
                st.markdown(
                    "<div style='font-size:0.9rem;font-weight:600;color:#d97706;margin:0.5rem 0 0.3rem;'>"
                    "🎤 發音練習</div>",
                    unsafe_allow_html=True,
                )
                _render_pronunciation_test(card["english"], component_key=f"pron_flash_{index}")
                if st.button("✖ 關閉發音練習", key=f"close_pron_{index}"):
                    st.session_state.show_pron_test = False
                    st.rerun()

        # 收藏
        card_key = card.get("english", "")
        is_favorite = card_key in st.session_state.favorite_cards
        fav_col, save_col = st.columns([1, 1])
        with fav_col:
            fav_label = "☆ 取消收藏" if is_favorite else "⭐ 收藏此卡"
            if st.button(fav_label, use_container_width=True):
                if is_favorite:
                    st.session_state.favorite_cards = [i for i in st.session_state.favorite_cards if i != card_key]
                else:
                    st.session_state.favorite_cards = sorted(set(st.session_state.favorite_cards + [card_key]))
                st.rerun()
        with save_col:
            if st.button("📂 存入分類", use_container_width=True):
                save_translation_entry(
                    card["english"], card["translation"], card.get("example", ""),
                    category=selected_category, db_path=st.session_state.db_path,
                )
                st.success(f"已存入「{selected_category}」")

        # 分類管理 & 單字清單（摺疊）
        with st.expander("🗂️ 管理分類"):
            new_cat = st.text_input("新增分類名稱", value=st.session_state.new_category_name, key="new_cat_input")
            if st.button("新增分類", key="add_cat_btn") and new_cat.strip():
                new_val = new_cat.strip()
                merged_cats = sorted(set(st.session_state.saved_categories + [new_val]))
                st.session_state.saved_categories = merged_cats
                _save_saved_categories(merged_cats, st.session_state.db_path)
                st.session_state.selected_category = new_val
                st.session_state.new_category_name = ""
                st.rerun()
            if st.session_state.saved_categories:
                tags_html = "".join(
                    f"<span style='display:inline-block;background:#e0e7ff;color:#4f46e5;"
                    f"border-radius:12px;padding:0.15rem 0.7rem;margin:0.15rem;font-size:0.82rem;'>{c}</span>"
                    for c in st.session_state.saved_categories
                )
                st.markdown(f"<div style='margin-top:0.4rem;'>{tags_html}</div>", unsafe_allow_html=True)

        with st.expander("📚 目前分類單字清單"):
            all_cats = sorted(set([i.get("category", "未分類") for i in practice_items]) | set(st.session_state.saved_categories))
            default_idx = all_cats.index(selected_category) if selected_category in all_cats else 0
            list_category = st.selectbox("查看分類", options=all_cats, index=default_idx, key="word_list_cat")
            cat_items = [i for i in practice_items if i.get("category", "未分類") == list_category]
            if cat_items:
                for idx, item in enumerate(cat_items):
                    row_col, del_col = st.columns([9, 1])
                    with row_col:
                        ex = item.get("example", "")
                        if ex:
                            st.markdown(
                                f"<div style='padding:0.3rem 0;border-bottom:1px solid #f1f5f9;'>"
                                f"<b style='color:#4f46e5;'>{item['english']}</b>"
                                f" <span style='color:#374151;'>→ {item['translation']}</span>"
                                f"<br><span style='font-size:0.82rem;color:#6b7280;'>💬 {ex}</span></div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f"<div style='padding:0.3rem 0;border-bottom:1px solid #f1f5f9;'>"
                                f"<b style='color:#4f46e5;'>{item['english']}</b>"
                                f" <span style='color:#374151;'>→ {item['translation']}</span></div>",
                                unsafe_allow_html=True,
                            )
                    with del_col:
                        if st.button("🗑️", key=f"del_{idx}_{item['english']}"):
                            delete_translation_entry(item["english"], db_path=st.session_state.db_path)
                            st.success(f"已刪除 {item['english']}")
                            st.rerun()
            else:
                st.info("這個分類目前沒有單字。")

    # ── 字典查詢區塊 ────────────────────────────────────────────
    def _render_dictionary_section(self):
        search_query = st.text_input(
            "搜尋英文或中文",
            placeholder="例如：resilience 或 韌性",
            key="dict_search_input",
        )

        # 即時本機查詢
        if search_query.strip() and st.session_state.get("last_search_query") != search_query.strip():
            st.session_state.last_search_query = search_query.strip()
            local = resolve_translation_lookup(search_query.strip(), db_path=st.session_state.db_path)
            if local["source"] == "local":
                st.session_state.translation_result = {
                    "english": local["english"] or search_query.strip(),
                    "translation": local["translation"] or "（尚未取得）",
                    "example": local.get("example", ""),
                    "examples": local.get("examples", []),
                    "phonetic": local.get("phonetic", ""),
                }
                st.session_state.example_candidates = local.get("examples", [])
                st.rerun()

        if st.button("🔍 查詢翻譯", use_container_width=True, type="primary") and search_query.strip():
            with st.spinner("查詢本機資料庫與 AI 生成中…"):
                try:
                    local = resolve_translation_lookup(search_query.strip(), db_path=st.session_state.db_path)
                    if local["source"] == "local":
                        translation = local["translation"]
                        example_entries = local.get("examples", [])
                        first_example = example_entries[0]["english"] if example_entries else local.get("example", "")
                        phonetic = local.get("phonetic", "")
                    else:
                        llm = LLMFactory.get_llm(
                            st.session_state.provider,
                            model_name=st.session_state.model,
                            temperature=st.session_state.temperature,
                        )
                        prompt = (
                            f"請提供英文單字或片語 '{search_query.strip()}' 的詳細資訊。\n"
                            "格式（每行一項，嚴格照此輸出）：\n"
                            "中文意思：...\n"
                            "音標：/IPA音標/\n"
                            "例句1：英文例句｜中文：中文翻譯\n"
                            "例句2：英文例句｜中文：中文翻譯\n"
                            "例句3：英文例句｜中文：中文翻譯"
                        )
                        response = llm.invoke([HumanMessage(content=prompt)])
                        translation, _ = parse_llm_translation_response(response.content)
                        phonetic = parse_llm_phonetic_response(response.content)
                        example_entries = parse_llm_example_items(response.content, fallback_translation=translation)
                        if not example_entries:
                            sents = parse_llm_example_sentences(response.content)
                            example_entries = [{"english": s, "chinese": translation} for s in sents]
                        first_example = example_entries[0]["english"] if example_entries else ""
                    st.session_state.translation_result = {
                        "english": local["english"] or search_query.strip(),
                        "translation": translation or "（尚未取得）",
                        "example": first_example,
                        "examples": example_entries,
                        "phonetic": phonetic,
                    }
                    st.session_state.example_candidates = example_entries
                    st.session_state.last_search_query = search_query.strip()
                    st.rerun()
                except Exception as exc:
                    st.error(f"查詢失敗：{exc}")

        if st.session_state.translation_result:
            result = st.session_state.translation_result

            # 音標
            phonetic = result.get("phonetic", "")
            phonetic_html = (
                f" <span style='font-size:1rem;color:#818cf8;font-family:serif;"
                f"letter-spacing:0.04em;'>{phonetic}</span>"
                if phonetic else ""
            )

            # 查詢結果卡片
            st.markdown(
                f"<div style='background:#fff;border:1.5px solid #c7d2fe;border-radius:16px;"
                f"padding:1.2rem 1.4rem;margin:0.6rem 0;box-shadow:0 4px 14px rgba(99,102,241,0.08);'>"
                f"<div style='font-size:1.4rem;font-weight:800;color:#1e1b4b;'>"
                f"{result['english']}{phonetic_html}</div>"
                f"<div style='font-size:1rem;color:#4b5563;margin-top:0.3rem;'>{result['translation']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # TTS 發音按鈕
            _render_tts_component(result["english"], component_key="tts_dict")

            with st.container():
                st.text_input("英文", value=result["english"], key="dictionary_english")
                d_col1, d_col2 = st.columns([3, 2])
                with d_col1:
                    st.text_area("中文意思", value=result["translation"], key="dictionary_translation", height=70)
                with d_col2:
                    st.text_input("IPA 音標", value=result.get("phonetic", ""), key="dictionary_phonetic",
                                  placeholder="/rɪˈzɪliəns/")
                col_ex, col_cht = st.columns(2)
                with col_ex:
                    st.text_area("主要例句", value=result.get("example", ""), key="dictionary_example", height=80)
                with col_cht:
                    first_chinese = (result.get("examples") or [{}])[0].get("chinese", "")
                    st.text_area("例句中文翻譯", value=first_chinese, key="dictionary_example_translation", height=80)

            # 例句列表
            if st.session_state.example_candidates:
                st.markdown(
                    "<div style='font-size:0.85rem;font-weight:600;color:#6366f1;margin:0.5rem 0 0.3rem;'>例句清單</div>",
                    unsafe_allow_html=True,
                )
                for idx, ex in enumerate(st.session_state.example_candidates, 1):
                    en = ex.get("english", "") if isinstance(ex, dict) else ex
                    zh = ex.get("chinese", "") if isinstance(ex, dict) else ""
                    st.markdown(
                        f"<div style='background:#f8faff;border-left:3px solid #a5b4fc;border-radius:6px;"
                        f"padding:0.45rem 0.8rem;margin-bottom:0.35rem;font-size:0.87rem;'>"
                        f"<span style='color:#1e1b4b;'>{idx}. {en}</span>"
                        + (f"<br><span style='color:#6b7280;font-size:0.82rem;'>　{zh}</span>" if zh else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )

            act_col1, act_col2, act_col3 = st.columns(3)
            with act_col1:
                if st.button("➕ 加入單字本", use_container_width=True, type="primary"):
                    example_entries = merge_example_items(
                        {"english": st.session_state.dictionary_example,
                         "chinese": st.session_state.dictionary_example_translation},
                        st.session_state.example_candidates,
                        fallback_translation=st.session_state.dictionary_translation,
                    )
                    save_translation_entry(
                        st.session_state.dictionary_english,
                        st.session_state.dictionary_translation,
                        serialize_example_items(example_entries),
                        category=st.session_state.selected_category,
                        db_path=st.session_state.db_path,
                        phonetic=st.session_state.get("dictionary_phonetic", ""),
                    )
                    st.session_state.translation_result["examples"] = example_entries
                    st.session_state.example_candidates = example_entries
                    st.success(f"已加入「{st.session_state.selected_category}」單字本 ✓")
                    st.rerun()
            with act_col2:
                if st.button("🎤 練習發音", use_container_width=True):
                    st.session_state.pron_test_word = st.session_state.translation_result["english"]
                    st.session_state.show_pron_test = True
                    st.rerun()
            with act_col3:
                if st.button("🧠 生成更多例句", use_container_width=True):
                    with st.spinner("AI 生成例句中…"):
                        try:
                            llm = LLMFactory.get_llm(
                                st.session_state.provider,
                                model_name=st.session_state.model,
                                temperature=st.session_state.temperature,
                            )
                            prompt = (
                                f"請為英文單字或片語 '{st.session_state.dictionary_english}' 生成 3 個自然的英文例句，"
                                "每行格式：例句：英文內容｜中文：中文翻譯"
                            )
                            resp = llm.invoke([HumanMessage(content=prompt)])
                            gen = parse_llm_example_items(resp.content, fallback_translation=st.session_state.dictionary_translation)
                            if not gen:
                                gen = [{"english": s, "chinese": st.session_state.dictionary_translation}
                                       for s in parse_llm_example_sentences(resp.content)]
                            merged = merge_example_items(
                                {"english": st.session_state.dictionary_example,
                                 "chinese": st.session_state.dictionary_example_translation},
                                st.session_state.example_candidates + gen,
                                fallback_translation=st.session_state.dictionary_translation,
                            )
                            st.session_state.example_candidates = merged
                            st.session_state.translation_result["examples"] = merged
                            st.session_state.translation_result["example"] = merged[0]["english"] if merged else ""
                            st.success("已生成更多例句 ✓")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"生成例句失敗：{exc}")

            # 字典查詢發音測驗（由「練習發音」按鈕觸發）
            if (st.session_state.show_pron_test and
                    st.session_state.pron_test_word == st.session_state.translation_result.get("english", "")):
                st.markdown(
                    "<div style='font-size:0.9rem;font-weight:600;color:#d97706;margin:0.8rem 0 0.3rem;'>"
                    "🎤 即時發音練習</div>",
                    unsafe_allow_html=True,
                )
                _render_pronunciation_test(
                    st.session_state.pron_test_word,
                    component_key="pron_dict",
                )
                if st.button("✖ 關閉", key="close_pron_dict"):
                    st.session_state.show_pron_test = False
                    st.rerun()

        # 手動新增表單
        st.markdown(
            "<div style='font-size:0.85rem;font-weight:600;color:#6366f1;margin:1rem 0 0.3rem;'>✏️ 手動新增單字</div>",
            unsafe_allow_html=True,
        )
        with st.form("translation_form", clear_on_submit=True):
            categories = sorted(set(st.session_state.saved_categories + [st.session_state.selected_category]))
            selected_save_cat = st.selectbox(
                "分類",
                options=categories,
                index=max(0, categories.index(st.session_state.selected_category))
                if st.session_state.selected_category in categories else 0,
            )
            f1, f2 = st.columns(2)
            with f1:
                english_phrase = st.text_input("英文", placeholder="resilience",
                                               value=(st.session_state.translation_result or {}).get("english", ""))
            with f2:
                translation_phrase = st.text_input("中文說明", placeholder="韌性、恢復力",
                                                   value=(st.session_state.translation_result or {}).get("translation", ""))
            ph_col, ex_col = st.columns(2)
            with ph_col:
                phonetic_manual = st.text_input(
                    "IPA 音標（選填）", placeholder="/rɪˈzɪliəns/",
                    value=(st.session_state.translation_result or {}).get("phonetic", "")
                )
            with ex_col:
                example_sentence = st.text_input("例句", placeholder="She showed great resilience.",
                                                 value=(st.session_state.translation_result or {}).get("example", ""))
            g1, g2 = st.columns(2)
            with g1:
                example_translation = st.text_input("例句中文翻譯", placeholder="她展現了極大的韌性。")
            with g2:
                pass  # 預留空間
            if st.form_submit_button("💾 儲存單字", use_container_width=True):
                if english_phrase.strip():
                    ex_items = [{"english": example_sentence.strip(),
                                 "chinese": example_translation.strip() or translation_phrase.strip()}]
                    save_translation_entry(
                        english_phrase.strip(), translation_phrase.strip(),
                        serialize_example_items(ex_items),
                        category=selected_save_cat,
                        db_path=st.session_state.db_path,
                        phonetic=phonetic_manual.strip(),
                    )
                    st.session_state.selected_category = selected_save_cat
                    st.success("✅ 已儲存到本機資料庫")
                    st.rerun()

    # ── TOEFL 測驗區塊 ──────────────────────────────────────────
    def _render_quiz_section(self):
        practice_items = list_english_practice_items(limit=8, db_path=st.session_state.db_path)

        if not st.session_state.quiz_question:
            quiz_data = build_quiz_question(practice_items)
            st.session_state.quiz_question = quiz_data["question"]
            st.session_state.quiz_options = quiz_data["options"]
            st.session_state.quiz_answer = quiz_data["answer"]
            st.session_state.quiz_result = None
            st.session_state.quiz_submitted = False

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#fffbeb 0%,#fef3c7 100%);"
            f"border:1.5px solid #fcd34d;border-radius:16px;padding:1.2rem 1.4rem;margin-bottom:0.8rem;"
            f"box-shadow:0 4px 14px rgba(251,191,36,0.1);'>"
            f"<div style='font-size:0.82rem;color:#92400e;font-weight:600;margin-bottom:0.3rem;'>請選擇最適合的中文意思</div>"
            f"<div style='font-size:1.6rem;font-weight:800;color:#1c1917;'>{st.session_state.quiz_question}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        selected_answer = st.radio(
            "選項", st.session_state.quiz_options,
            key="quiz_choice", label_visibility="collapsed",
        )

        if not st.session_state.quiz_submitted:
            if st.button("📝 提交答案", use_container_width=True, type="primary"):
                is_correct = selected_answer == st.session_state.quiz_answer
                st.session_state.quiz_result = is_correct
                st.session_state.quiz_submitted = True
                record_study_session("toefl", 1 if is_correct else 0, 1, db_path=st.session_state.db_path)
                st.rerun()
        else:
            if st.session_state.quiz_result:
                st.success("🎉 答對了！答案正確。")
            else:
                st.error(f"❌ 答錯了，正確答案是：**{st.session_state.quiz_answer}**")
            if st.button("➡️ 下一題", use_container_width=True):
                st.session_state.quiz_question = None
                st.session_state.quiz_options = []
                st.session_state.quiz_answer = None
                st.session_state.quiz_result = None
                st.session_state.quiz_submitted = False
                st.rerun()

    # ── 發音測驗區塊 ────────────────────────────────────────────
    def _render_pronunciation_section(self):
        practice_items = list_english_practice_items(limit=100, db_path=st.session_state.db_path)
        st.caption("選擇單字，聽示範發音後跟著朗讀，系統自動比對並給分（需 Chrome / Edge，且允許麥克風）。")

        col_word, col_random = st.columns([4, 1])
        with col_word:
            word_options = [item["english"] for item in practice_items] if practice_items else []
            if word_options:
                # 預設選取 pron_test_word（若存在）
                default_idx = 0
                if st.session_state.pron_test_word in word_options:
                    default_idx = word_options.index(st.session_state.pron_test_word)
                selected_word = st.selectbox(
                    "選擇要練習的單字",
                    options=word_options,
                    index=default_idx,
                    key="pron_word_select",
                )
            else:
                selected_word = st.text_input("輸入要練習的單字", value="hello", key="pron_word_input")
        with col_random:
            st.markdown("<div style='height:1.8rem;'></div>", unsafe_allow_html=True)
            if st.button("🎲 隨機", use_container_width=True) and word_options:
                selected_word = random.choice(word_options)
                st.session_state.pron_test_word = selected_word
                st.rerun()

        # 顯示音標
        phonetic = ""
        if practice_items:
            matched = next((item for item in practice_items if item["english"] == selected_word), None)
            if matched:
                phonetic = matched.get("phonetic", "")
        if phonetic:
            st.markdown(
                f"<span style='font-size:1rem;color:#818cf8;font-family:serif;"
                f"background:#eef2ff;border-radius:8px;padding:0.2rem 0.7rem;"
                f"letter-spacing:0.04em;'>{phonetic}</span>",
                unsafe_allow_html=True,
            )

        if selected_word:
            _render_pronunciation_test(selected_word, component_key="pron_main")

    # ── 學習成效 & 趨勢區塊 ─────────────────────────────────────
    def _render_stats_section(self):
        sessions = list_study_sessions(limit=8, db_path=st.session_state.db_path)
        if not sessions:
            st.info("目前還沒有測驗紀錄，先做一次測驗吧！")
            return

        total_score = sum(i["score"] for i in sessions)
        total_tests = sum(i["total"] for i in sessions)
        avg_acc = round(total_score / total_tests, 2) if total_tests else 0.0

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 100%);"
            f"border:1.5px solid #86efac;border-radius:14px;padding:0.9rem 1.2rem;"
            f"margin-bottom:0.8rem;display:inline-block;'>"
            f"<span style='font-size:0.85rem;color:#166534;font-weight:600;'>最近 8 次平均準確率　</span>"
            f"<span style='font-size:1.5rem;font-weight:800;color:#15803d;'>{avg_acc * 100:.0f}%</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        rows_html = "".join(
            f"<tr style='border-bottom:1px solid #f1f5f9;'>"
            f"<td style='padding:0.35rem 0.6rem;color:#6b7280;font-size:0.82rem;'>{i['created_at'][:10]}</td>"
            f"<td style='padding:0.35rem 0.6rem;font-size:0.82rem;'>{i['test_type']}</td>"
            f"<td style='padding:0.35rem 0.6rem;font-weight:600;color:#4f46e5;'>{i['score']}/{i['total']}</td>"
            f"<td style='padding:0.35rem 0.6rem;font-weight:600;color:#10b981;'>{i['accuracy'] * 100:.0f}%</td>"
            f"</tr>"
            for i in sessions
        )
        st.markdown(
            f"<div style='border:1.5px solid #e0e7ff;border-radius:12px;overflow:hidden;margin-bottom:1rem;'>"
            f"<table style='width:100%;border-collapse:collapse;'>"
            f"<thead><tr style='background:#eef2ff;'>"
            f"<th style='padding:0.5rem 0.6rem;text-align:left;font-size:0.82rem;color:#4338ca;'>日期</th>"
            f"<th style='padding:0.5rem 0.6rem;text-align:left;font-size:0.82rem;color:#4338ca;'>類型</th>"
            f"<th style='padding:0.5rem 0.6rem;text-align:left;font-size:0.82rem;color:#4338ca;'>答對/總題</th>"
            f"<th style='padding:0.5rem 0.6rem;text-align:left;font-size:0.82rem;color:#4338ca;'>準確率</th>"
            f"</tr></thead><tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True,
        )

        # 趨勢圖
        trend_sessions = list_study_sessions(limit=30, db_path=st.session_state.db_path)
        if trend_sessions:
            trend_rows: list = []
            for item in trend_sessions:
                day = item["created_at"][:10]
                existing = next((r for r in trend_rows if r["date"] == day), None)
                if existing is None:
                    trend_rows.append({"date": day, "score": item["score"], "total": item["total"], "accuracy": item["accuracy"]})
                else:
                    existing["score"] += item["score"]
                    existing["total"] += item["total"]
                    existing["accuracy"] = round((existing["accuracy"] + item["accuracy"]) / 2, 2)
            trend_rows = sorted(trend_rows, key=lambda r: r["date"])

            t1, t2 = st.tabs(["📈 每日準確率", "📊 每日題數"])
            with t1:
                st.line_chart({"準確率": [r["accuracy"] for r in trend_rows]})
            with t2:
                st.bar_chart({"題數": [r["total"] for r in trend_rows]})
