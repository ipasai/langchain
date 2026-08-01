import json
import random
import js
from datetime import datetime
from chat import call_llm

active_flashcard_list = []
active_flashcard_index = 0
current_quiz_answer = ""
current_quiz_question = ""

def refresh_english_practice_metrics(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM english_practice WHERE english NOT LIKE 'dummy-%'")
    vocab_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*), AVG(accuracy) FROM study_sessions")
    row = cursor.fetchone()
    quiz_count = row[0] or 0
    avg_accuracy = row[1] or 0.0
    
    js.document.getElementById("metric-word-count").innerText = str(vocab_count)
    js.document.getElementById("metric-quiz-count").innerText = str(quiz_count)
    js.document.getElementById("metric-accuracy").innerText = f"{avg_accuracy*100:.0f}%"
    
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM daily_review WHERE review_date = ?", (today_str,))
    reviewed_today = cursor.fetchone()[0] > 0
    
    panel = js.document.getElementById("review-reminder-panel")
    msg = js.document.getElementById("review-reminder-msg")
    btn = js.document.getElementById("btn-mark-review-completed")
    
    if reviewed_today:
        msg.innerHTML = '<span style="color:var(--color-emerald); font-weight:600;"><i class="fa-solid fa-circle-check"></i> 今日已完成單字複習！持續保持科學學習習慣。</span>'
        btn.disabled = True
        btn.style.opacity = "0.5"
    else:
        msg.innerHTML = '<span style="color:var(--color-amber); font-weight:600;"><i class="fa-solid fa-bell"></i> 今日尚未標記完成複習，別忘了進行每日 Flashcards 卡片複習！</span>'
        btn.disabled = False
        btn.style.opacity = "1"
        
    refresh_vocabulary_categories_selectors(db_conn)
    refresh_flashcard_view(db_conn)
    draw_study_charts(db_conn)

def mark_daily_review_complete(event, db_conn, show_toast_fn):
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO daily_review (review_date, created_at) VALUES (?,?)",
                   (today_str, datetime.utcnow().isoformat()))
    db_conn.commit()
    show_toast_fn("今日複習紀錄已標記完成！")
    refresh_english_practice_metrics(db_conn)

def refresh_vocabulary_categories_selectors(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM english_practice WHERE category IS NOT NULL AND category != ''")
    categories = [r[0] for r in cursor.fetchall()]
    if "未分類" not in categories:
        categories.insert(0, "未分類")
        
    card_cat_select = js.document.getElementById("vocab-card-category-select")
    add_cat_select = js.document.getElementById("vocab-add-category-select")
    list_cat_select = js.document.getElementById("cat-view-list-select")
    
    for select_el in [card_cat_select, add_cat_select, list_cat_select]:
        if not select_el:
            continue
        current_val = select_el.value
        select_el.innerHTML = ""
        
        if select_el == card_cat_select or select_el == list_cat_select:
            all_opt = js.document.createElement("option")
            all_opt.value = "所有單字"
            all_opt.innerText = "所有單字"
            select_el.appendChild(all_opt)
            
        for cat in categories:
            opt = js.document.createElement("option")
            opt.value = cat
            opt.innerText = cat
            select_el.appendChild(opt)
            
        if current_val:
            select_el.value = current_val

    labels = js.document.getElementById("cat-list-labels")
    if labels:
        labels.innerText = ", ".join(categories)
        
    refresh_category_words_list(db_conn)

def add_custom_category(event, db_conn, show_toast_fn):
    inp = js.document.getElementById("cat-add-input")
    cat_name = inp.value.strip()
    if not cat_name:
        show_toast_fn("請輸入分類名稱", is_success=False)
        return
        
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO english_practice (english, translation, example, category, created_at) VALUES (?,?,?,?,?)",
                   (f"dummy-{random.randint(1000,9999)}", "分類標記", "", cat_name, datetime.utcnow().isoformat()))
    db_conn.commit()
    
    inp.value = ""
    show_toast_fn(f"成功建立 [{cat_name}] 分類！")
    refresh_vocabulary_categories_selectors(db_conn)

