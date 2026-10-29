import { useState, useEffect, useRef } from 'react'
import { useLLMGuard } from '../lib/useLLMGuard'
import LLMOverlay from './LLMOverlay'

export default function Chat({ settings = {} }) {
  // ── Session 狀態 ────────────────────────────────────────────
  const [sessions, setSessions] = useState([])          // 所有分組
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [sessionPanelOpen, setSessionPanelOpen] = useState(false)
  const [renamingId, setRenamingId] = useState(null)
  const [renameValue, setRenameValue] = useState('')

  // ── 對話狀態 ────────────────────────────────────────────────
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState([])
  const { loading, elapsedSec, run } = useLLMGuard()
  const inputRef = useRef(null)

  // ── 初始化：載入 sessions，若無則自動建一個 ─────────────────
  useEffect(() => {
    loadSessions()
  }, [])

  async function loadSessions() {
    try {
      const res = await fetch('/api/db?action=list_sessions')
      const data = await res.json()
      const list = Array.isArray(data) ? data : []
      setSessions(list)
      if (list.length === 0) {
        // 第一次使用：自動建立預設分組
        await createSession('預設對話')
      } else {
        // 還原上次選的 session
        const lastId = Number(localStorage.getItem('last_session_id'))
        const target = list.find(s => s.id === lastId) || list[0]
        switchSession(target.id)
      }
    } catch (e) {
      console.error('loadSessions error', e)
    }
  }

  async function createSession(name = '新對話') {
    try {
      const res = await fetch('/api/db', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create_session', name }),
      })
      const data = await res.json()
      await loadSessions()
      switchSession(data.id)
      return data.id
    } catch (e) {
      console.error('createSession error', e)
    }
  }

  async function switchSession(sessionId) {
    setCurrentSessionId(sessionId)
    localStorage.setItem('last_session_id', sessionId)
    setSessionPanelOpen(false)
    await loadMessages(sessionId)
  }

  async function loadMessages(sessionId) {
    if (!sessionId) return
    try {
      const res = await fetch(`/api/db?action=list_chats_by_session&session_id=${sessionId}&limit=200`)
      const rows = await res.json()
      const mapped = Array.isArray(rows)
        ? rows.map(r => ({
            id: r.id,
            role: r.role,
            text: r.content,
            meta: r.meta ? (() => { try { return JSON.parse(r.meta) } catch { return null } })() : null,
          })).reverse()
        : []
      setMessages(mapped)
    } catch (e) {
      setMessages([])
    }
  }

  async function deleteSession(sessionId) {
    if (!window.confirm('確定刪除此對話分組？所有訊息將一併刪除。')) return
    try {
      await fetch('/api/db', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'delete_session', id: sessionId }),
      })
      const remaining = sessions.filter(s => s.id !== sessionId)
      if (remaining.length === 0) {
        await createSession('預設對話')
      } else {
        const next = currentSessionId === sessionId ? remaining[0].id : currentSessionId
        await loadSessions()
        switchSession(next)
      }
    } catch (e) {
      console.error('deleteSession error', e)
    }
  }

  async function renameSession(id, name) {
    try {
      await fetch('/api/db', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'rename_session', id, name }),
      })
      setRenamingId(null)
      await loadSessions()
    } catch (e) {
      console.error('renameSession error', e)
    }
  }

  // ── 清除歷史（當前 session）的外部事件 ─────────────────────
  useEffect(() => {
    async function reload() {
      await loadSessions()
    }
    window.addEventListener('chat-history-cleared', reload)
    return () => window.removeEventListener('chat-history-cleared', reload)
  }, [])

  // ── 儲存單則訊息 ────────────────────────────────────────────
  async function saveChat(role, content, meta = null) {
    if (!currentSessionId) return
    try {
      await fetch('/api/db', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'save_chat', role, content, session_id: currentSessionId, meta }),
      })
    } catch (e) {}
  }

  // ── 刪除單則訊息（僅前端，不刪 DB） ───────────────────────
  function deleteMessage(id) {
    setMessages(m => m.filter(msg => msg.id !== id))
  }

  // ── 送出訊息 ────────────────────────────────────────────────
  async function send() {
    if (!prompt.trim() || !currentSessionId) return
    const userText = prompt.trim()
    const userFrontendId = crypto.randomUUID()

    setMessages(m => [{ id: userFrontendId, role: 'user', text: userText }, ...m])
    setPrompt('')

    saveChat('user', userText)

    const rawModel = (settings.model || '').split(' (')[0]
    const providerName = settings.provider || 'openai'

    await run(async () => {
      const historyForLLM = [...messages]
        .reverse()
        .slice(-20)
        .map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text }))
      historyForLLM.push({ role: 'user', content: userText })

      const requestBody = {
        action: 'chat',
        provider: providerName,
        model: rawModel,
        temperature: settings.temperature,
        system_prompt: settings.systemPrompt,
        messages: historyForLLM,
        stream: providerName === 'openai' || providerName === 'ollama',
      }

      const res = await fetch('/api/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })

      if (!res.ok) {
        let errMsg = ''
        try {
          const errJson = await res.json()
          errMsg = errJson.message || errJson.error || JSON.stringify(errJson)
        } catch {
          errMsg = await res.text()
        }
        throw new Error(errMsg || `HTTP ${res.status}`)
      }

      const assistantId = crypto.randomUUID()
      let assistantText = ''
      const startTime = Date.now()
      setMessages(m => [{ id: assistantId, role: 'assistant', text: '' }, ...m])

      if (requestBody.stream && res.body) {
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split('\n\n')
          buffer = events.pop() || ''
          for (const event of events) {
            const line = event.split('\n').find(l => l.startsWith('data:'))
            if (!line) continue
            const payload = line.slice(5).trim()
            if (payload === '[DONE]') continue
            try {
              const chunk = JSON.parse(payload)
              assistantText += chunk.text || chunk.choices?.[0]?.delta?.content || ''
              setMessages(m => m.map(msg => msg.id === assistantId ? { ...msg, text: assistantText } : msg))
            } catch (e) {}
          }
        }
      } else {
        const json = await res.json()
        assistantText = json?.text || (typeof json === 'string' ? json : JSON.stringify(json))
        setMessages(m => m.map(msg => msg.id === assistantId ? { ...msg, text: assistantText } : msg))
      }

      const thinkMs = Date.now() - startTime
      const meta = { model: rawModel, provider: providerName, thinkMs }
      setMessages(m => m.map(msg => msg.id === assistantId ? { ...msg, meta } : msg))
      saveChat('assistant', assistantText, meta)
      loadSessions()
    }, {
      feature: 'chat',
      action: '送出訊息',
      model: rawModel,
      provider: providerName,
      note: currentSession?.name || '',
    }).catch(err => {
      setMessages(m => [{ id: crypto.randomUUID(), role: 'assistant', text: `Error: ${err.message || '無法取得模型回應'}` }, ...m])
    })

    inputRef.current?.focus()
  }

  const currentSession = sessions.find(s => s.id === currentSessionId)

  return (
    <div className="flex flex-col h-full relative">

      {/* ── 全畫面遮罩 ── */}
      <LLMOverlay
        show={loading}
        model={settings.model}
        provider={settings.provider}
        elapsed={elapsedSec}
        label="AI 正在思考中…"
      />

      {/* ── Session 面板（下拉） ── */}
      {sessionPanelOpen && (
        <div className="absolute top-0 left-0 right-0 z-40 bg-white border border-indigo-100 rounded-xl shadow-xl p-3 space-y-2 max-h-72 overflow-y-auto">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-bold text-indigo-700">📂 對話分組</span>
            <button
              className="rounded-lg bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-700"
              onClick={() => {
                const name = window.prompt('新分組名稱：', '新對話')
                if (name?.trim()) createSession(name.trim())
              }}
            >＋ 新增分組</button>
          </div>

          {sessions.map(s => (
            <div
              key={s.id}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 cursor-pointer transition
                ${s.id === currentSessionId ? 'bg-indigo-100 border border-indigo-300' : 'hover:bg-slate-50 border border-transparent'}`}
            >
              {renamingId === s.id ? (
                <form className="flex flex-1 gap-1" onSubmit={e => { e.preventDefault(); renameSession(s.id, renameValue) }}>
                  <input
                    autoFocus
                    className="flex-1 rounded border px-2 py-0.5 text-sm"
                    value={renameValue}
                    onChange={e => setRenameValue(e.target.value)}
                    onBlur={() => setRenamingId(null)}
                  />
                  <button type="submit" className="text-xs text-indigo-600 font-semibold">確認</button>
                </form>
              ) : (
                <>
                  <button className="flex-1 text-left" onClick={() => switchSession(s.id)}>
                    <div className="text-sm font-medium truncate">{s.name}</div>
                    <div className="text-xs text-slate-400">{s.message_count} 則訊息</div>
                  </button>
                  <button
                    className="text-slate-300 hover:text-indigo-500 text-xs px-1"
                    title="重新命名"
                    onClick={() => { setRenamingId(s.id); setRenameValue(s.name) }}
                  >✏️</button>
                  <button
                    className="text-slate-300 hover:text-red-500 text-xs px-1"
                    title="刪除分組"
                    onClick={() => deleteSession(s.id)}
                  >🗑️</button>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── 頂部：輸入區 + 分組切換 ── */}
      <div className="sticky top-0 z-10 bg-white pb-2 pt-1 border-b border-gray-200 shadow-sm space-y-2">
        {/* Session 切換列 */}
        <div className="flex items-center gap-2">
          <button
            className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-sm font-semibold text-indigo-700 hover:bg-indigo-100 transition max-w-[60%] truncate"
            onClick={() => setSessionPanelOpen(o => !o)}
          >
            <span className="truncate">📂 {currentSession?.name || '選擇分組'}</span>
            <svg className={`h-3 w-3 shrink-0 transition-transform ${sessionPanelOpen ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" />
            </svg>
          </button>
          <button
            className="rounded-lg border border-indigo-200 bg-white px-2 py-1.5 text-xs text-indigo-600 hover:bg-indigo-50"
            title="新增分組"
            onClick={() => {
              const name = window.prompt('新分組名稱：', '新對話')
              if (name?.trim()) createSession(name.trim())
            }}
          >＋</button>
          <span className="ml-auto text-xs text-slate-400">{messages.length} 則訊息</span>
        </div>

        {/* 輸入框 */}
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            rows={2}
            className="flex-1 border border-gray-300 p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y text-sm"
            placeholder={currentSession ? `在「${currentSession.name}」中輸入訊息…` : '請先選擇或建立對話分組'}
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !e.nativeEvent.isComposing) {
                e.preventDefault()
                send()
              }
            }}
            disabled={loading || !currentSessionId}
          />
          <button
            className="px-5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium self-stretch flex items-center justify-center shrink-0"
            onClick={send}
            disabled={loading || !currentSessionId}
          >
            {loading ? '…' : '送出'}
          </button>
        </div>
      </div>

      {/* ── 訊息列表 ── */}
      <div className="flex-1 overflow-auto mt-3 space-y-2" onClick={() => sessionPanelOpen && setSessionPanelOpen(false)}>
        {messages.length === 0 && (
          <p className="text-center text-gray-400 text-sm mt-8">
            {currentSession ? `「${currentSession.name}」尚無訊息，開始對話吧！` : '請選擇對話分組'}
          </p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`group flex items-start gap-2 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
            <div className="flex flex-col gap-0.5 max-w-[80%]">
              <div className={`inline-block p-2 rounded-lg text-sm whitespace-pre-wrap break-words ${
                m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'
              }`}>
                {m.text || (
                  <span className="flex gap-1 items-center h-4">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                  </span>
                )}
              </div>
              {/* Meta 標籤：只顯示在 assistant 訊息上 */}
              {m.role === 'assistant' && m.meta && (
                <div className="flex items-center gap-1.5 px-1">
                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-medium text-indigo-600">
                    {m.meta.provider}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500 font-mono">
                    {m.meta.model}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    ⏱ {m.meta.thinkMs < 1000
                      ? `${m.meta.thinkMs} ms`
                      : `${(m.meta.thinkMs / 1000).toFixed(1)} 秒`}
                  </span>
                </div>
              )}
            </div>
            <button
              className="opacity-0 group-hover:opacity-100 transition-opacity self-start mt-1 p-1 rounded hover:bg-red-100 text-gray-400 hover:text-red-500 focus:opacity-100"
              onClick={() => deleteMessage(m.id)}
              title="刪除"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
