import fs from 'fs'
import path from 'path'
import axios from 'axios'

function getDataDir() {
  return path.resolve(process.cwd(), '..', 'data')
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

function loadIndex(indexPath) {
  try {
    const raw = fs.readFileSync(indexPath, 'utf-8')
    return JSON.parse(raw)
  } catch (e) {
    return []
  }
}

function saveIndex(indexPath, data) {
  fs.writeFileSync(indexPath, JSON.stringify(data, null, 2), 'utf-8')
}

export async function uploadFile({ filename, content_base64 }) {
  const dataDir = getDataDir()
  const uploadsDir = path.join(dataDir, 'uploads')
  ensureDir(uploadsDir)
  const indexPath = path.join(dataDir, 'doc_index.json')

  if (!filename || !content_base64) throw new Error('missing_params')

  const MAX = 8 * 1024 * 1024
  const buffer = Buffer.from(content_base64, 'base64')
  if (buffer.length > MAX) throw new Error('file_too_large')

  const savePath = path.join(uploadsDir, `${Date.now()}_${filename}`)
  fs.writeFileSync(savePath, buffer)

  const ext = path.extname(filename).toLowerCase()
  let extracted = ''
  try {
    if (ext === '.txt') {
      extracted = buffer.toString('utf-8')
    } else if (ext === '.json') {
      const j = JSON.parse(buffer.toString('utf-8'))
      extracted = JSON.stringify(j, null, 2)
    } else if (ext === '.csv') {
      const txt = buffer.toString('utf-8')
      const lines = txt.split(/\r?\n/).slice(0, 50).join('\n')
      extracted = lines
    } else if (ext === '.pdf') {
      try {
        // dynamic require
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const pdfParse = require('pdf-parse')
        const data = await pdfParse(buffer)
        extracted = (data && data.text) ? data.text.slice(0, 20000) : ''
      } catch (e) { extracted = '' }
    } else if (ext === '.docx' || ext === '.doc') {
      try {
        const mammoth = require('mammoth')
        const r = await mammoth.extractRawText({ buffer })
        extracted = (r && r.value) ? r.value.slice(0, 20000) : ''
      } catch (e) { extracted = '' }
    } else if (ext === '.xlsx' || ext === '.xls') {
      try {
        const XLSX = require('xlsx')
        const wb = XLSX.read(buffer, { type: 'buffer' })
        const sh = wb.Sheets[wb.SheetNames[0]]
        const csv = XLSX.utils.sheet_to_csv(sh)
        extracted = csv.split(/\r?\n/).slice(0, 200).join('\n')
      } catch (e) { extracted = '' }
    } else {
      extracted = ''
    }
  } catch (e) {
    extracted = ''
  }

  const idx = loadIndex(indexPath)
  const id = String(Date.now())
  idx.push({ id, filename, path: savePath, extracted: extracted.slice(0, 20000), indexed: false, created_at: new Date().toISOString() })
  saveIndex(indexPath, idx)

  const summary = extracted ? (extracted.slice(0, 500) + (extracted.length > 500 ? '…' : '')) : '已儲存，需進一步後端解析或索引。'
  return { ok: true, id, filename, summary, savePath }
}

export async function indexDocument({ id }) {
  const dataDir = getDataDir()
  const indexPath = path.join(dataDir, 'doc_index.json')
  const idx = loadIndex(indexPath)
  const item = idx.find((it) => it.id === String(id))
  if (!item) throw new Error('not_found')

  item.indexed = true
  item.indexed_at = new Date().toISOString()
  item.vector = null
  const chromaUrl = process.env.CHROMA_SERVER_URL || 'http://127.0.0.1:8001'
  let usedLocal = false
  try {
    await axios.get(`${chromaUrl}/health`, { timeout: 2000 })
    const fileBuffer = fs.readFileSync(item.path)
    const b64 = fileBuffer.toString('base64')
    const r = await axios.post(`${chromaUrl}/index`, { id: item.id, filename: item.filename, content_base64: b64 }, { timeout: 120000 })
    if (r.data && r.data.ok) usedLocal = true
  } catch (e) {
    const apiKey = process.env.OPENAI_API_KEY || process.env.OPENAI_KEY
    if (apiKey && item.extracted) {
      try {
        const text = String(item.extracted).slice(0, 3000)
        const embRes = await axios.post('https://api.openai.com/v1/embeddings', { input: text, model: 'text-embedding-3-small' }, { headers: { Authorization: `Bearer ${apiKey}` } })
        const vector = embRes.data && embRes.data.data && embRes.data.data[0] && embRes.data.data[0].embedding
        item.vector = vector || null
      } catch (e) { item.vector = null }
    }
  }
  saveIndex(indexPath, idx)
  return { ok: true, id: item.id, indexed: item.indexed, usedLocal }
}

export function queryIndex(q) {
  const dataDir = getDataDir()
  const indexPath = path.join(dataDir, 'doc_index.json')
  const idx = loadIndex(indexPath)
  const matches = idx
    .filter((it) => (it.extracted || '').toLowerCase().includes(String(q).toLowerCase()))
    .map((it) => ({ id: it.id, filename: it.filename, snippet: (it.extracted || '').slice(0, 400) }))
  return { ok: true, results: matches }
}

export function listDocs() {
  const dataDir = getDataDir()
  const indexPath = path.join(dataDir, 'doc_index.json')
  const idx = loadIndex(indexPath)
  return { ok: true, items: idx }
}

export async function searchDocs(q) {
  const dataDir = getDataDir()
  const indexPath = path.join(dataDir, 'doc_index.json')
  const idx = loadIndex(indexPath)
  const chromaUrl = process.env.CHROMA_SERVER_URL || 'http://127.0.0.1:8001'
  try {
    await axios.get(`${chromaUrl}/health`, { timeout: 2000 })
    const r = await axios.post(`${chromaUrl}/search`, { q }, { timeout: 120000 })
    if (r.data && r.data.ok) return { ok: true, results: r.data.results }
  } catch (e) {
    // fallback
  }

  const apiKey = process.env.OPENAI_API_KEY || process.env.OPENAI_KEY
  if (!apiKey) {
    const matches = idx
      .filter((it) => (it.extracted || '').toLowerCase().includes(String(q).toLowerCase()))
      .map((it) => ({ id: it.id, filename: it.filename, snippet: (it.extracted || '').slice(0, 400), score: 0 }))
    return { ok: true, results: matches }
  }

  const embRes = await axios.post('https://api.openai.com/v1/embeddings', { input: String(q).slice(0, 3000), model: 'text-embedding-3-small' }, { headers: { Authorization: `Bearer ${apiKey}` } })
  const qvec = embRes.data && embRes.data.data && embRes.data.data[0] && embRes.data.data[0].embedding
  if (!qvec) return { ok: false, error: 'embedding_failed' }

  function cosine(a, b) {
    if (!a || !b || a.length !== b.length) return -1
    let dot = 0, na = 0, nb = 0
    for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i] }
    if (na === 0 || nb === 0) return 0
    return dot / (Math.sqrt(na) * Math.sqrt(nb))
  }

  const candidates = idx.filter(it => it.vector && Array.isArray(it.vector))
  const scored = candidates.map(it => ({ id: it.id, filename: it.filename, snippet: (it.extracted||'').slice(0,400), score: cosine(qvec, it.vector) }))
  scored.sort((a,b)=>b.score - a.score)
  return { ok: true, results: scored.slice(0, 12) }
}

