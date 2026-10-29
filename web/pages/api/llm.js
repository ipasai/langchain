import url from 'url'
import path from 'path'

function getOllamaModels(baseUrl) {
  const tagsUrl = `${baseUrl.replace(/\/$/, '')}/api/tags`
  return fetch(tagsUrl, { method: 'GET' }).then(r => r.json()).then(js => (js.models || []).map(m => m.name).filter(Boolean)).catch(() => ['llama3', 'mistral', 'neural-chat', 'dolphin-mixtral'])
}

function getModelRecommendation(modelName) {
  const name = (modelName || '').toLowerCase()
  if (name.includes(':cloud')) return '需登入 Ollama 雲端憑證'
  if (name.includes('embed')) return '向量嵌入 / 不適合對話'
  if (name.includes('1.5b') || name.includes('0.5b')) return '⚡ 輕量推薦 (筆電 CPU 順暢)'
  if (name.includes('7b') || name.includes('8b')) return '重量級 (7B~8B 需較大 RAM，本機 CPU 載入較慢)'
  if (name.includes('coder') || name.includes('code')) return '程式開發 / 編輯 / 代碼補全'
  if (name.includes('taiwan')) return '繁中對話 / 台灣在地知識'
  if (name.includes('deepseek')) return '深度推理 / Agent 代理 / 複雜邏輯'
  if (name.includes('kimi')) return '長文本處理 / 聯網搜尋'
  if (name.includes('glm')) return '多功能助理 / 中文對話'
  if (name.includes('minimax')) return '一般對話 / 角色扮演'
  if (name.includes('gemini-2.5-flash')) return '推薦：快速對話 / 多模態 / 綜合任務'
  if (name.includes('gemini-1.5-pro')) return '推薦：長文本分析 / 程式開發 / 複雜邏輯'
  if (name.includes('gemini-1.5-flash')) return '快速對話 / 輕量任務'
  if (name.includes('gpt-4o-mini')) return '推薦：快速對話 / 輕量任務 / 綜合性價比'
  if (name.includes('gpt-4o')) return '推薦：高級推理 / 程式開發 / 綜合任務'
  if (name.includes('gpt-4-turbo')) return '高級推理 / 綜合任務'
  if (name.includes('gpt-3.5')) return '舊版快速對話'
  if (name.includes('llama3')) return '一般對話 / 英文推理'
  if (name.includes('mistral')) return '一般對話 / 邏輯推理'
  if (name.includes('neural-chat') || name.includes('dolphin')) return '一般對話 / 角色扮演'
  return '通用 AI 任務'
}

function resolveTemperature(temperature) {
  if (typeof temperature !== 'undefined' && temperature !== null) return Number(temperature)
  const env = process.env.TEMPERATURE
  if (env) {
    const v = parseFloat(env)
    if (!Number.isNaN(v)) return v
  }
  return 0.7
}

function getFormattedModelName(name) {
  const rec = getModelRecommendation(name)
  return `${name} (${rec})`
}

