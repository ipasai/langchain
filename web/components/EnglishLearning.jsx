import { useEffect, useMemo, useState } from 'react'

const tabs = [
  ['manage', '📚 單字管理'],
  ['flashcard', '🃏 單字卡'],
  ['dictionary', '📖 字典查詢'],
  ['quiz', '🧪 測驗'],
  ['pronunciation', '🎤 發音'],
  ['stats', '📊 學習統計'],
]

export default function EnglishLearning() {
  const [activeTab, setActiveTab] = useState('manage')
  const [words, setWords] = useState([])
  const [word, setWord] = useState('')
  const [translation, setTranslation] = useState('')
  const [example, setExample] = useState('')
  const [category, setCategory] = useState('未分類')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [flashIndex, setFlashIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [quiz, setQuiz] = useState([])
  const [quizAnswers, setQuizAnswers] = useState({})
  const [quizResult, setQuizResult] = useState(null)
  const [stats, setStats] = useState(null)

  async function loadWords() {
    const response = await fetch('/api/db?action=list_words&limit=100')
    const data = await response.json()
    setWords(Array.isArray(data) ? data : [])
  }

  async function loadStats() {
    const response = await fetch('/api/db?action=stats')
    setStats(await response.json())
  }

  useEffect(() => { loadWords(); loadStats() }, [])

  async function addWord(event) {
    event.preventDefault()
    if (!word.trim() || !translation.trim()) return setStatus('英文與中文意思不可空白')
    const response = await fetch('/api/db', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'add_word', word, definition: translation, example, category }) })
    const data = await response.json()
    setStatus(data.ok ? '已儲存單字' : data.message || '儲存失敗')
    if (data.ok) { setWord(''); setTranslation(''); setExample(''); await loadWords() }
  }

  async function deleteWord(english) {
    if (!window.confirm(`刪除「${english}」？`)) return
    await fetch('/api/db', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'delete_word', english }) })
    await loadWords()
  }

  const categories = useMemo(() => ['未分類', ...new Set(words.map((item) => item.category).filter(Boolean))], [words])
  const filteredWords = useMemo(() => words.filter((item) => !search || `${item.english} ${item.translation}`.toLowerCase().includes(search.toLowerCase())), [words, search])
  const currentCard = filteredWords[flashIndex % Math.max(filteredWords.length, 1)]

  function speak(text) {
    if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance(text)) }
  }

  function createQuiz() {
    const pool = [...words].sort(() => Math.random() - 0.5).slice(0, Math.min(5, words.length))
    setQuiz(pool.map((item) => ({ ...item, options: [item.translation, ...words.filter((other) => other.english !== item.english).sort(() => Math.random() - 0.5).slice(0, 3).map((other) => other.translation)].sort(() => Math.random() - 0.5) })))
    setQuizAnswers({}); setQuizResult(null)
  }

  async function submitQuiz() {
    const score = quiz.reduce((total, item, index) => total + (quizAnswers[index] === item.translation ? 1 : 0), 0)
    setQuizResult({ score, total: quiz.length })
    await fetch('/api/db', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'save_study_session', test_type: 'english', score, total: quiz.length }) })
    await loadStats()
  }

  return (
    <div className="space-y-5">
      <header><h2 className="text-xl font-bold text-indigo-700">📘 英文學習</h2><p className="text-sm text-slate-500">單字管理、卡片複習、字典、測驗、發音與學習統計。</p></header>
      <div className="flex gap-1 overflow-x-auto border-b border-indigo-100">{tabs.map(([id, label]) => <button key={id} type="button" onClick={() => setActiveTab(id)} className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold ${activeTab === id ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500'}`}>{label}</button>)}</div>

      {activeTab === 'manage' && <section className="space-y-4"><form onSubmit={addWord} className="grid gap-2 md:grid-cols-2"><input className="rounded-lg border p-2" value={word} onChange={(event) => setWord(event.target.value)} placeholder="英文單字或片語" /><input className="rounded-lg border p-2" value={translation} onChange={(event) => setTranslation(event.target.value)} placeholder="中文意思" /><input className="rounded-lg border p-2" value={example} onChange={(event) => setExample(event.target.value)} placeholder="例句（選填）" /><input className="rounded-lg border p-2" value={category} onChange={(event) => setCategory(event.target.value)} placeholder="分類" /><button className="rounded-lg bg-indigo-600 px-4 py-2 text-white md:col-span-2">💾 儲存單字</button></form>{status && <p className="text-sm text-slate-600">{status}</p>}<WordList words={words} onDelete={deleteWord} onSpeak={speak} /></section>}

      {activeTab === 'flashcard' && <section className="space-y-4"><select className="rounded-lg border p-2" value={category} onChange={(event) => { setCategory(event.target.value); setFlashIndex(0) }}>{categories.map((item) => <option key={item}>{item}</option>)}</select>{currentCard ? <div className="rounded-2xl border bg-indigo-50 p-8 text-center"><div className="text-3xl font-bold text-indigo-900">{currentCard.english}</div><button className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-white" onClick={() => setRevealed(!revealed)}>{revealed ? currentCard.translation : '顯示中文意思'}</button>{revealed && currentCard.example && <p className="mt-4 text-slate-600">{currentCard.example}</p>}<div className="mt-6 flex justify-center gap-2"><button className="rounded-lg border bg-white px-4 py-2" onClick={() => { setFlashIndex((value) => (value + 1) % filteredWords.length); setRevealed(false) }}>下一張</button><button className="rounded-lg border bg-white px-4 py-2" onClick={() => speak(currentCard.english)}>🔊 發音</button></div></div> : <p>目前沒有單字。</p>}</section>}

      {activeTab === 'dictionary' && <section className="space-y-3"><input className="w-full rounded-lg border p-2" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜尋英文或中文意思" /><WordList words={filteredWords} onDelete={deleteWord} onSpeak={speak} /></section>}

      {activeTab === 'quiz' && <section className="space-y-4"><button className="rounded-lg bg-indigo-600 px-4 py-2 text-white" onClick={createQuiz} disabled={!words.length}>開始測驗</button>{quiz.map((item, index) => <fieldset key={item.english} className="rounded-lg border p-4"><legend className="font-semibold">{index + 1}. {item.english}</legend>{item.options.map((option) => <label key={option} className="block p-1"><input type="radio" name={`quiz-${index}`} checked={quizAnswers[index] === option} onChange={() => setQuizAnswers({ ...quizAnswers, [index]: option })} /> <span className="ml-2">{option}</span></label>)}</fieldset>)}{quiz.length > 0 && <button className="rounded-lg bg-emerald-600 px-4 py-2 text-white" onClick={submitQuiz}>提交答案</button>}{quizResult && <p className="font-semibold">得分：{quizResult.score} / {quizResult.total}</p>}</section>}

      {activeTab === 'pronunciation' && <section className="space-y-3"><input className="w-full rounded-lg border p-2" value={word} onChange={(event) => setWord(event.target.value)} placeholder="輸入要朗讀的英文" /><button className="rounded-lg bg-indigo-600 px-4 py-2 text-white" onClick={() => speak(word)}>🔊 示範發音</button><p className="text-sm text-slate-500">瀏覽器的語音辨識需要 Chrome/Edge 與麥克風權限。</p></section>}
      {activeTab === 'stats' && <section className="grid gap-3 sm:grid-cols-4">{[['單字數', stats?.total_items], ['測驗次數', stats?.total_sessions], ['總得分', stats?.total_score], ['準確率', stats ? `${Math.round((stats.accuracy || 0) * 100)}%` : '-']].map(([label, value]) => <div key={label} className="rounded-lg border bg-emerald-50 p-4"><div className="text-sm text-slate-500">{label}</div><div className="mt-1 text-2xl font-bold text-emerald-800">{value ?? '-'}</div></div>)}</section>}
    </div>
  )
}

function WordList({ words, onDelete, onSpeak }) {
  return <div className="grid gap-2">{words.length === 0 && <div className="text-sm text-slate-500">目前沒有單字。</div>}{words.map((item) => <div key={`${item.english}-${item.created_at}`} className="flex items-start justify-between rounded-lg border bg-white p-3"><div><strong>{item.english}</strong><div className="text-sm text-slate-600">{item.translation}</div>{item.example && <div className="text-sm text-slate-500">{item.example}</div>}</div><div className="flex gap-2"><button className="text-sm text-indigo-600" onClick={() => onSpeak(item.english)}>🔊</button><button className="text-sm text-red-600" onClick={() => onDelete(item.english)}>刪除</button></div></div>)}</div>
}