export async function mindmap({ id, prompt }) {
  const apiKey = process.env.OPENAI_API_KEY || process.env.OPENAI_KEY
  if (!apiKey) return { ok: false, error: 'missing_api_key' }
  let text = ''
  if (id) {
    const dataDir = getDataDir()
    const indexPath = path.join(dataDir, 'doc_index.json')
    const idx = loadIndex(indexPath)
    const item = idx.find(it => it.id === String(id))
    if (!item) return { ok: false, error: 'not_found' }
    text = item.extracted || ''
  } else if (prompt) {
    text = String(prompt)
  } else {
    return { ok: false, error: 'missing_input' }
  }

  const sys = { role: 'system', content: 'You are a helpful assistant that outputs a Mermaid mindmap with rules: first line "mindmap", second line "root((...))", max 3 levels, no code fences, Traditional Chinese.' }
  const user = { role: 'user', content: `請根據以下文字產生 Mermaid mindmap（只輸出 mermaid 語法，不要任何說明）：\n\n${text.slice(0,4000)}` }
  const chatRes = await axios.post('https://api.openai.com/v1/chat/completions', { model: 'gpt-3.5-turbo', messages: [sys, user], max_tokens: 800, temperature: 0.3 }, { headers: { Authorization: `Bearer ${apiKey}` } })
  const out = (chatRes.data && chatRes.data.choices && chatRes.data.choices[0] && chatRes.data.choices[0].message && chatRes.data.choices[0].message.content) || ''
  return { ok: true, mermaid: out }
}

export async function generateQuiz({ id, count = 5 }) {
  const apiKey = process.env.OPENAI_API_KEY || process.env.OPENAI_KEY
  if (!apiKey) return { ok: false, error: 'missing_api_key' }
  const dataDir = getDataDir()
  const index = loadIndex(path.join(dataDir, 'doc_index.json'))
  const item = index.find((entry) => entry.id === String(id))
  if (!item) return { ok: false, error: 'not_found' }
  const prompt = `請根據以下文件內容產生 ${Math.min(Number(count) || 5, 10)} 道四選一選擇題。只輸出 JSON 陣列，每題包含 question、options（四個字串）、answer（正確選項完整字串）、explanation。\n\n${(item.extracted || '').slice(0, 5000)}`
  const response = await axios.post('https://api.openai.com/v1/chat/completions', { model: 'gpt-4o-mini', messages: [{ role: 'user', content: prompt }], temperature: 0.2 }, { headers: { Authorization: `Bearer ${apiKey}` } })
  const raw = response.data?.choices?.[0]?.message?.content || '[]'
  const cleaned = raw.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  try { return { ok: true, questions: JSON.parse(cleaned) } }
  catch (error) { return { ok: false, error: 'invalid_quiz_response' } }
}