const AVAILABLE_MODELS = {
  ollama: ['llama3', 'mistral', 'neural-chat', 'dolphin-mixtral'],
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  google: ['gemini-2.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
}

function getProviders() {
  return Object.keys(AVAILABLE_MODELS)
}

export default async function handler(req, res) {
  const query = url.parse(req.url, true).query || {}
  const action = (req.method === 'GET' ? query.action : (req.body && req.body.action)) || query.action

  if (action === 'get_recommendation') {
    const model = req.method === 'GET' ? query.model : (req.body && req.body.model) || ''
    return res.json({ model, recommendation: getModelRecommendation(model) })
  }

  if (action === 'get_models') {
    const provider = req.method === 'GET' ? query.provider : (req.body && req.body.provider) || 'ollama'
    if (provider === 'ollama') {
      const base = process.env.OLLAMA_BASE_URL || 'http://localhost:11434'
      const models = await getOllamaModels(base)
      return res.json({ provider, models: models.map(getFormattedModelName) })
    }
    // fallback: return simple defaults
    const defaults = AVAILABLE_MODELS[provider] || AVAILABLE_MODELS['openai']
    return res.json({ provider, models: defaults.map(getFormattedModelName) })
  }

  if (action === 'providers') {
    return res.json({ providers: getProviders(), defaults: AVAILABLE_MODELS })
  }

  if (action === 'chat') {
    const body = req.method === 'GET' ? query : (req.body || {})
    const provider = (body.provider || 'openai').toLowerCase()
    const model = body.model || process.env.OPENAI_MODEL || 'gpt-4o-mini'
    const temperature = resolveTemperature(body.temperature)
    let messages = body.messages
    if (!messages && body.prompt) messages = [{ role: 'user', content: body.prompt }]
    if (body.system_prompt) messages = [{ role: 'system', content: body.system_prompt }, ...(messages || [])]

    if (action === 'chat' && body.stream === true) {
      if (provider === 'openai') {
        const apiKey = process.env.OPENAI_API_KEY
        if (!apiKey) return res.status(400).json({ error: 'no_openai_key', message: 'Set OPENAI_API_KEY in env.' })
        try {
          const upstream = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
            body: JSON.stringify({ model, messages: messages || [], temperature, stream: true }),
          })
          if (!upstream.ok || !upstream.body) {
            const errText = await upstream.text()
            return res.status(upstream.status).json({ error: 'openai_error', message: errText || `OpenAI 回傳狀態碼 ${upstream.status}` })
          }
          res.statusCode = 200
          res.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
          res.setHeader('Cache-Control', 'no-cache, no-transform')
          res.setHeader('Connection', 'keep-alive')
          const reader = upstream.body.getReader()
          const decoder = new TextDecoder()
          try {
            while (true) {
              const { done, value } = await reader.read()
              if (done) break
              res.write(decoder.decode(value, { stream: true }))
            }
          } finally { res.end() }
          return
        } catch (err) {
          return res.status(500).json({ error: 'openai_fetch_failed', message: `OpenAI 連線失敗: ${err.message}` })
        }
      }

      if (provider === 'ollama') {
        const base = process.env.OLLAMA_BASE_URL || 'http://localhost:11434'
        const promptText = messages ? messages.map(m => `${m.role}: ${m.content}`).join('\n') : (body.prompt || '')
        try {
          const upstream = await fetch(`${base.replace(/\/$/, '')}/api/generate`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model, prompt: promptText, temperature, stream: true }),
          })
          if (!upstream.ok || !upstream.body) {
            const errText = await upstream.text()
            if (upstream.status === 401) {
              return res.status(401).json({
                error: 'ollama_401',
                message: `該模型 (${model}) 需登入 Ollama.com 帳號憑證授權 (401 Unauthorized)，無法直接在本地調用。`
              })
            }
            return res.status(upstream.status).json({
              error: 'ollama_error',
              message: errText || `Ollama 回傳錯誤狀態碼: ${upstream.status}`
            })
          }
          res.statusCode = 200
          res.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
          res.setHeader('Cache-Control', 'no-cache, no-transform')
          res.setHeader('Connection', 'keep-alive')
          const reader = upstream.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''
          try {
            while (true) {
              const { done, value } = await reader.read()
              if (done) break
              buffer += decoder.decode(value, { stream: true })
              const lines = buffer.split('\n')
              buffer = lines.pop() || ''
              for (const line of lines) {
                if (!line.trim()) continue
                try {
                  const chunk = JSON.parse(line)
                  if (chunk.response) res.write(`data: ${JSON.stringify({ text: chunk.response })}\n\n`)
                } catch (e) {}
              }
            }
          } finally { res.write('data: [DONE]\n\n'); res.end() }
          return
        } catch (fetchErr) {
          const isTimeout = fetchErr.name === 'HeadersTimeoutError' || fetchErr.code === 'UND_ERR_HEADERS_TIMEOUT' || fetchErr.message?.includes('timeout')
          const msg = isTimeout
            ? `模型「${model}」載入逾時（超過 5 分鐘）！本機規格為 8GB 記憶體，7B/8B 大型模型由 CPU 載入耗時過長導致逾時。建議切換為輕量模型（如 qwen2.5:1.5b）或使用雲端 API (OpenAI / Gemini)。`
            : `無法連線至 Ollama 服務 (${fetchErr.message})，請確認 Ollama 容器是否正在運行。`
          return res.status(500).json({ error: 'ollama_fetch_failed', message: msg })
        }
      }
      // Google has no compatible stream in this adapter; fall through to normal response.
    }

    if (provider === 'openai') {
      const apiKey = process.env.OPENAI_API_KEY
      if (!apiKey) return res.status(400).json({ error: 'no_openai_key', message: 'Set OPENAI_API_KEY in env.' })
      try {
        const r = await fetch('https://api.openai.com/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
          body: JSON.stringify({ model, messages: messages || [{ role: 'user', content: body.prompt || '' }], temperature }),
        })
        const json = await r.json()
        // try to extract assistant text
        const content = json?.choices?.[0]?.message?.content ?? json?.choices?.[0]?.text ?? JSON.stringify(json)
        return res.json({ provider: 'openai', model, raw: json, text: content })
      } catch (err) {
        return res.status(500).json({ error: 'openai_error', detail: err.message })
      }
    }

    if (provider === 'ollama') {
      const base = process.env.OLLAMA_BASE_URL || 'http://localhost:11434'
      try {
        const promptText = messages ? messages.map(m => `${m.role}: ${m.content}`).join('\n') : (body.prompt || '')
        const r = await fetch(`${base.replace(/\/$/, '')}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model, prompt: promptText, temperature, stream: false }),
        })
        const js = await r.json()
        // Ollama /api/generate non-stream returns { response: "..." }
        const text = js?.response ?? js?.text ?? js?.result ?? js?.output ?? JSON.stringify(js)
        return res.json({ provider: 'ollama', model, raw: js, text })
      } catch (err) {
        return res.status(500).json({ error: 'ollama_error', detail: err.message })
      }
    }

    if (provider === 'google') {
      const apiKey = process.env.GOOGLE_API_KEY
      const endpoint = process.env.GOOGLE_API_ENDPOINT || 'https://generativelanguage.googleapis.com'
      if (!apiKey) return res.status(400).json({ error: 'no_google_key', message: 'Set GOOGLE_API_KEY in env.' })
      try {
        // Gemini API: POST /v1beta/models/{model}:generateContent
        const geminiMessages = (messages || [])
          .filter(m => m.role !== 'system')
          .map(m => ({
            role: m.role === 'assistant' ? 'model' : 'user',
            parts: [{ text: m.content }],
          }))
        // prepend system prompt as first user turn if present
        const systemMsg = (messages || []).find(m => m.role === 'system')
        const contents = systemMsg
          ? [{ role: 'user', parts: [{ text: systemMsg.content }] }, { role: 'model', parts: [{ text: '好的，我了解。' }] }, ...geminiMessages]
          : geminiMessages
        const apiUrl = `${endpoint.replace(/\/$/, '')}/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`
        const r = await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ contents, generationConfig: { temperature } }),
        })
        const js = await r.json()
        // Gemini response: { candidates: [{ content: { parts: [{ text: "..." }] } }] }
        const text = js?.candidates?.[0]?.content?.parts?.[0]?.text
          ?? js?.candidates?.[0]?.content
          ?? JSON.stringify(js)
        return res.json({ provider: 'google', model, raw: js, text })
      } catch (err) {
        return res.status(500).json({ error: 'google_error', detail: err.message })
      }
    }
  }

  // default: proxy to existing backend if configured
  const BACKEND = process.env.BACKEND_URL
  if (!BACKEND) return res.status(400).json({ error: 'no_backend', message: 'No BACKEND_URL configured for proxying other LLM operations.' })

  const target = `${BACKEND}${req.url.replace(/^\/api/, '')}`
  try {
    const response = await fetch(target, { method: req.method, headers: { ...req.headers, host: new URL(BACKEND).host }, body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined })
    const text = await response.text()
    res.status(response.status).send(text)
  } catch (err) {
    res.status(500).json({ error: 'proxy_failed', detail: err.message })
  }
}
