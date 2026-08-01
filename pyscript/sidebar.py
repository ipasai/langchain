import os
import js
from pyodide.http import pyfetch

AVAILABLE_MODELS = {
    "ollama": ["llama3", "qwen2.5-coder:1.5b", "mistral", "neural-chat", "dolphin-mixtral"],
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "google": ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
}

async def fetch_ollama_models():
    try:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        url = f"{base_url.rstrip('/')}/api/tags"
        res = await pyfetch(url)
        if res.status == 200:
            data = await res.json()
            names = [m.get("name") for m in data.get("models", []) if m.get("name")]
            if names:
                return names
    except Exception:
        pass
    return AVAILABLE_MODELS["ollama"]

def update_summary_card(event=None):
    provider = js.document.getElementById("ai-provider").value
    model_el = js.document.getElementById("ai-model")
    model = model_el.value if model_el else ""
    temp = js.document.getElementById("ai-temp").value
    
    js.document.getElementById("summary-provider").innerText = provider.upper()
    js.document.getElementById("summary-model").innerText = model or "無"
    js.document.getElementById("summary-temp").innerText = str(temp)
    
    rec = "通用 AI 任務"
    m_lower = (model or "").lower()
    if "coder" in m_lower or "code" in m_lower:
        rec = "程式開發 / 代碼補全"
    elif "gemini-2.5-flash" in m_lower or "gpt-4o-mini" in m_lower:
        rec = "推薦：快速對話 / 綜合性價比"
    elif "gemini-1.5-pro" in m_lower or "gpt-4o" in m_lower:
        rec = "推薦：高級推理 / 程式 / 邏輯"
    elif "deepseek" in m_lower:
        rec = "推薦：深度推理 / 複雜邏輯"
    js.document.getElementById("summary-rec").innerText = rec

async def populate_models_dropdown(event=None):
    provider = js.document.getElementById("ai-provider").value
    models_dropdown = js.document.getElementById("ai-model")
    models_dropdown.innerHTML = ""
    
    if provider == "ollama":
        models = await fetch_ollama_models()
    else:
        models = AVAILABLE_MODELS.get(provider, [])
        
    for m in models:
        opt = js.document.createElement("option")
        opt.value = m
        recommendation = "通用 AI 任務"
        m_lower = m.lower()
        if "coder" in m_lower or "code" in m_lower:
            recommendation = "程式開發 / 代碼補全"
        elif "gemini-2.5-flash" in m_lower or "gpt-4o-mini" in m_lower:
            recommendation = "推薦：快速對話 / 綜合性價比"
        elif "gemini-1.5-pro" in m_lower or "gpt-4o" in m_lower:
            recommendation = "推薦：高級推理 / 程式 / 邏輯"
        elif "deepseek" in m_lower:
            recommendation = "推薦：深度推理 / 複雜邏輯"
        opt.innerText = f"{m} ({recommendation})"
        models_dropdown.appendChild(opt)
        
    update_summary_card()

def handle_temp_change(e):
    js.document.getElementById("temp-val-display").innerText = str(e.target.value)
    update_summary_card()

def handle_persona_change(e):
    p = e.target.value
    box = js.document.getElementById("custom-prompt-container")
    if p == "Custom Prompt":
        box.style.display = "block"
    else:
        box.style.display = "none"
