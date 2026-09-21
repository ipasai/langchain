import { useEffect, useState } from 'react'
import MermaidRenderer from './MermaidRenderer'
import { useLLMGuard } from '../lib/useLLMGuard'
import LLMOverlay from './LLMOverlay'

export default function DocAnalyzer() {
  const [status, setStatus] = useState('idle')
  const [summary, setSummary] = useState('')
  const [uploadedId, setUploadedId] = useState(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [mermaidCode, setMermaidCode] = useState('')
  const [activeTab, setActiveTab] = useState('upload')
  const [quizQuestions, setQuizQuestions] = useState([])
  const [quizAnswers, setQuizAnswers] = useState({})
  const [quizScore, setQuizScore] = useState(null)
  const [savedSets, setSavedSets] = useState([])
  const [documents, setDocuments] = useState([])
  const { loading, elapsedSec, run } = useLLMGuard()

  useEffect(() => {
    try { setSavedSets(JSON.parse(window.localStorage.getItem('doc_quiz_sets') || '[]')) } catch (error) { setSavedSets([]) }
    fetch('/api/doc?action=list').then((response) => response.json()).then((data) => setDocuments(data.items || [])).catch(() => setDocuments([]))
  }, [])

  const tabs = [
    ['upload', '📤 上傳分析'],
    ['knowledge', '🧠 知識模式'],
    ['quiz', '📝 考題測驗'],
    ['rag', '🔍 RAG 問答'],
    ['bank', '🗂️ 題庫管理'],
    ['history', '📊 歷史紀錄'],
  ]

  async function handleFileChange(e) {
    const f = e.target.files && e.target.files[0]
    if (!f) return
    setStatus('reading')
    await run(async () => {
      const buf = await f.arrayBuffer()
      const uint8 = new Uint8Array(buf)
      let binary = ''
      const chunkSize = 0x8000
      for (let i = 0; i < uint8.length; i += chunkSize) {
        binary += String.fromCharCode.apply(null, Array.from(uint8.subarray(i, i + chunkSize)))
      }
      const b64 = btoa(binary)
      setStatus('uploading')
      const res = await fetch('/api/doc?action=upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: f.name, content_base64: b64 }),
      })
      const j = await res.json()
      if (j.ok) { setUploadedId(j.id); setSummary(j.summary); setStatus('uploaded') }
      else setStatus('error')
    }, { feature: 'doc_upload', action: `上傳文件：${f.name}`, note: f.name })
  }

  async function handleIndex() {
    if (!uploadedId) return
    setStatus('indexing')
    await run(async () => {
      const res = await fetch('/api/doc?action=index', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: uploadedId }),
      })
      const j = await res.json()
      if (j.ok) setStatus('indexed')
      else setStatus('error')
    }, { feature: 'doc_index', action: '建立索引', note: uploadedId })
  }

  async function handleQuery() {
    if (!query) return
    setStatus('querying')
    await run(async () => {
      const res = await fetch('/api/doc?action=search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: query }),
      })
      const j = await res.json()
      if (j.ok) { setResults(j.results || []); setStatus('queried'); setMermaidCode('') }
      else {
        const r2 = await fetch(`/api/doc?action=query&q=${encodeURIComponent(query)}`)
        const j2 = await r2.json()
        if (j2.ok) { setResults(j2.results || []); setStatus('queried') } else setStatus('error')
      }
    }, { feature: 'doc_query', action: `RAG 查詢：${query}`, note: query })
  }

  async function generateQuiz() {
    if (!uploadedId) return
    setStatus('quiz_generating')
    await run(async () => {
      const response = await fetch('/api/doc?action=quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: uploadedId, count: 5 }),
      })
      const data = await response.json()
      if (data.ok) { setQuizQuestions(data.questions || []); setQuizAnswers({}); setQuizScore(null); setStatus('quiz_ready') }
      else setStatus(data.error || 'quiz_error')
    }, { feature: 'doc_quiz', action: '產生考題', note: uploadedId })
  }

  async function submitQuiz() {
    const score = quizQuestions.reduce((total, question, index) => total + (quizAnswers[index] === question.answer ? 1 : 0), 0)
    setQuizScore({ score, total: quizQuestions.length })
  }

  function saveQuizSet() {
    if (!quizQuestions.length) return
    const next = [{ name: `${new Date().toLocaleString()} 題組`, questions: quizQuestions }, ...savedSets].slice(0, 20)
    setSavedSets(next)
    window.localStorage.setItem('doc_quiz_sets', JSON.stringify(next))
    setStatus('quiz_saved')
  }

  return (
    <div>
      <LLMOverlay show={loading} elapsed={elapsedSec} label="文件處理中…" />
      <h2 className="mb-1 text-xl font-bold text-indigo-700">📄 智慧文件分析</h2>
      <p className="mb-4 text-gray-600">上傳任意文件，進行摘要、心智圖、知識庫、問答與測驗。</p>

      <div className="mb-5 flex gap-1 overflow-x-auto border-b border-indigo-100" role="tablist" aria-label="文件分析功能">
        {tabs.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={activeTab === id} onClick={() => setActiveTab(id)} className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold ${activeTab === id ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500'}`}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'upload' && <div className="mb-3">
        <input type="file" onChange={handleFileChange} />
        <div className="mt-2 text-sm text-gray-500">狀態：{status}</div>
      </div>}

      {activeTab === 'knowledge' && summary && (
        <div className="mb-3 p-3 bg-gray-50 border rounded">
          <div className="font-medium mb-1">🧠 文件摘要與知識內容</div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap">{summary}</div>
          <div className="mt-3 rounded border bg-white p-3 text-sm text-slate-600">文件：{documents.find((item) => item.id === uploadedId)?.filename || '目前文件'}<br />可從 RAG 問答頁搜尋已建立索引的內容。</div>
          <button type="button" className="mt-3 rounded bg-indigo-600 px-3 py-1 text-sm text-white" onClick={() => window.speechSynthesis?.speak(new SpeechSynthesisUtterance(summary))}>🔊 朗讀摘要</button>
        </div>
      )}

      {activeTab === 'knowledge' && !summary && <div className="text-sm text-gray-500">請先到「上傳分析」選擇文件。</div>}

      {activeTab === 'upload' && <div className="flex flex-wrap gap-2 mb-4">
        <button onClick={handleIndex} className="px-3 py-1 bg-indigo-600 text-white rounded" disabled={!uploadedId}>建立索引</button>
        <button onClick={async ()=>{
          // list docs
          setStatus('loading_list')
          const res = await fetch('/api/doc?action=list')
          const j = await res.json()
          if (j.ok) setResults((j.items||[]).map(it=>({ id: it.id, filename: it.filename, snippet: (it.extracted||'').slice(0,200), indexed: it.indexed })))
          setStatus('loaded')
        }} className="px-3 py-1 bg-gray-200 rounded">列出已上傳文件</button>
        <button onClick={async ()=>{
          if (!uploadedId) return
          setStatus('mindmap')
          const res = await fetch('/api/doc?action=mindmap', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: uploadedId })
          })
          const j = await res.json()
          if (j.ok) {
            setResults([{ id: 'mindmap', filename: '心智圖', snippet: j.mermaid }])
            setMermaidCode(j.mermaid || '')
            setStatus('mindmap_ready')
          } else setStatus('error')
        }} className="px-3 py-1 bg-amber-500 text-white rounded">產生心智圖</button>
        <button onClick={() => { setUploadedId(null); setSummary(''); setStatus('idle') }} className="px-3 py-1 bg-gray-200 rounded">重置</button>
      </div>}

      {activeTab === 'rag' && <div className="mb-3">
        <div className="flex gap-2">
          <input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="輸入查詢關鍵字" className="flex-1 border px-2 py-1 rounded" />
          <button onClick={handleQuery} className="px-3 py-1 bg-green-600 text-white rounded">查詢</button>
        </div>
        <div className="mt-2 text-sm text-gray-500">狀態：{status}</div>
      </div>}

      {activeTab === 'quiz' && <section className="space-y-4"><button className="rounded bg-indigo-600 px-3 py-2 text-white disabled:opacity-50" disabled={!uploadedId} onClick={generateQuiz}>📝 產生考題</button>{quizQuestions.map((question, index) => <fieldset key={index} className="rounded border p-3"><legend className="font-semibold">{index + 1}. {question.question}</legend>{(question.options || []).map((option) => <label key={option} className="block py-1"><input type="radio" name={`doc-quiz-${index}`} checked={quizAnswers[index] === option} onChange={() => setQuizAnswers({ ...quizAnswers, [index]: option })} /> <span className="ml-2">{option}</span></label>)}</fieldset>)}{quizQuestions.length > 0 && <div className="flex gap-2"><button className="rounded bg-emerald-600 px-3 py-2 text-white" onClick={submitQuiz}>提交答案</button><button className="rounded border px-3 py-2" onClick={saveQuizSet}>儲存題組</button></div>}{quizScore && <p className="font-semibold">得分：{quizScore.score} / {quizScore.total}</p>}</section>}
      {activeTab === 'bank' && <section className="space-y-3"><h3 className="font-semibold text-indigo-900">🗂️ 已儲存題組</h3>{savedSets.length === 0 ? <p className="text-sm text-slate-500">尚未儲存題組，請先在考題測驗頁產生題目。</p> : savedSets.map((set) => <div key={set.name} className="rounded border p-3"><strong>{set.name}</strong><span className="ml-2 text-sm text-slate-500">{set.questions.length} 題</span></div>)}</section>}
      {activeTab === 'history' && <section className="space-y-3"><h3 className="font-semibold text-slate-800">📊 文件歷史紀錄</h3>{documents.length === 0 ? <p className="text-sm text-slate-500">尚無上傳文件。</p> : documents.slice().reverse().map((document) => <div key={document.id} className="flex justify-between rounded border p-3 text-sm"><span>{document.filename}</span><span className={document.indexed ? 'text-emerald-600' : 'text-slate-500'}>{document.indexed ? '已索引' : '未索引'}</span></div>)}</section>}

      {(activeTab === 'rag' || activeTab === 'knowledge' || activeTab === 'upload') && <div>
        {results.length === 0 && <div className="text-sm text-gray-500">無查詢結果。</div>}
        <MermaidRenderer code={mermaidCode} />
        {results.map((r) => (
          <div key={r.id} className="mb-3 p-3 bg-white border rounded">
            <div className="flex justify-between">
              <div className="font-medium">{r.filename}</div>
              <div className="text-xs text-gray-500">{r.score ? `score: ${r.score.toFixed(3)}` : (r.indexed ? 'indexed' : '')}</div>
            </div>
            <div className="text-sm text-gray-700 whitespace-pre-wrap mt-2">{r.snippet}</div>
          </div>
        ))}
      </div>}
    </div>
  )
}