def refresh_category_words_list(db_conn, event=None):
    cat_select = js.document.getElementById("cat-view-list-select")
    if not cat_select:
        return
    cat = cat_select.value
    
    cursor = db_conn.cursor()
    if cat == "所有單字" or not cat:
        cursor.execute("SELECT id, english, translation, example FROM english_practice WHERE english NOT LIKE 'dummy-%' ORDER BY id DESC")
    else:
        cursor.execute("SELECT id, english, translation, example FROM english_practice WHERE category = ? AND english NOT LIKE 'dummy-%' ORDER BY id DESC", (cat,))
        
    rows = cursor.fetchall()
    tbody = js.document.getElementById("cat-words-tbody-list")
    tbody.innerHTML = ""
    
    if not rows:
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:15px; color:var(--text-secondary);">該分類下尚無單字數據。</td></tr>'
        return
        
    for r in rows:
        word_id, eng, trans, ex = r[0], r[1], r[2], r[3] or ""
        tr = js.document.createElement("tr")
        tr.innerHTML = f"""
            <td><strong>{eng}</strong></td>
            <td>{trans}</td>
            <td><small>{ex}</small></td>
            <td style="text-align:center;">
                <button class="btn btn-danger btn-del-word" style="padding:4px 8px; font-size:0.8rem;" data-id="{word_id}">🗑️</button>
            </td>
        """
        tbody.appendChild(tr)

    def on_del_btn_click(evt):
        target = evt.target
        w_id = target.getAttribute("data-id")
        if w_id:
            cursor.execute("DELETE FROM english_practice WHERE id = ?", (w_id,))
            db_conn.commit()
            refresh_english_practice_metrics(db_conn)
            
    for btn in js.document.querySelectorAll(".btn-del-word"):
        btn.addEventListener("click", js.create_proxy(on_del_btn_click))

def refresh_flashcard_view(db_conn):
    global active_flashcard_list, active_flashcard_index
    cat = js.document.getElementById("vocab-card-category-select").value
    
    cursor = db_conn.cursor()
    if cat == "所有單字" or not cat:
        cursor.execute("SELECT id, english, translation, example FROM english_practice WHERE english NOT LIKE 'dummy-%' ORDER BY id ASC")
    else:
        cursor.execute("SELECT id, english, translation, example FROM english_practice WHERE category = ? AND english NOT LIKE 'dummy-%' ORDER BY id ASC", (cat,))
        
    active_flashcard_list = cursor.fetchall()
    
    inner = js.document.getElementById("flashcard-inner")
    inner.classList.remove("flipped")
    
    if not active_flashcard_list:
        js.document.getElementById("card-index-label").innerText = "卡片 0/0"
        js.document.getElementById("card-front-word").innerText = "尚無單字數據"
        js.document.getElementById("card-back-translation").innerText = "請新增或使用 AI 生成生字"
        js.document.getElementById("card-back-example").innerText = ""
        return

    if active_flashcard_index >= len(active_flashcard_list):
        active_flashcard_index = 0

    card = active_flashcard_list[active_flashcard_index]
    js.document.getElementById("card-index-label").innerText = f"卡片 {active_flashcard_index + 1}/{len(active_flashcard_list)}"
    
    direction = "english"
    radios = js.document.querySelectorAll('input[name="display-direction"]')
    for r in radios:
        if r.checked:
            direction = r.value

    if direction == "english":
        js.document.getElementById("card-front-word").innerText = card[1]
        js.document.getElementById("card-back-translation").innerText = card[2]
    else:
        js.document.getElementById("card-front-word").innerText = card[2]
        js.document.getElementById("card-back-translation").innerText = card[1]

    ex_text = card[3] or ""
    if "｜" in ex_text:
        parts = ex_text.split("｜")
        js.document.getElementById("card-back-example").innerHTML = f"<strong>例句：</strong>{parts[0]}<br><small style='color:var(--text-secondary);'>{parts[1]}</small>"
    else:
        js.document.getElementById("card-back-example").innerText = ex_text

