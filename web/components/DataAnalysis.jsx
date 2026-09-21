import { useEffect, useMemo, useState } from 'react'

export default function DataAnalysis() {
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

  async function loadHistory() {
    const response = await fetch('/api/data?action=history')
    const data = await response.json()
    setHistory(data.entries || [])
  }
  useEffect(() => { loadHistory() }, [])

  async function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setMessage('讀取檔案中...')
    const buffer = await file.arrayBuffer()
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let index = 0; index < bytes.length; index += 0x8000) binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
    const response = await fetch('/api/data?action=analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filename: file.name, content_base64: btoa(binary) }) })
    const data = await response.json()
    if (!data.ok) return setMessage(data.detail || data.error || '分析失敗')
    setFileName(file.name); setRows(data.rows || []); setColumns(data.columns || []); setNumeric(data.numeric || []); setCategorical(data.categorical || []); setXColumn(data.defaults?.xColumn || data.columns?.[0] || ''); setYColumn(data.defaults?.yColumn || ''); setChartType(data.suggestion || 'bar'); setMessage(`已讀取 ${file.name}`)
  }

  async function generateChart() {
    const response = await fetch('/api/data?action=chart', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filename: fileName, rows, chart_type: chartType, x_col: xColumn, y_col: yColumn || undefined, aggregation, title: `${xColumn} ${yColumn ? `vs ${yColumn}` : '分類比較'}` }) })
    const data = await response.json()
    if (!data.ok) return setMessage(data.detail || data.error || '圖表產生失敗')
    setChart(data); setMessage('圖表與分析已完成')
    await fetch('/api/data?action=save_history', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ entry: { file_name: fileName, x_col: xColumn, y_col: yColumn, chart_type: chartType, saved_path: '', data: data.data } }) })
    await loadHistory()
  }

  const maxValue = useMemo(() => Math.max(...(chart?.data?.values || [1]), 1), [chart])

  return <div className="space-y-5"><header><h2 className="text-xl font-bold text-indigo-700">📊 資料分析</h2><p className="text-sm text-slate-500">上傳資料、選擇欄位與圖表設定，再生成圖表與分析紀錄。</p></header>
    <section className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4"><input type="file" accept=".csv,.xlsx,.xls,.json" onChange={handleFileChange} /><p className="mt-2 text-sm text-slate-600">{message}</p></section>
    {rows.length > 0 && <><section className="rounded-xl border p-4"><h3 className="mb-3 font-semibold">📋 資料預覽</h3><div className="mb-3 grid gap-3 sm:grid-cols-3"><div>資料列數：<strong>{rows.length}</strong></div><div>欄位數：<strong>{columns.length}</strong></div><div>數值欄位：<strong>{numeric.length}</strong></div></div><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="bg-slate-100"><tr>{columns.map((column) => <th key={column} className="px-3 py-2">{column}</th>)}</tr></thead><tbody>{rows.slice(0, 10).map((row, index) => <tr key={index} className="border-t">{columns.map((column) => <td key={column} className="px-3 py-2">{String(row[column] ?? '')}</td>)}</tr>)}</tbody></table></div></section>
      <section className="rounded-xl border p-4"><h3 className="mb-3 font-semibold">⚙️ 圖表設定</h3><div className="grid gap-3 md:grid-cols-4"><label>X 欄位<select className="mt-1 w-full rounded border p-2" value={xColumn} onChange={(event) => setXColumn(event.target.value)}>{columns.map((column) => <option key={column}>{column}</option>)}</select></label><label>Y 欄位<select className="mt-1 w-full rounded border p-2" value={yColumn} onChange={(event) => setYColumn(event.target.value)}><option value="">不指定</option>{numeric.map((column) => <option key={column}>{column}</option>)}</select></label><label>圖表類型<select className="mt-1 w-full rounded border p-2" value={chartType} onChange={(event) => setChartType(event.target.value)}><option value="bar">長條圖</option><option value="histogram">直方圖</option><option value="line">折線圖</option><option value="scatter">散佈圖</option></select></label><label>統計方式<select className="mt-1 w-full rounded border p-2" value={aggregation} onChange={(event) => setAggregation(event.target.value)}><option value="count">計數</option><option value="mean">平均值</option></select></label></div><button className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-white" onClick={generateChart}>🤖 生成圖表與分析</button></section></>}
    {chart && <section className="rounded-xl border p-4"><h3 className="mb-3 font-semibold">📈 {chart.title}</h3><div className="flex h-64 items-end gap-2 overflow-x-auto border-b border-l p-3">{chart.data.labels.map((label, index) => <div key={label} className="flex min-w-12 flex-col items-center justify-end self-stretch"><div className="w-8 bg-indigo-500" style={{ height: `${Math.max((chart.data.values[index] / maxValue) * 90, 4)}%` }} title={`${label}: ${chart.data.values[index]}`} /><span className="mt-1 max-w-16 truncate text-xs">{label}</span></div>)}</div></section>}
    <section className="rounded-xl border p-4"><h3 className="mb-3 font-semibold">📜 歷史紀錄</h3>{history.length === 0 ? <p className="text-sm text-slate-500">尚無分析紀錄。</p> : history.slice().reverse().map((entry, index) => <div key={`${entry.created_at}-${index}`} className="border-t py-2 text-sm"><strong>{entry.file_name}</strong>：{entry.chart_type} / {entry.x_col}{entry.y_col ? ` vs ${entry.y_col}` : ''}<span className="ml-2 text-slate-500">{entry.created_at}</span></div>)}</section>
  </div>
}
