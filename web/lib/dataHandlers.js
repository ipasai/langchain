import fs from 'fs'
import path from 'path'
import XLSX from 'xlsx'

function historyPath() {
  return path.resolve(process.cwd(), '..', 'data', 'analysis_history.json')
}

function readHistory() {
  try { return JSON.parse(fs.readFileSync(historyPath(), 'utf-8')) || [] } catch (error) { return [] }
}

function writeHistory(entries) {
  fs.mkdirSync(path.dirname(historyPath()), { recursive: true })
  fs.writeFileSync(historyPath(), JSON.stringify(entries.slice(-20), null, 2), 'utf-8')
}

function parseCsv(text) {
  const lines = text.split(/\r?\n/).filter(Boolean)
  if (!lines.length) return []
  const headers = lines[0].split(',').map((value) => value.trim())
  return lines.slice(1, 201).map((line) => {
    const values = line.split(',')
    return Object.fromEntries(headers.map((header, index) => [header, values[index]?.trim() || '']))
  })
}

export function parseData(filename, buffer) {
  const ext = path.extname(filename).toLowerCase()
  if (ext === '.csv') return parseCsv(buffer.toString('utf-8'))
  if (ext === '.json') {
    const value = JSON.parse(buffer.toString('utf-8'))
    if (Array.isArray(value)) return value.slice(0, 200)
    if (value && typeof value === 'object') return Object.values(value).every(Array.isArray) ? Object.entries(value[Object.keys(value)[0]] || {}).map((entry) => entry) : [value]
  }
  if (ext === '.xlsx' || ext === '.xls') {
    const workbook = XLSX.read(buffer, { type: 'buffer' })
    return XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]).slice(0, 200)
  }
  throw new Error('目前僅支援 CSV / Excel / JSON 檔案')
}

export function columnRoles(rows) {
  const columns = Object.keys(rows[0] || {})
  const numeric = columns.filter((column) => {
    const values = rows.map((row) => row[column]).filter((value) => value !== '' && value !== null && value !== undefined)
    return values.length > 0 && values.filter((value) => Number.isFinite(Number(value))).length / values.length > 0.7
  })
  return { numeric, categorical: columns.filter((column) => !numeric.includes(column)) }
}

export function chartData(rows, chartType, xColumn, yColumn, aggregation = 'count') {
  if (!rows.length || !xColumn) return { labels: [], values: [] }
  const groups = new Map()
  rows.forEach((row) => {
    const key = String(row[xColumn] ?? '')
    const value = yColumn ? Number(row[yColumn]) : 1
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(Number.isFinite(value) ? value : 0)
  })
  const entries = [...groups.entries()].slice(0, 30)
  const values = entries.map(([, values]) => aggregation === 'mean' ? values.reduce((sum, value) => sum + value, 0) / values.length : values.length)
  return { labels: entries.map(([label]) => label), values, chartType }
}

export function saveAnalysis(entry) {
  const history = readHistory()
  history.push({ ...entry, created_at: new Date().toISOString() })
  writeHistory(history)
  return { ok: true, entries: readHistory() }
}

export function getHistory(search = '') {
  const query = String(search).toLowerCase()
  return { ok: true, entries: readHistory().filter((entry) => !query || JSON.stringify(entry).toLowerCase().includes(query)) }
}

export function deleteHistory(index) {
  const entries = readHistory()
  if (index >= 0 && index < entries.length) entries.splice(index, 1)
  writeHistory(entries)
  return { ok: true, entries }
}