def toggle_card_flip(event=None):
    inner = js.document.getElementById("flashcard-inner")
    inner.classList.toggle("flipped")

def reveal_card_answer(event=None):
    toggle_card_flip()

def card_next(db_conn, event=None):
    global active_flashcard_index
    if active_flashcard_list:
        active_flashcard_index = (active_flashcard_index + 1) % len(active_flashcard_list)
        refresh_flashcard_view(db_conn)

def card_prev(db_conn, event=None):
    global active_flashcard_index
    if active_flashcard_list:
        active_flashcard_index = (active_flashcard_index - 1 + len(active_flashcard_list)) % len(active_flashcard_list)
        refresh_flashcard_view(db_conn)

def record_card_feedback(remember, db_conn, show_toast_fn):
    score = 1 if remember else 0
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO study_sessions (test_type, score, total, accuracy, created_at) VALUES (?,?,?,?,?)",
                   ("card_review", score, 1, float(score), datetime.utcnow().isoformat()))
    db_conn.commit()
    msg = "記住了！表現優良 👍" if remember else "已標記為需再複習 💪"
    show_toast_fn(msg)
    card_next(db_conn)

def handle_card_remember(event, db_conn, show_toast_fn):
    record_card_feedback(True, db_conn, show_toast_fn)

def handle_card_review_need(event, db_conn, show_toast_fn):
    record_card_feedback(False, db_conn, show_toast_fn)

def collect_card_to_category(event, db_conn, show_toast_fn):
    global active_flashcard_list, active_flashcard_index
    if not active_flashcard_list or active_flashcard_index >= len(active_flashcard_list):
        show_toast_fn("無可收藏之卡片", is_success=False)
        return
    card = active_flashcard_list[active_flashcard_index]
    word_id = card[0]
    cat = js.document.getElementById("vocab-card-category-select").value or "未分類"
    
    cursor = db_conn.cursor()
    cursor.execute("UPDATE english_practice SET category = ? WHERE id = ?", (cat, word_id))
    db_conn.commit()
    show_toast_fn(f"卡片 [{card[1]}] 已成功加入至 [{cat}] 分類！")
    refresh_flashcard_view(db_conn)

async def run_dict_lookup(event, db_conn, show_toast_fn):
    query = js.document.getElementById("dict-search-input").value.strip()
    if not query:
        show_toast_fn("請輸入搜尋字彙或片語", is_success=False)
        return

    panel = js.document.getElementById("dict-search-result-panel")
    panel.style.display = "flex"
    
    js.document.getElementById("dict-res-english").value = query
    js.document.getElementById("dict-res-translation").value = "查詢中..."
    js.document.getElementById("dict-res-example").value = ""
    js.document.getElementById("dict-res-example-trans").value = ""
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT translation, example FROM english_practice WHERE english LIKE ? OR translation LIKE ? LIMIT 1",
                   (f"%{query}%", f"%{query}%"))
    local_row = cursor.fetchone()
    
    if local_row:
        js.document.getElementById("dict-res-translation").value = local_row[0]
        ex_text = local_row[1] or ""
        eng_ex, chi_ex = "", ""
        if "｜" in ex_text:
            parts = ex_text.split("｜")
            eng_ex = parts[0].strip()
            chi_ex = parts[1].strip()
        else:
            eng_ex = ex_text
        
        js.document.getElementById("dict-res-example").value = eng_ex
        js.document.getElementById("dict-res-example-trans").value = chi_ex
        show_toast_fn("本機資料庫查詢成功")
    else:
        provider = js.document.getElementById("ai-provider").value
        model = js.document.getElementById("ai-model").value
        temp = js.document.getElementById("ai-temp").value
        
        prompt = f"""請提供英文單字或片語 '{query}' 的中文意思，並附上一個自然的英文例句與對應中文翻譯。
格式請固定如下：
中文意思：[中文說明]
例句：[英文例句] ｜ 中文翻譯：[中文翻譯]"""

        try:
            ai_response = await call_llm(provider, model, temp, "你是一位專業的英文單字字典助手。", prompt)
            
            translation, example, translation_example = "", "", ""
            for line in ai_response.splitlines():
                if "中文意思：" in line:
                    translation = line.split("中文意思：", 1)[1].strip()
                elif "例句：" in line:
                    val = line.split("例句：", 1)[1].strip()
                    if "｜" in val:
                        p = val.split("｜")
                        example = p[0].strip()
                        translation_example = p[1].replace("中文翻譯：", "").strip()
                    else:
                        example = val

            js.document.getElementById("dict-res-translation").value = translation or ai_response.strip()
            js.document.getElementById("dict-res-example").value = example
            js.document.getElementById("dict-res-example-trans").value = translation_example
            show_toast_fn("AI 字典查詢生成成功")
        except Exception as e:
            js.document.getElementById("dict-res-translation").value = f"查詢失敗: {e}"

