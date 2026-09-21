import { useEffect, useState } from 'react'
import { getActivities, clearActivities, generateCommitSummary } from '../lib/activityLog'

const FEATURE_LABEL = {
  chat:         '💬 AI 對話',
  db_analysis:  '🗄️ 資料庫分析',
  doc_upload:   '📤 文件上傳',
  doc_index:    '🔍 文件索引',
  doc_query:    '🔎 RAG 查詢',
  doc_quiz:     '📝 考題產生',
  unknown:      '❓ 未知',
}

function formatMs(ms) {
  if (!ms && ms !== 0) return '-'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} 秒`
}

function formatTime(iso) {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('zh-TW', { hour12: false })
  } catch { return iso }
}

export default function ActivityPage() {
  const [activities, setActivities] = useState([])
  const [commitText, setCommitText] = useState('')
  const [copied, setCopied] = useState(false)
  const [filterFeature, setFilterFeature] = useState('all')

  useEffect(() => {
    setActivities(getActivities())
  }, [])

  function refresh() {
    setActivities(getActivities())
    setCommitText('')
  }

  function handleClear() {
    if (!window.confirm('確定清除所有活動紀錄？')) return
    clearActivities()
    setActivities([])
    setCommitText('')
  }

  function handleGenerateCommit() {
    const text = generateCommitSummary(30)
    setCommitText(text)
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(commitText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const features = ['all', ...new Set(activities.map(a => a.feature))]
  const filtered = filterFeature === 'all'
    ? activities
    : activities.filter(a => a.feature === filterFeature)

  // 統計
  const totalCount = activities.length
  const avgMs = totalCount
    ? Math.round(activities.reduce((s, a) => s + (a.thinkMs || 0), 0) / totalCount)
    : 0
  const featureCounts = activities.reduce((acc, a) => {
    acc[a.feature] = (acc[a.feature] || 0) + 1
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto max-w-5xl space-y-6">

        {/* 標題 */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">📋 活動歷程</h1>
            <p className="mt-1 text-sm text-slate-500">記錄每次 AI 模型呼叫的功能、模型、耗時，方便填寫 git commit。</p>
          </div>
          <a href="/" className="rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50">
            ← 返回主頁
          </a>
        </div>

        {/* 統計卡 */}
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">總操作次數</div>
            <div className="mt-1 text-2xl font-bold text-indigo-700">{totalCount}</div>
          </div>
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">平均耗時</div>
            <div className="mt-1 text-2xl font-bold text-emerald-600">{formatMs(avgMs)}</div>
          </div>
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">功能分佈</div>
            <div className="mt-1 space-y-0.5">
              {Object.entries(featureCounts).map(([f, c]) => (
                <div key={f} className="flex justify-between text-xs">
                  <span className="text-slate-600">{FEATURE_LABEL[f] || f}</span>
                  <span className="font-semibold text-slate-800">{c}</span>
                </div>
              ))}
              {totalCount === 0 && <span className="text-sm text-slate-400">尚無記錄</span>}
            </div>
          </div>
        </div>

        {/* Git Commit 產生器 */}
        <div className="rounded-xl border bg-white p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-800">🔖 Git Commit 摘要產生器</h2>
            <button
              onClick={handleGenerateCommit}
              className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              產生摘要
            </button>
          </div>
          {commitText && (
            <div className="relative">
              <pre className="rounded-lg bg-slate-800 p-4 text-sm text-slate-100 whitespace-pre-wrap font-mono">
                {commitText}
              </pre>
              <button
                onClick={handleCopy}
                className="absolute right-2 top-2 rounded bg-white/10 px-2 py-1 text-xs text-white hover:bg-white/20"
              >
                {copied ? '✓ 已複製' : '複製'}
              </button>
            </div>
          )}
        </div>

        {/* 篩選 + 工具列 */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1">
            {features.map(f => (
              <button
                key={f}
                onClick={() => setFilterFeature(f)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition
                  ${filterFeature === f
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white border text-slate-600 hover:bg-indigo-50'}`}
              >
                {f === 'all' ? '全部' : (FEATURE_LABEL[f] || f)}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={refresh} className="rounded-lg border px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100">
              🔄 重新整理
            </button>
            <button onClick={handleClear} className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">
              🗑️ 清除記錄
            </button>
          </div>
        </div>

        {/* 活動列表 */}
        {filtered.length === 0 ? (
          <div className="rounded-xl border bg-white p-8 text-center text-slate-400">
            尚無活動記錄。執行任意 AI 功能後即會在此顯示。
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map(a => (
              <div key={a.id} className="rounded-xl border bg-white p-3 shadow-sm flex flex-wrap items-start gap-3">
                {/* 功能標籤 */}
                <span className="shrink-0 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                  {FEATURE_LABEL[a.feature] || a.feature}
                </span>

                {/* 動作描述 */}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-800 truncate">{a.action}</div>
                  {a.note && <div className="text-xs text-slate-400 truncate">{a.note}</div>}
                </div>

                {/* 模型 */}
                <div className="shrink-0 flex items-center gap-1.5">
                  {a.provider && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
                      {a.provider}
                    </span>
                  )}
                  {a.model && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-500">
                      {a.model}
                    </span>
                  )}
                </div>

                {/* 耗時 */}
                <span className="shrink-0 text-xs text-emerald-600 font-medium tabular-nums">
                  ⏱ {formatMs(a.thinkMs)}
                </span>

                {/* 時間戳 */}
                <span className="shrink-0 text-xs text-slate-400 tabular-nums">
                  {formatTime(a.timestamp)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
