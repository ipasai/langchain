import { useEffect, useMemo, useState } from 'react'
import { useLLMGuard } from '../lib/useLLMGuard'
import LLMOverlay from './LLMOverlay'

export default function DataAnalysis({ settings = {} }) {
  const [fileName, setFileName] = useState('')
  const [rows, setRows] = useState([])
  const [columns, setColumns] = useState([])
  const [numeric, setNumeric] = useState([])
  const [categorical, setCategorical] = useState([])
  const [xColumn, setXColumn] = useState('')
  const [yColumn, setYColumn] = useState('')
  const [chartType, setChartType] = useState('bar')
  const [aggregation, setAggregation] = useState('count')
  const [chart, setChart] = useState(null)
  const [history, setHistory] = useState([])
  const [message, setMessage] = useState('尚未載入資料')
  const [overlayLabel, setOverlayLabel] = useState('資料分析處理中…')
  const [aiInsight, setAiInsight] = useState('')
  const [aiInsightMeta, setAiInsightMeta] = useState(null)

  const { loading, elapsedSec, run } = useLLMGuard()

  // 取得目前有效的 provider 與 model
  function getActiveConfig() {
    let provider = settings.provider
    let model = settings.model
    if (!provider) {
      try {
        const saved = JSON.parse(localStorage.getItem('tab_settings_data') || '{}')
        if (saved.provider) provider = saved.provider
        if (saved.model) model = saved.model
      } catch (_) {}
    }
    return {
      provider: provider || 'openai',
      model: (model || 'gpt-4o-mini').split(' (')[0],
    }
  }

  const { provider: activeProvider, model: activeModel } = getActiveConfig()

  async function loadHistory() {
    try {
      const response = await fetch('/api/data?action=history')
      const data = await response.json()
      setHistory(data.entries || [])
    } catch (_) {}
  }

  useEffect(() => {
    loadHistory()
  }, [])

  // ── 讀取檔案 ────────────────────────────────────────────────
  async function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return

    setOverlayLabel(`正在讀取並解析檔案「${file.name}」…`)
    setMessage(`正在讀取「${file.name}」…`)
    setAiInsight('')
    setAiInsightMeta(null)

    const startTime = Date.now()
    await run(async () => {
      const buffer = await file.arrayBuffer()
      const bytes = new Uint8Array(buffer)
      let binary = ''
      for (let index = 0; index < bytes.length; index += 0x8000) {
        binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
      }

      const response = await fetch('/api/data?action=analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name, content_base64: btoa(binary) }),
      })
      const data = await response.json()
      if (!data.ok) throw new Error(data.detail || data.error || '檔案解析失敗')

      setFileName(file.name)
      setRows(data.rows || [])
      setColumns(data.columns || [])
      setNumeric(data.numeric || [])
      setCategorical(data.categorical || [])
      setXColumn(data.defaults?.xColumn || data.columns?.[0] || '')
      setYColumn(data.defaults?.yColumn || '')
      setChartType(data.suggestion || 'bar')

      const timeSec = ((Date.now() - startTime) / 1000).toFixed(1)
      setMessage(`✅ 已成功讀取 ${file.name}（共 ${data.rows?.length || 0} 列資料，解析耗時 ${timeSec} 秒）`)
    }, {
      feature: 'data_upload',
      action: `讀取檔案：${file.name}`,
      provider: activeProvider,
      model: activeModel,
      note: file.name,
    }).catch((err) => {
      setMessage(`❌ 檔案讀取失敗：${err.message}`)
    })
  }

  // ── 生成圖表與 AI 分析 ──────────────────────────────────────
  async function generateChart() {
    if (!fileName || rows.length === 0) {
      setMessage('❌ 請先上傳並讀取資料檔案')
      return
    }

    setOverlayLabel('AI 正在計算圖表數據與生成數據分析洞察…')
    setMessage('AI 正在計算圖表數據與分析中…')
    setAiInsight('')
    setAiInsightMeta(null)

    const startTime = Date.now()
    await run(async () => {
      // 1. 生成圖表數據
      const response = await fetch('/api/data?action=chart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: fileName,
          rows,
          chart_type: chartType,
          x_col: xColumn,
          y_col: yColumn || undefined,
          aggregation,
          title: `${xColumn} ${yColumn ? `vs ${yColumn}` : '分類比較'}`,
        }),
      })
      const data = await response.json()
      if (!data.ok) throw new Error(data.detail || data.error || '圖表產生失敗')

      setChart(data)
      const chartElapsed = ((Date.now() - startTime) / 1000).toFixed(1)
      setMessage(`✅ 圖表生成完成（耗時 ${chartElapsed} 秒）`)

      // 儲存至分析歷史
      await fetch('/api/data?action=save_history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entry: {
            file_name: fileName,
            x_col: xColumn,
            y_col: yColumn,
            chart_type: chartType,
            saved_path: '',
            data: data.data,
          },
        }),
      })
      await loadHistory()

      // 2. 呼叫 LLM 進行智慧數據洞察分析
      try {
        const topLabels = (data.data?.labels || []).slice(0, 10)
        const topValues = (data.data?.values || []).slice(0, 10)
        const summaryLines = topLabels.map((lbl, idx) => `  - ${lbl}: ${topValues[idx]}`).join('\n')

        const prompt = `你是一位專業的商業與統計數據分析師。使用者對資料集「${fileName}」進行了統計圖表分析：
- 分析維度 (X 軸)：${xColumn}
- 分析指標 (Y 軸)：${yColumn || '出現次數 (計數)'}
- 統計方法：${aggregation === 'mean' ? '平均值 (Mean)' : '數量統計 (Count)'}
- 圖表類型：${chartType}
- 總數據列數：${rows.length} 列
- 前 10 項統計結果：
${summaryLines || '  （無統計數據）'}

請以繁體中文撰寫一份簡潔明瞭的「📊 數據洞察與決策建議」：
1. 【趨勢觀察】：簡述資料的主要分佈情況或極值（最高、最低）。
2. 【核心發現】：指出資料背後可能代表的含意或模式。
3. 【決策建議】：依據此分析結果提出 1~2 點具體可行的改善或應用建議。`

        const llmRes = await fetch('/api/llm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'chat',
            provider: activeProvider,
            model: activeModel,
            temperature: 0.3,
            prompt,
            stream: false,
          }),
        })

        if (llmRes.ok) {
          const llmJson = await llmRes.json()
          const thinkMs = Date.now() - startTime
          setAiInsight(llmJson?.text || '')
          setAiInsightMeta({
            provider: activeProvider,
            model: activeModel,
            thinkMs,
          })
        }
      } catch (e) {
        console.warn('AI insight generation error:', e)
      }
    }, {
      feature: 'data_analysis',
      action: `圖表與AI分析：${fileName}`,
      provider: activeProvider,
      model: activeModel,
      note: `${xColumn} vs ${yColumn || 'count'}`,
    }).catch((err) => {
      setMessage(`❌ 生成失敗：${err.message}`)
    })
  }

  const maxValue = useMemo(() => Math.max(...(chart?.data?.values || [1]), 1), [chart])

  return (
    <div className="space-y-5">
      {/* ── 全畫面遮罩（讀檔與 AI 處理中） ── */}
      <LLMOverlay
        show={loading}
        model={activeModel}
        provider={activeProvider}
        elapsed={elapsedSec}
        label={overlayLabel}
      />

      <header>
        <h2 className="text-xl font-bold text-indigo-700">📊 資料分析</h2>
        <p className="text-sm text-slate-500">上傳資料檔案、選擇欄位與圖表設定，生成圖表並獲取 AI 智慧數據分析洞察。</p>
      </header>

      {/* 檔案上傳區塊 */}
      <section className="rounded-xl border border-indigo-200 bg-gradient-to-r from-indigo-50/60 to-purple-50/40 p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">📁</span>
            <div>
              <h3 className="font-semibold text-slate-800 text-sm sm:text-base">資料檔案上傳</h3>
              <p className="text-xs text-slate-500">支援 CSV、Excel (.xlsx, .xls)、JSON 等格式</p>
            </div>
          </div>
          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-indigo-700 border border-indigo-200">
            {fileName ? `📄 ${fileName}` : '尚未選取檔案'}
          </span>
        </div>

        <input
          type="file"
          accept=".csv,.xlsx,.xls,.json"
          onChange={handleFileChange}
          disabled={loading}
          className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 file:cursor-pointer cursor-pointer"
        />

        {message && (
          <div className={`text-xs font-medium px-3 py-2 rounded-lg flex items-center gap-1.5 ${
            message.startsWith('✅')
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : message.startsWith('❌')
              ? 'bg-red-50 text-red-700 border border-red-200'
              : 'bg-white text-slate-600 border border-slate-200'
          }`}>
            <span>{message}</span>
            {loading && elapsedSec > 0 && (
              <span className="ml-auto text-indigo-600 font-semibold tabular-nums">
                ⏱ {elapsedSec} 秒
              </span>
            )}
          </div>
        )}
      </section>

      {/* 資料預覽區塊 */}
      {rows.length > 0 && (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span>📋</span> 資料預覽（前 10 筆）
              </h3>
              <span className="text-xs text-slate-400">顯示前 10 列以供參考</span>
            </div>

            <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
              <div className="rounded-lg bg-slate-50 border p-2.5 text-center">
                <div className="text-xs text-slate-500">總資料列數</div>
                <div className="text-lg font-bold text-indigo-600">{rows.length}</div>
              </div>
              <div className="rounded-lg bg-slate-50 border p-2.5 text-center">
                <div className="text-xs text-slate-500">總欄位數</div>
                <div className="text-lg font-bold text-slate-700">{columns.length}</div>
              </div>
              <div className="rounded-lg bg-slate-50 border p-2.5 text-center">
                <div className="text-xs text-slate-500">數值欄位</div>
                <div className="text-lg font-bold text-emerald-600">{numeric.length}</div>
              </div>
              <div className="rounded-lg bg-slate-50 border p-2.5 text-center">
                <div className="text-xs text-slate-500">類別欄位</div>
                <div className="text-lg font-bold text-purple-600">{categorical.length}</div>
              </div>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-200 max-h-64 overflow-y-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-slate-100 sticky top-0">
                  <tr>
                    {columns.map((column) => (
                      <th key={column} className="px-3 py-2 font-semibold text-slate-700 whitespace-nowrap">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 10).map((row, index) => (
                    <tr key={index} className="border-t hover:bg-slate-50">
                      {columns.map((column) => (
                        <td key={column} className="px-3 py-2 text-slate-600 whitespace-nowrap">
                          {String(row[column] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* 圖表設定區塊 */}
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
            <h3 className="font-semibold text-slate-800 flex items-center gap-1.5">
              <span>⚙️</span> 圖表與分析設定
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
              <label className="block text-xs font-medium text-slate-700">
                X 軸欄位（分析維度）
                <select
                  className="mt-1 w-full rounded-lg border p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  value={xColumn}
                  onChange={(event) => setXColumn(event.target.value)}
                >
                  {columns.map((column) => (
                    <option key={column} value={column}>{column}</option>
                  ))}
                </select>
              </label>

              <label className="block text-xs font-medium text-slate-700">
                Y 軸欄位（數值指標）
                <select
                  className="mt-1 w-full rounded-lg border p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  value={yColumn}
                  onChange={(event) => setYColumn(event.target.value)}
                >
                  <option value="">不指定（以計數為準）</option>
                  {numeric.map((column) => (
                    <option key={column} value={column}>{column}</option>
                  ))}
                </select>
              </label>

              <label className="block text-xs font-medium text-slate-700">
                圖表類型
                <select
                  className="mt-1 w-full rounded-lg border p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  value={chartType}
                  onChange={(event) => setChartType(event.target.value)}
                >
                  <option value="bar">📊 長條圖 (Bar)</option>
                  <option value="histogram">📶 直方圖 (Histogram)</option>
                  <option value="line">📈 折線圖 (Line)</option>
                  <option value="scatter">🫧 散佈圖 (Scatter)</option>
                </select>
              </label>

              <label className="block text-xs font-medium text-slate-700">
                統計方式
                <select
                  className="mt-1 w-full rounded-lg border p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  value={aggregation}
                  onChange={(event) => setAggregation(event.target.value)}
                >
                  <option value="count">計數 (Count)</option>
                  <option value="mean">平均值 (Mean)</option>
                </select>
              </label>
            </div>

            <div className="flex items-center gap-3">
              <button
                className="rounded-lg bg-indigo-600 px-5 py-2.5 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition flex items-center gap-2 text-sm shadow-sm"
                onClick={generateChart}
                disabled={loading}
              >
                <span>🤖</span> 生成圖表與 AI 分析
              </button>
              {loading && (
                <span className="text-xs text-indigo-600 font-medium animate-pulse">
                  AI 正在運算中…（⏱ {elapsedSec} 秒）
                </span>
              )}
            </div>
          </section>
        </>
      )}

      {/* 視覺化圖表呈現 */}
      {chart && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 flex items-center gap-1.5">
              <span>📈</span> {chart.title}
            </h3>
            <span className="text-xs text-slate-500">
              類型：{chart.chart_type} / 項目數：{chart.data?.labels?.length || 0}
            </span>
          </div>

          <div className="flex h-64 items-end gap-2 overflow-x-auto border-b border-l border-slate-200 p-3 bg-slate-50/50 rounded-lg">
            {chart.data?.labels?.map((label, index) => {
              const val = chart.data?.values?.[index] ?? 0
              const barHeight = Math.max((val / maxValue) * 90, 4)
              return (
                <div key={label} className="flex min-w-14 flex-col items-center justify-end self-stretch group">
                  <span className="text-[10px] text-slate-500 font-mono mb-1 opacity-80 group-hover:opacity-100">
                    {val}
                  </span>
                  <div
                    className="w-9 bg-indigo-600 rounded-t group-hover:bg-indigo-500 transition-all shadow-sm"
                    style={{ height: `${barHeight}%` }}
                    title={`${label}: ${val}`}
                  />
                  <span className="mt-1.5 max-w-16 truncate text-[11px] text-slate-600 text-center font-medium" title={label}>
                    {label}
                  </span>
                </div>
              )
            })}
          </div>

          {/* AI 智慧數據分析洞察卡片 */}
          {aiInsight && (
            <div className="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50/70 via-indigo-50/40 to-white p-4 space-y-2">
              <div className="flex items-center justify-between border-b border-purple-100 pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🤖</span>
                  <h4 className="font-bold text-purple-900 text-sm">AI 智慧數據分析洞察</h4>
                </div>
                {aiInsightMeta && (
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[11px] font-medium text-purple-700">
                      {aiInsightMeta.provider}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-600">
                      {aiInsightMeta.model}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      ⏱ {(aiInsightMeta.thinkMs / 1000).toFixed(1)} 秒
                    </span>
                  </div>
                )}
              </div>
              <div className="text-xs sm:text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {aiInsight}
              </div>
            </div>
          )}
        </section>
      )}

      {/* 分析歷史紀錄 */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
        <h3 className="font-semibold text-slate-800 flex items-center gap-1.5">
          <span>📜</span> 分析歷史紀錄
        </h3>
        {history.length === 0 ? (
          <p className="text-xs text-slate-400">尚無分析紀錄。</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {history.slice().reverse().map((entry, index) => (
              <div key={`${entry.created_at}-${index}`} className="py-2.5 flex items-center justify-between text-xs sm:text-sm">
                <div>
                  <span className="font-semibold text-slate-800">📄 {entry.file_name}</span>
                  <span className="mx-2 text-slate-300">|</span>
                  <span className="text-indigo-600 font-medium">{entry.chart_type}</span>
                  <span className="mx-2 text-slate-300">|</span>
                  <span className="text-slate-600">{entry.x_col}{entry.y_col ? ` vs ${entry.y_col}` : ''}</span>
                </div>
                <span className="text-xs text-slate-400 tabular-nums">
                  {entry.created_at}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