async def generate_multiple_examples(event, show_toast_fn):
    eng = js.document.getElementById("dict-res-english").value.strip()
    trans = js.document.getElementById("dict-res-translation").value.strip()
    if not eng:
        show_toast_fn("請先執行字典查詢", is_success=False)
        return
        
    container = js.document.getElementById("dict-additional-examples-container")
    list_box = js.document.getElementById("dict-additional-examples-list")
    container.style.display = "flex"
    list_box.innerHTML = '<div class="spinner-inline"></div> AI 正在生成多個例句中...'
    
    provider = js.document.getElementById("ai-provider").value
    model = js.document.getElementById("ai-model").value
    temp = js.document.getElementById("ai-temp").value
    
    prompt = f"""請為英文單字/片語 '{eng}' (中文意思：{trans}) 生成 3 個生動自然的全新英文例句，並附上對應中文翻譯。
格式固定為：
例句：英文例句 ｜ 中文翻譯"""
    
    try:
        resp = await call_llm(provider, model, temp, "你是一位專業的英文語言教學助手。", prompt)
        lines = [l.strip() for l in resp.splitlines() if "例句：" in l or "｜" in l]
        if not lines:
            lines = [l.strip() for l in resp.splitlines() if l.strip()]
            
        list_box.innerHTML = ""
        ex_items = []
        for line in lines:
            val = line.replace("例句：", "").strip()
            item_div = js.document.createElement("div")
            item_div.style.background = "rgba(255,255,255,0.05)"
            item_div.style.padding = "8px 12px"
            item_div.style.borderRadius = "8px"
            item_div.innerText = f"• {val}"
            list_box.appendChild(item_div)
            ex_items.append(val)
            
        existing_ex = js.document.getElementById("dict-res-example").value.strip()
        new_merged = existing_ex + ("\n" if existing_ex else "") + "\n".join(ex_items)
        js.document.getElementById("dict-res-example").value = new_merged
        show_toast_fn("多例句生成成功！")
    except Exception as e:
        list_box.innerHTML = f'<div style="color:var(--color-crimson);">生成失敗: {e}</div>'

def save_word_from_dict(event, db_conn, show_toast_fn):
    eng = js.document.getElementById("dict-res-english").value.strip()
    trans = js.document.getElementById("dict-res-translation").value.strip()
    ex_eng = js.document.getElementById("dict-res-example").value.strip()
    ex_trans = js.document.getElementById("dict-res-example-trans").value.strip()
    cat = js.document.getElementById("vocab-card-category-select").value or "未分類"

    if not eng or not trans:
        show_toast_fn("英文與中文意思不能為空", is_success=False)
        return

    ex_field = f"{ex_eng}｜{ex_trans}" if ex_eng else ""
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO english_practice (english, translation, example, category, created_at) VALUES (?,?,?,?,?)",
                   (eng, trans, ex_field, cat, datetime.utcnow().isoformat()))
    db_conn.commit()
    
    show_toast_fn(f"單字 {eng} 已成功存入 {cat} 分類！")
    refresh_english_practice_metrics(db_conn)

