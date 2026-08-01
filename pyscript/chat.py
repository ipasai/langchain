import os
import json
import js
from datetime import datetime
from pyodide.http import pyfetch

PERSONA_PROMPTS = {
    "General Assistant": "你是一個親切且專業的 AI 助理，請用繁體中文回答問題。",
    "Coding Expert": "你是一位精通軟體開發與系統架構的程式專家。請提供乾淨、高效且有詳細註解的程式碼，並使用繁體中文解釋。",
    "Database Expert": "你是一位世界級資料庫專家(Database Expert)，精通 SQL、MySQL、PostgreSQL、SQL Server、Oracle、SQLite、MariaDB、MongoDB、Redis 與資料庫架構設計。請協助使用者設計資料模型、ERD、正規化/反正規化、SQL 查詢、Stored Procedure、Trigger、View、Function、Index、Partition、Transaction、Lock、Isolation Level、Execution Plan、Query Optimization、Replication、Backup/Restore、HA、Sharding、資料遷移與效能調校。回答時請提供完整 SQL 範例、最佳實務、可能的效能瓶頸及改善建議，並使用繁體中文說明。",
    "English Tutor": "You are an encouraging and professional English tutor. Help the user learn English by correcting grammar, explaining vocabulary, and providing natural example sentences. Respond in Traditional Chinese with English explanations."
}

async def call_llm(provider, model, temperature, system_prompt, prompt, history=[]):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": prompt})

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError("錯誤: 請在您的 .env 檔案中填寫正確的 OPENAI_API_KEY")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature)
        }
        response = await pyfetch("https://api.openai.com/v1/chat/completions", 
                                  method="POST", 
                                  headers=headers, 
                                  body=json.dumps(payload))
        if response.status != 200:
            err_msg = await response.string()
            raise Exception(f"HTTP {response.status}: {err_msg}")
        data = await response.json()
        return data["choices"][0]["message"]["content"]
        
    elif provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key or api_key == "your_google_ai_studio_api_key_here":
            raise ValueError("錯誤: 請在您的 .env 檔案中填寫正確的 GOOGLE_API_KEY")
        
        contents = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": float(temperature)
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        response = await pyfetch(url, 
                                  method="POST", 
                                  headers={"Content-Type": "application/json"}, 
                                  body=json.dumps(payload))
        if response.status != 200:
            err_msg = await response.string()
            raise Exception(f"HTTP {response.status}: {err_msg}")
        data = await response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
        
    else: # ollama (local)
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        url = f"{base_url.rstrip('/')}/api/chat"
        
        ollama_msgs = []
        for m in messages:
            role = "assistant" if m["role"] == "assistant" else m["role"]
            ollama_msgs.append({"role": role, "content": m["content"]})
            
        payload = {
            "model": model,
            "messages": ollama_msgs,
            "options": {
                "temperature": float(temperature)
            },
            "stream": False
        }
        try:
            response = await pyfetch(url, 
                                      method="POST", 
                                      headers={"Content-Type": "application/json"}, 
                                      body=json.dumps(payload))
            if response.status != 200:
                raise Exception(f"Ollama returned HTTP {response.status}")
            data = await response.json()
            return data["message"]["content"]
        except Exception as e:
            raise Exception(f"本地 Ollama 連線失敗！請確保 Ollama 服務已啟動且模型已下載 ({e})")

def refresh_chat_messages_ui(db_conn):
    container = js.document.getElementById("chat-messages-container")
    container.innerHTML = ""
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history ORDER BY id ASC")
    rows = cursor.fetchall()
    
    if not rows:
        welcome_div = js.document.createElement("div")
        welcome_div.className = "chat-message assistant"
        welcome_div.innerHTML = f"""
            <div class="avatar">🤖</div>
            <div class="message-content">
                👋 歡迎使用 <strong>LangChain 多模型 AI 助理</strong>！請在下方輸入您想與 AI 對話的內容。
            </div>
        """
        container.appendChild(welcome_div)
        return

    for role, content in rows:
        div = js.document.createElement("div")
        div.className = f"chat-message {role}"
        avatar = "👤" if role == "user" else "🤖"
        formatted = content.replace("\n", "<br>")
        div.innerHTML = f"""
            <div class="avatar">{avatar}</div>
            <div class="message-content">{formatted}</div>
        """
        container.appendChild(div)
        
    container.scrollTop = container.scrollHeight

async def send_chat_message(event, db_conn, show_toast_fn):
    input_el = js.document.getElementById("chat-input-prompt")
    prompt = input_el.value.strip()
    if not prompt:
        return
        
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO chat_history (role, content, created_at) VALUES (?,?,?)", 
                   ("user", prompt, datetime.utcnow().isoformat()))
    db_conn.commit()
    input_el.value = ""
    refresh_chat_messages_ui(db_conn)
    
    container = js.document.getElementById("chat-messages-container")
    loading_div = js.document.createElement("div")
    loading_div.className = "chat-message assistant"
    loading_div.innerHTML = '<div class="avatar">🤖</div><div class="message-content"><div class="spinner-inline"></div> 思考中...</div>'
    container.appendChild(loading_div)
    container.scrollTop = container.scrollHeight
    
    provider = js.document.getElementById("ai-provider").value
    model = js.document.getElementById("ai-model").value
    temp = js.document.getElementById("ai-temp").value
    
    persona = js.document.getElementById("ai-persona").value
    if persona == "Custom Prompt":
        system_prompt = js.document.getElementById("ai-custom-prompt").value
    else:
        system_prompt = PERSONA_PROMPTS.get(persona, "")

    cursor.execute("SELECT role, content FROM chat_history ORDER BY id DESC LIMIT 10")
    recent_rows = cursor.fetchall()
    history = []
    for r in reversed(recent_rows[:-1]):
        history.append({"role": r[0], "content": r[1]})

    try:
        response = await call_llm(provider, model, temp, system_prompt, prompt, history)
        loading_div.remove()
        cursor.execute("INSERT INTO chat_history (role, content, created_at) VALUES (?,?,?)", 
                       ("assistant", response, datetime.utcnow().isoformat()))
        db_conn.commit()
        refresh_chat_messages_ui(db_conn)
    except Exception as e:
        loading_div.remove()
        err_div = js.document.createElement("div")
        err_div.className = "chat-message assistant"
        err_div.style.border = "1px solid rgba(239, 68, 68, 0.4)"
        err_div.style.background = "rgba(239, 68, 68, 0.1)"
        err_div.innerHTML = f'<div class="avatar">❌</div><div class="message-content" style="color:var(--color-crimson);"><strong>Error:</strong> {str(e)}</div>'
        container.appendChild(err_div)
        container.scrollTop = container.scrollHeight

def clear_chat_history(event, db_conn, show_toast_fn):
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    db_conn.commit()
    refresh_chat_messages_ui(db_conn)
    show_toast_fn("對話歷史已成功清空！")