def save_single_word_manual(event, db_conn, show_toast_fn):
    cat = js.document.getElementById("vocab-add-category-select").value
    eng = js.document.getElementById("vocab-add-english").value.strip()
    trans = js.document.getElementById("vocab-add-translation").value.strip()
    ex_eng = js.document.getElementById("vocab-add-example").value.strip()
    ex_trans = js.document.getElementById("vocab-add-example-trans").value.strip()

    if not eng or not trans:
        show_toast_fn("請填寫英文單字與中文翻譯", is_success=False)
        return

    ex_field = f"{ex_eng}｜{ex_trans}" if ex_eng else ""
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO english_practice (english, translation, example, category, created_at) VALUES (?,?,?,?,?)",
                   (eng, trans, ex_field, cat, datetime.utcnow().isoformat()))
    db_conn.commit()
    
    js.document.getElementById("vocab-add-english").value = ""
    js.document.getElementById("vocab-add-translation").value = ""
    js.document.getElementById("vocab-add-example").value = ""
    js.document.getElementById("vocab-add-example-trans").value = ""

    show_toast_fn("單字已成功儲存！")
    refresh_english_practice_metrics(db_conn)

async def run_vocab_auto_generation(event, db_conn, show_toast_fn):
    theme = js.document.getElementById("vocab-gen-theme").value
    level = js.document.getElementById("vocab-gen-level").value
    count = int(js.document.getElementById("vocab-gen-count").value)
    
    btn = js.document.getElementById("btn-vocab-auto-generate")
    original_html = btn.innerHTML
    btn.innerHTML = '<div class="spinner-inline"></div> AI 生成與寫入中...'
    btn.disabled = True

    prompt = f"""請生成 {count} 個適合 {level} 程度的「{theme}」英文單字或常用片語。
請嚴格以下方的 JSON 陣列格式回傳，不可包含 Markdown 標記：

[
  {{
    "english": "單字或片語",
    "translation": "中文意思說明",
    "example": "英文例句 ｜ 中文翻譯"
  }}
]"""

    provider = js.document.getElementById("ai-provider").value
    model = js.document.getElementById("ai-model").value
    temp = js.document.getElementById("ai-temp").value

    try:
        raw_response = await call_llm(provider, model, temp, "你是一位專業的英文語言教學助手。", prompt)
        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            lines = clean_json.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_json = "\n".join(lines).strip()

        vocab_list = json.loads(clean_json)
        cursor = db_conn.cursor()
        added_count = 0
        for item in vocab_list:
            eng = item.get("english", "").strip()
            trans = item.get("translation", "").strip()
            ex = item.get("example", "").strip()
            if eng and trans:
                cursor.execute("INSERT INTO english_practice (english, translation, example, category, created_at) VALUES (?,?,?,?,?)",
                               (eng, trans, ex, theme, datetime.utcnow().isoformat()))
                added_count += 1
        db_conn.commit()
        
        show_toast_fn(f"成功自動生成並匯入 {added_count} 個單字至 {theme} 分類！")
        refresh_english_practice_metrics(db_conn)
    except Exception as e:
        show_toast_fn(f"AI 生成失敗: {e}", is_success=False)
    finally:
        btn.innerHTML = original_html
        btn.disabled = False

def render_new_quiz_question(db_conn):
    global current_quiz_answer, current_quiz_question
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT english, translation FROM english_practice")
    rows = [r for r in cursor.fetchall() if not r[0].startswith("dummy-")]
    
    container = js.document.getElementById("quiz-options-list")
    container.innerHTML = ""
    js.document.getElementById("quiz-result-feedback").style.display = "none"
    js.document.getElementById("btn-quiz-submit").style.display = "inline-flex"
    js.document.getElementById("btn-quiz-next").style.display = "none"

    if len(rows) < 2:
        js.document.getElementById("quiz-question-text").innerText = "請先在庫中建立至少 2 個以上的單字以啟動 TOEFL 測驗。"
        js.document.getElementById("btn-quiz-submit").disabled = True
        return

    js.document.getElementById("btn-quiz-submit").disabled = False
    
    sample = random.choice(rows)
    current_quiz_question = sample[0]
    current_quiz_answer = sample[1]
    
    js.document.getElementById("quiz-question-text").innerText = f"請選擇最適合的中文意思： {current_quiz_question}"
    
    distractors = [r[1] for r in rows if r[1] != current_quiz_answer]
    if len(distractors) < 3:
        distractors += ["請重新練習", "這是測驗示例", "請稍後再試"]
    
    options = [current_quiz_answer] + random.sample(distractors, k=min(3, len(distractors)))
    random.shuffle(options)
    
    for idx, opt in enumerate(options):
        lbl = js.document.createElement("label")
        lbl.className = "quiz-option-label"
        lbl.innerHTML = f'<input type="radio" name="quiz-ans-opt" value="{opt}"> <span>{opt}</span>'
        
        def make_option_click_handler(element):
            def handler(evt):
                for el in js.document.querySelectorAll(".quiz-option-label"):
                    el.classList.remove("selected")
                element.classList.add("selected")
            return handler
        lbl.addEventListener("click", js.create_proxy(make_option_click_handler(lbl)))
        container.appendChild(lbl)

def submit_quiz_answer(event, db_conn, show_toast_fn):
    selected_opt = js.document.querySelector('input[name="quiz-ans-opt"]:checked')
    if not selected_opt:
        show_toast_fn("請選擇一個選項", is_success=False)
        return
    
    ans = selected_opt.value
    is_correct = ans == current_quiz_answer
    
    feedback = js.document.getElementById("quiz-result-feedback")
    feedback.style.display = "block"
    
    score = 1 if is_correct else 0
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO study_sessions (test_type, score, total, accuracy, created_at) VALUES (?,?,?,?,?)",
                   ("toefl", score, 1, float(score), datetime.utcnow().isoformat()))
    db_conn.commit()
    
    if is_correct:
        feedback.style.background = "rgba(16, 185, 129, 0.15)"
        feedback.style.color = "var(--color-emerald)"
        feedback.innerHTML = '<i class="fa-solid fa-circle-check"></i> 恭喜答對了！'
    else:
        feedback.style.background = "rgba(239, 68, 68, 0.15)"
        feedback.style.color = "var(--color-crimson)"
        feedback.innerHTML = f'<i class="fa-solid fa-circle-xmark"></i> 答錯囉！正確答案是：<strong>{current_quiz_answer}</strong>'
    
    js.document.getElementById("btn-quiz-submit").style.display = "none"
    js.document.getElementById("btn-quiz-next").style.display = "inline-flex"
    refresh_english_practice_metrics(db_conn)

def draw_study_charts(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT created_at, score, total, accuracy FROM study_sessions ORDER BY id ASC")
    rows = cursor.fetchall()
    
    tbody = js.document.getElementById("study-trend-tbody")
    tbody.innerHTML = ""
    
    if not rows:
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:15px;">尚無測驗歷程數據以產生圖表。</td></tr>'
        return
        
    trend_map = {}
    for r in rows:
        date_str = r[0][:10]
        if date_str not in trend_map:
            trend_map[date_str] = {"score": 0, "total": 0}
        trend_map[date_str]["score"] += r[1]
        trend_map[date_str]["total"] += r[2]
        
    sorted_dates = sorted(list(trend_map.keys()))
    accuracies = [round(trend_map[d]["score"] / trend_map[d]["total"], 2) for d in sorted_dates]
    totals = [trend_map[d]["total"] for d in sorted_dates]
    
    for d in sorted_dates:
        tr = js.document.createElement("tr")
        acc_val = round(trend_map[d]["score"] / trend_map[d]["total"], 2)
        tr.innerHTML = f"""
            <td>{d}</td>
            <td>{trend_map[d]["score"]}</td>
            <td>{trend_map[d]["total"]}</td>
            <td>{acc_val*100:.0f}%</td>
        """
        tbody.appendChild(tr)
        
    js.window.updateCharts(sorted_dates, accuracies, totals)
