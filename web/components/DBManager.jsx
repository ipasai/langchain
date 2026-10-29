import { useState, useRef } from 'react'
import { useLLMGuard } from '../lib/useLLMGuard'
import LLMOverlay from './LLMOverlay'

const TABS = [
  { id: 'connection', label: '🔌 連線設定' },
  { id: 'tables',     label: '🔍 資料表' },
  { id: 'sql',        label: '▶️ SQL 查詢' },
  { id: 'crud',       label: '📝 CRUD' },
]

export default function DBManager() {
  const [activeTab, setActiveTab] = useState('connection')

  // ── 連線設定狀態 ─────────────────────────────────────────────
  const [filepath, setFilepath] = useState('data/app_memory.db')
  const [dbType, setDbType] = useState('sqlite')
  const [config, setConfig] = useState({
    host: 'localhost', port: '3306', user: 'root',
    password: '', database: '', uri: 'mongodb://localhost:27017',
    db: '0', charset: 'utf8mb4',
  })
  const [connMessage, setConnMessage] = useState('')

  // ── 資料表狀態 ──────────────────────────────────────────────
  const [analysis, setAnalysis] = useState(null)
  const [selectedTable, setSelectedTable] = useState('')
  const [preview, setPreview] = useState(null)
  const [tableMessage, setTableMessage] = useState('')

  // ── LLM 分析狀態 ────────────────────────────────────────────
  const [llmAnalysis, setLlmAnalysis] = useState('')
  const [llmDone, setLlmDone] = useState(false)
  const [llmMeta, setLlmMeta] = useState(null)
  const { loading: llmLoading, elapsedSec: llmElapsed, run: llmRun } = useLLMGuard()
  const llmAbortRef = useRef(null)

  // ── SQL 狀態 ────────────────────────────────────────────────
  const [query, setQuery] = useState('SELECT * FROM english_practice LIMIT 10;')
  const [queryResult, setQueryResult] = useState(null)
  const [sqlMessage, setSqlMessage] = useState('')

  // ── 自然語言轉 SQL 狀態 ───────────────────────────────────────
  const [nlPrompt, setNlPrompt] = useState('')
  const [generatedSql, setGeneratedSql] = useState('')
  const [generatedExplanation, setGeneratedExplanation] = useState('')
  const [nlError, setNlError] = useState('')
  const [nlCopied, setNlCopied] = useState(false)
  const [overlayLabel, setOverlayLabel] = useState('AI 正在分析資料庫…')

  // ── CRUD 狀態 ───────────────────────────────────────────────
  const [crudMode, setCrudMode] = useState('insert')
  const [crudTable, setCrudTable] = useState('')
  const [crudValues, setCrudValues] = useState('{}')
  const [whereClause, setWhereClause] = useState('')
  const [whereValues, setWhereValues] = useState('')
  const [crudMessage, setCrudMessage] = useState('')

  // ── 共用 loading ────────────────────────────────────────────
  const [loading, setLoading] = useState(false)

  // ── API 工具 ────────────────────────────────────────────────
  async function call(action, body = {}) {
    const res = await fetch('/api/db', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, filepath, ...body }),
    })
    const data = await res.json()
    if (!res.ok || data.error) throw new Error(data.detail || data.message || data.error)
    return data
  }

  function connectionConfig() {
    return { type: dbType, filepath, ...config }
  }

  // ── 連線 & 分析 ─────────────────────────────────────────────
  async function inspect() {
    setLoading(true)
    setConnMessage('')
    try {
      const data = dbType === 'sqlite'
        ? await call('inspect')
        : await call('external_test', { config: connectionConfig() })
      setAnalysis(data)
      const first = data.tables?.[0]?.name || ''
      setSelectedTable(first)
      setCrudTable(first)
      setConnMessage(`✅ 連線成功：${data.database}`)
      if (first) await loadPreview(first)
      // 重置舊的 LLM 分析，切到資料表頁籤，自動觸發 LLM 分析
      setLlmAnalysis('')
      setLlmDone(false)
      setLlmMeta(null)
      setActiveTab('tables')
      analyzeWithLLM(data)
    } catch (error) {
      setConnMessage(`❌ 連線失敗：${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 將資料庫結構整理成 prompt，透過 /api/llm 串流分析。
   * provider/model 從 localStorage 的 tab_settings_database 讀取，
   * 若無記錄則 fallback 到 openai / gpt-4o-mini。
   */
  async function analyzeWithLLM(dbData) {
    if (llmAbortRef.current) llmAbortRef.current.abort()
    const controller = new AbortController()
    llmAbortRef.current = controller

    setLlmAnalysis('')
    setLlmDone(false)
    setLlmMeta(null)

    // 讀取目前頁籤的 provider/model 設定
    let provider = 'openai'
    let model = 'gpt-4o-mini'
    try {
      const saved = JSON.parse(localStorage.getItem('tab_settings_database') || '{}')
      if (saved.provider) provider = saved.provider
      if (saved.model) model = saved.model.split(' (')[0]
    } catch (_) {}

    const tableDetails = (dbData.tables || []).map((t) => {
      const cols = (t.columns || []).map((c) =>
        `    - ${c.name} (${c.type}${c.pk ? ', PRIMARY KEY' : ''}${c.notnull ? ', NOT NULL' : ''}${c.dflt_value != null ? `, DEFAULT ${c.dflt_value}` : ''})`
      ).join('\n')
      return `  資料表「${t.name}」（${t.row_count} 列）：\n${cols || '    （無欄位資訊）'}`
    }).join('\n\n')

    const prompt = `你是一位資深資料庫架構師。請分析以下資料庫結構，以繁體中文輸出完整分析報告，格式如下：

## 📊 資料庫概覽
（說明資料庫類型、版本、整體用途推測）

## 📋 資料表詳解
（逐表說明：用途推測、各欄位意義、資料類型意義、主鍵與索引策略）

## 🔗 資料表關聯推測
（根據欄位命名推測可能的 FK 關係或業務邏輯關聯）

## ⚠️ 設計限制與注意事項
（指出潛在問題：缺少索引、缺少 NOT NULL、命名不一致等）

## 💡 功能使用建議
（建議如何善用此資料庫，並附上常見查詢 SQL 範例）

--- 資料庫結構 ---
類型：${dbData.db_type || dbData.type || dbType}
版本：${dbData.version || '未知'}
名稱：${dbData.database || filepath}
資料表數：${dbData.tables?.length || 0}

${tableDetails}`

    setOverlayLabel('AI 正在分析資料庫結構…')
    await llmRun(async () => {
      const startTime = Date.now()
      const useStream = provider === 'openai' || provider === 'ollama'
      const res = await fetch('/api/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'chat', provider, model, temperature: 0.3, prompt, stream: useStream }),
        signal: controller.signal,
      })

      if (!res.ok) {
        let msg = ''
        try {
          const errJson = await res.json()
          msg = errJson.message || errJson.error || JSON.stringify(errJson)
        } catch {
          msg = await res.text()
        }
        throw new Error(msg || `HTTP ${res.status}`)
      }

      if (useStream && res.body) {
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let text = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split('\n\n')
          buffer = events.pop() || ''
          for (const event of events) {
            const line = event.split('\n').find((l) => l.startsWith('data:'))
            if (!line) continue
            const payload = line.slice(5).trim()
            if (payload === '[DONE]') continue
            try {
              const chunk = JSON.parse(payload)
              text += chunk.text || chunk.choices?.[0]?.delta?.content || ''
              setLlmAnalysis(text)
            } catch (_) {}
          }
        }
      } else {
        const json = await res.json()
        setLlmAnalysis(json?.text || JSON.stringify(json))
      }
      setLlmDone(true)
      setLlmMeta({ model, provider, thinkMs: Date.now() - startTime })
    }, {
      feature: 'db_analysis',
      action: '分析資料庫結構',
      model,
      provider,
      note: dbData.database || filepath,
    }).catch(err => {
      if (err.name !== 'AbortError') {
        setLlmAnalysis(`⚠️ 分析失敗：${err.message}\n\n請確認側邊欄的 AI 模型設定正確後，點「重新分析」。`)
        setLlmDone(true)
      }
    })
  }

  // ── 預覽資料表 ──────────────────────────────────────────────
  async function loadPreview(table) {
    if (!table) return
    setTableMessage('')
    try {
      const data = dbType === 'sqlite'
        ? await call('preview', { table, limit: 10 })
        : await call('external_preview', { config: connectionConfig(), table, limit: 10 })
      setPreview(data)
    } catch (error) {
      setTableMessage(`預覽失敗：${error.message}`)
    }
  }

  // ── 執行 SQL ────────────────────────────────────────────────
  async function runSql(sqlOverride) {
    const targetQuery = typeof sqlOverride === 'string' ? sqlOverride : query
    if (!targetQuery || !targetQuery.trim()) {
      setSqlMessage('❌ 請先輸入 SQL 語句')
      return
    }
    setLoading(true)
    setSqlMessage('')
    try {
      const data = dbType === 'sqlite'
        ? await call('execute_sql', { query: targetQuery })
        : await call('external_sql', { config: connectionConfig(), query: targetQuery })
      setQueryResult(data)
      setSqlMessage(`✅ SQL 執行成功，共 ${data.rows?.length ?? 0} 列`)
    } catch (error) {
      setSqlMessage(`❌ SQL 執行失敗：${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // ── 自然語言轉 SQL ──────────────────────────────────────────
  async function generateSqlFromNL() {
    if (!nlPrompt.trim()) {
      setNlError('請先輸入想要查詢的自然語言描述')
      return
    }
    if (!isSQLSupported) {
      setNlError('目前僅支援關聯式 SQL 資料庫（SQLite, MySQL, PostgreSQL, MariaDB）')
      return
    }
    setNlError('')
    setGeneratedSql('')
    setGeneratedExplanation('')

    // 若尚未載入 schema，先嘗試取得
    let currentAnalysis = analysis
    if (!currentAnalysis) {
      try {
        setLoading(true)
        currentAnalysis = dbType === 'sqlite'
          ? await call('inspect')
          : await call('external_test', { config: connectionConfig() })
        setAnalysis(currentAnalysis)
      } catch (e) {
        setNlError(`無法取得資料庫結構：${e.message}。請先至「連線設定」確認連線正常。`)
        return
      } finally {
        setLoading(false)
      }
    }

    const tableDetails = (currentAnalysis?.tables || []).map((t) => {
      const cols = (t.columns || []).map((c) =>
        `    - ${c.name} (${c.type}${c.pk ? ', PRIMARY KEY' : ''})`
      ).join('\n')
      return `  資料表「${t.name}」：\n${cols || '    （無欄位資訊）'}`
    }).join('\n\n')

    const prompt = `你是一位資深的 ${dbType} 資料庫架構師。請根據下方提供的資料庫結構，將使用者的自然語言查詢需求轉換為精準且完全相容 ${dbType} 語法的 SQL 查詢。

--- 資料庫結構 ---
類型：${dbType}
資料庫：${currentAnalysis?.database || filepath}
${tableDetails || '（無資料表結構資訊）'}

--- 使用者查詢需求 ---
${nlPrompt.trim()}

請嚴格遵循以下輸出格式：
1. 必須提供一個以 \`\`\`sql 開頭、以 \`\`\` 結尾的完整 SQL 程式碼區塊，裡面只能放可直接執行的 SQL，不要放額外註釋或說明。
2. 在代碼區塊下方，請附上 1~2 句簡要的繁體中文說明（例如使用的篩選條件或排序邏輯）。`

    // 讀取設定
    let provider = 'openai'
    let model = 'gpt-4o-mini'
    try {
      const saved = JSON.parse(localStorage.getItem('tab_settings_database') || '{}')
      if (saved.provider) provider = saved.provider
      if (saved.model) model = saved.model.split(' (')[0]
    } catch (_) {}

    setOverlayLabel('AI 正在透過自然語言生成 SQL…')
    setLlmMeta({ model, provider, thinkMs: 0 })

    await llmRun(async () => {
      const startTime = Date.now()
      const res = await fetch('/api/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'chat',
          provider,
          model,
          temperature: 0.1,
          prompt,
          stream: false,
        }),
      })

      if (!res.ok) {
        let msg = ''
        try {
          const errJson = await res.json()
          msg = errJson.message || errJson.error || JSON.stringify(errJson)
        } catch {
          msg = await res.text()
        }
        throw new Error(msg || `HTTP ${res.status}`)
      }

      const json = await res.json()
      const rawText = json?.text || ''

      // 解析 SQL 與說明
      const sqlMatch = rawText.match(/```(?:sql)?\s*([\s\S]*?)\s*```/i)
      let extractedSql = ''
      let explanation = ''
      if (sqlMatch) {
        extractedSql = sqlMatch[1].trim()
        explanation = rawText.replace(sqlMatch[0], '').trim()
      } else {
        const lines = rawText.split('\n')
        const firstSqlIdx = lines.findIndex(l => /^\s*(SELECT|INSERT|UPDATE|DELETE|WITH|SHOW|CREATE|ALTER|DROP)\b/i.test(l))
        if (firstSqlIdx !== -1) {
          extractedSql = lines.slice(firstSqlIdx).join('\n').trim()
          explanation = lines.slice(0, firstSqlIdx).join('\n').trim()
        } else {
          extractedSql = rawText.trim()
        }
      }

      setGeneratedSql(extractedSql)
      setGeneratedExplanation(explanation)
      setLlmMeta({ model, provider, thinkMs: Date.now() - startTime })
    }, {
      feature: 'db_nl2sql',
      action: '自然語言生成 SQL',
      model,
      provider,
      note: nlPrompt.slice(0, 50),
    }).catch(err => {
      setNlError(`生成失敗：${err.message}`)
    })
  }

  // ── CRUD ────────────────────────────────────────────────────
  async function runCrud() {
    setLoading(true)
    setCrudMessage('')
    try {
      const values = JSON.parse(crudValues || '{}')
      const valuesList = whereValues ? whereValues.split(',').map((v) => v.trim()) : []
      const data = crudMode === 'insert'
        ? await call('insert_row', { table: crudTable, values })
        : crudMode === 'update'
          ? await call('update_row', { table: crudTable, values, where_clause: whereClause, where_values: valuesList })
          : await call('delete_row', { table: crudTable, where_clause: whereClause, where_values: valuesList })
      setCrudMessage(`✅ 操作成功，影響 ${data.row_count} 列`)
      if (crudTable) await loadPreview(crudTable)
    } catch (error) {
      setCrudMessage(`❌ 操作失敗：${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // ── 共用 Table 元件 ─────────────────────────────────────────
  function DataTable({ columns, rows }) {
    if (!columns?.length) return null
    return (
      <div className="overflow-x-auto rounded-lg border">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-100">
            <tr>{columns.map((col) => <th key={col} className="px-3 py-2 font-semibold">{col}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t hover:bg-slate-50">
                {columns.map((col) => <td key={col} className="px-3 py-2">{String(row[col] ?? '')}</td>)}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={columns.length} className="px-3 py-4 text-center text-slate-400">無資料</td></tr>
            )}
          </tbody>
        </table>
      </div>
    )
  }

  // ── 頁籤內容 ────────────────────────────────────────────────
  const isSQLSupported = dbType !== 'redis' && dbType !== 'mongodb'
  const isCRUDSupported = dbType === 'sqlite'

  return (
    <div className="space-y-4">
      {/* LLM 分析遮罩 */}
      <LLMOverlay
        show={llmLoading}
        model={llmMeta?.model || ''}
        provider={llmMeta?.provider || ''}
        elapsed={llmElapsed}
        label={overlayLabel || 'AI 正在處理…'}
      />
      <header>
        <h2 className="text-xl font-bold text-indigo-700">🗄️ 資料庫管理</h2>
        <p className="text-sm text-slate-500">連線設定、資料表瀏覽、SQL 執行與資料列 CRUD。</p>
      </header>

      {/* 頁籤列 */}
      <div className="flex gap-1 overflow-x-auto border-b border-indigo-100">
        {TABS.map((tab) => {
          const disabled =
            (tab.id === 'tables' && !analysis) ||
            (tab.id === 'sql' && (!analysis || !isSQLSupported)) ||
            (tab.id === 'crud' && (!analysis || !isCRUDSupported))
          return (
            <button
              key={tab.id}
              type="button"
              disabled={disabled}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-semibold transition
                ${activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-700'
                  : disabled
                    ? 'border-transparent text-slate-300 cursor-not-allowed'
                    : 'border-transparent text-slate-500 hover:border-indigo-300 hover:text-indigo-600'}`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* ── 頁籤：連線設定 ── */}
      {activeTab === 'connection' && (
        <section className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 space-y-3">
          <h3 className="font-semibold text-indigo-900">資料庫類型與連線資訊</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            <select className="rounded-lg border p-2" value={dbType} onChange={(e) => setDbType(e.target.value)}>
              <option value="sqlite">SQLite</option>
              <option value="mysql">MySQL</option>
              <option value="mariadb">MariaDB</option>
              <option value="postgres">PostgreSQL</option>
              <option value="redis">Redis</option>
              <option value="mongodb">MongoDB</option>
            </select>

            {dbType === 'sqlite' && (
              <input className="rounded-lg border p-2" value={filepath}
                onChange={(e) => setFilepath(e.target.value)} placeholder="SQLite 檔案路徑" />
            )}
            {dbType === 'mongodb' && (
              <input className="rounded-lg border p-2" value={config.uri}
                onChange={(e) => setConfig({ ...config, uri: e.target.value })} placeholder="MongoDB URI" />
            )}
            {dbType !== 'sqlite' && dbType !== 'mongodb' && (
              <input className="rounded-lg border p-2" value={config.host}
                onChange={(e) => setConfig({ ...config, host: e.target.value })} placeholder="主機 host" />
            )}
            {dbType !== 'sqlite' && dbType !== 'mongodb' && (
              <input className="rounded-lg border p-2" value={config.port}
                onChange={(e) => setConfig({ ...config, port: e.target.value })} placeholder="連接埠" />
            )}
            {['mysql', 'mariadb', 'postgres'].includes(dbType) && (<>
              <input className="rounded-lg border p-2" value={config.user}
                onChange={(e) => setConfig({ ...config, user: e.target.value })} placeholder="使用者" />
              <input type="password" className="rounded-lg border p-2" value={config.password}
                onChange={(e) => setConfig({ ...config, password: e.target.value })} placeholder="密碼" />
              <input className="rounded-lg border p-2" value={config.database}
                onChange={(e) => setConfig({ ...config, database: e.target.value })} placeholder="資料庫名稱" />
            </>)}
            {dbType === 'redis' && (
              <input className="rounded-lg border p-2" value={config.db}
                onChange={(e) => setConfig({ ...config, db: e.target.value })} placeholder="Redis DB index" />
            )}
            {dbType === 'mongodb' && (
              <input className="rounded-lg border p-2" value={config.database}
                onChange={(e) => setConfig({ ...config, database: e.target.value })} placeholder="資料庫名稱" />
            )}
          </div>

          <button
            className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            onClick={inspect} disabled={loading}
          >
            {loading ? '連線中…' : '🔌 測試連線'}
          </button>

          {connMessage && (
            <p className={`text-sm font-medium ${connMessage.startsWith('✅') ? 'text-emerald-700' : 'text-red-600'}`}>
              {connMessage}
            </p>
          )}
        </section>
      )}

      {/* ── 頁籤：資料表 ── */}
      {activeTab === 'tables' && analysis && (
        <section className="space-y-4">
          {/* 摘要卡 */}
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ['資料庫類型', analysis.db_type],
              ['版本', analysis.version],
              ['資料表數', analysis.tables?.length ?? 0],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border bg-white p-3">
                <div className="text-xs text-slate-500">{label}</div>
                <strong className="text-slate-800">{value}</strong>
              </div>
            ))}
          </div>

          {/* 資料表按鈕 */}
          <div className="flex flex-wrap gap-2">
            {analysis.tables?.map((table) => (
              <button
                key={table.name}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition
                  ${selectedTable === table.name
                    ? 'border-indigo-600 bg-indigo-100 text-indigo-800'
                    : 'bg-white hover:bg-indigo-50'}`}
                onClick={() => { setSelectedTable(table.name); setCrudTable(table.name); loadPreview(table.name) }}
              >
                {table.name}
                <span className="ml-1 text-xs text-slate-400">({table.row_count})</span>
              </button>
            ))}
          </div>

          {tableMessage && <p className="text-sm text-red-600">{tableMessage}</p>}

          {/* 資料預覽 */}
          {preview && (
            <>
              <h4 className="font-semibold text-slate-700">
                📋 {selectedTable} 預覽
                <span className="ml-2 text-xs font-normal text-slate-400">前 10 列</span>
              </h4>
              <DataTable columns={preview.columns} rows={preview.rows} />
            </>
          )}

          {/* ── LLM 智慧分析區塊 ── */}
          <div className="rounded-xl border border-violet-200 bg-violet-50/40">
            <div className="flex items-center justify-between px-4 py-3 border-b border-violet-100">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-base font-semibold text-violet-800">🤖 AI 資料庫分析</span>
                {llmLoading && (
                  <span className="flex items-center gap-1 text-xs text-violet-600">
                    <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                    </svg>
                    分析中… {llmElapsed > 0 && <span className="tabular-nums">{llmElapsed} 秒</span>}
                  </span>
                )}
                {llmDone && !llmLoading && llmMeta && (
                  <span className="flex items-center gap-1.5">
                    <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-medium text-violet-600">
                      {llmMeta.provider}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500 font-mono">
                      {llmMeta.model}
                    </span>
                    <span className="text-[11px] text-emerald-600 font-medium">
                      ✓ {llmMeta.thinkMs < 1000
                        ? `${llmMeta.thinkMs} ms`
                        : `${(llmMeta.thinkMs / 1000).toFixed(1)} 秒`}
                    </span>
                  </span>
                )}
              </div>
              <button
                type="button"
                disabled={llmLoading}
                onClick={() => analyzeWithLLM(analysis)}
                className="rounded-lg border border-violet-300 bg-white px-3 py-1 text-xs font-semibold text-violet-700 hover:bg-violet-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                🔄 重新分析
              </button>
            </div>

            <div className="px-4 py-3">
              {!llmAnalysis && !llmLoading && (
                <p className="text-sm text-slate-400 text-center py-4">
                  連線後將自動分析資料庫結構，或點「重新分析」手動觸發。
                </p>
              )}
              {llmAnalysis && (
                <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap leading-relaxed">
                  <LlmMarkdown text={llmAnalysis} />
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* ── 頁籤：SQL 查詢 ── */}
      {activeTab === 'sql' && (
        <section className="space-y-4">
          {/* 自然語言轉 SQL 區塊 */}
          <div className="rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50/80 via-purple-50/40 to-white p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">🧠</span>
                <div>
                  <h4 className="font-bold text-indigo-900 text-sm sm:text-base">自然語言轉 SQL（Text-to-SQL）</h4>
                  <p className="text-xs text-slate-500">輸入中文需求，AI 會自動根據當前資料庫結構生成對應的 SQL 語法</p>
                </div>
              </div>
              <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                AI 智慧輔助
              </span>
            </div>

            {/* 快速提示範例 */}
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-slate-400 font-medium">常見範例：</span>
              {[
                '查詢最新 10 筆學習英文單字紀錄',
                '統計各單字分類的單字數量並由多到少排列',
                '查詢測驗正確率低於 60% 的歷史紀錄',
                '查詢各資料表的名稱與記錄筆數',
              ].map((sample) => (
                <button
                  key={sample}
                  type="button"
                  className="rounded-full border border-indigo-200 bg-white px-2.5 py-1 text-indigo-700 hover:bg-indigo-50 hover:border-indigo-300 transition"
                  onClick={() => setNlPrompt(sample)}
                >
                  {sample}
                </button>
              ))}
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <textarea
                rows={2}
                className="flex-1 rounded-lg border border-slate-300 bg-white p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-y"
                placeholder="請用自然語言描述想查詢的內容（例如：查詢所有測驗總分大於 80 分的紀錄，依時間新到舊排序）…"
                value={nlPrompt}
                onChange={(e) => setNlPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault()
                    generateSqlFromNL()
                  }
                }}
              />
              <button
                type="button"
                className="self-stretch sm:self-auto rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition shrink-0 flex items-center justify-center gap-1.5 text-sm"
                onClick={generateSqlFromNL}
                disabled={llmLoading || !nlPrompt.trim()}
              >
                <span>✨</span> 生成 SQL
              </button>
            </div>

            {nlError && (
              <div className="rounded-lg bg-red-50 border border-red-200 p-2.5 text-xs text-red-600">
                ❌ {nlError}
              </div>
            )}

            {/* 生成結果卡片 */}
            {generatedSql && (
              <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 text-slate-100 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800 pb-2 flex-wrap gap-2">
                  <span className="font-semibold text-emerald-400 flex items-center gap-1">
                    <span>💡</span> 建議 SQL 語法（{dbType}）
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700 text-xs text-slate-200 transition"
                      onClick={() => {
                        navigator.clipboard.writeText(generatedSql)
                        setNlCopied(true)
                        setTimeout(() => setNlCopied(false), 2000)
                      }}
                    >
                      {nlCopied ? '✅ 已複製！' : '📋 複製 SQL'}
                    </button>
                    <button
                      type="button"
                      className="rounded bg-indigo-600 px-2.5 py-1 font-medium text-xs text-white hover:bg-indigo-500 transition"
                      onClick={() => {
                        setQuery(generatedSql)
                        setSqlMessage('📋 已將 AI 產生的 SQL 填入編輯器')
                      }}
                    >
                      📥 填入編輯器
                    </button>
                    <button
                      type="button"
                      className="rounded bg-emerald-600 px-2.5 py-1 font-semibold text-xs text-white hover:bg-emerald-500 transition"
                      onClick={() => {
                        setQuery(generatedSql)
                        runSql(generatedSql)
                      }}
                    >
                      ▶️ 填入並執行
                    </button>
                  </div>
                </div>

                <pre className="font-mono text-xs text-emerald-400 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {generatedSql}
                </pre>

                {generatedExplanation && (
                  <p className="text-xs text-slate-400 border-t border-slate-800 pt-2 leading-relaxed">
                    <span className="text-indigo-300 font-medium">說明：</span>{generatedExplanation}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* 原有 SQL 編輯器 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-indigo-900">SQL 查詢編輯器</h3>
              <span className="text-xs text-slate-400">快速鍵：Ctrl+Enter 或 Cmd+Enter 執行</span>
            </div>
            <textarea
              className="min-h-32 w-full rounded-lg border p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runSql() }}
              placeholder="輸入 SQL 語句（Ctrl+Enter 執行）"
            />
            <div className="flex items-center gap-3">
              <button
                className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition"
                onClick={() => runSql()} disabled={loading}
              >
                {loading ? '執行中…' : '▶️ 執行 SQL'}
              </button>
              {sqlMessage && (
                <span className={`text-sm font-medium ${sqlMessage.startsWith('✅') ? 'text-emerald-700' : 'text-red-600'}`}>
                  {sqlMessage}
                </span>
              )}
            </div>
          </div>

          {queryResult && (
            <>
              <h4 className="font-semibold text-slate-700">查詢結果</h4>
              <DataTable columns={queryResult.columns} rows={queryResult.rows} />
            </>
          )}
        </section>
      )}

      {/* ── 頁籤：CRUD ── */}
      {activeTab === 'crud' && (
        <section className="space-y-3">
          <h3 className="font-semibold text-indigo-900">資料列 CRUD</h3>

          <div className="grid gap-2 sm:grid-cols-3">
            <label className="block text-sm font-medium text-slate-700">
              操作類型
              <select
                className="mt-1 w-full rounded-lg border p-2"
                value={crudMode}
                onChange={(e) => setCrudMode(e.target.value)}
              >
                <option value="insert">新增 (INSERT)</option>
                <option value="update">更新 (UPDATE)</option>
                <option value="delete">刪除 (DELETE)</option>
              </select>
            </label>

            <label className="block text-sm font-medium text-slate-700">
              資料表
              <input
                className="mt-1 w-full rounded-lg border p-2"
                value={crudTable}
                onChange={(e) => setCrudTable(e.target.value)}
                placeholder="資料表名稱"
              />
            </label>

            {crudMode !== 'insert' && (
              <label className="block text-sm font-medium text-slate-700">
                WHERE 條件
                <input
                  className="mt-1 w-full rounded-lg border p-2"
                  value={whereClause}
                  onChange={(e) => setWhereClause(e.target.value)}
                  placeholder="例如 id = ?"
                />
              </label>
            )}
          </div>

          {crudMode !== 'delete' && (
            <label className="block text-sm font-medium text-slate-700">
              欄位值（JSON 格式）
              <textarea
                className="mt-1 min-h-24 w-full rounded-lg border p-2 font-mono text-sm"
                value={crudValues}
                onChange={(e) => setCrudValues(e.target.value)}
                placeholder='{"english":"hello","translation":"你好"}'
              />
            </label>
          )}

          {crudMode !== 'insert' && (
            <label className="block text-sm font-medium text-slate-700">
              WHERE 條件值（逗號分隔）
              <input
                className="mt-1 w-full rounded-lg border p-2"
                value={whereValues}
                onChange={(e) => setWhereValues(e.target.value)}
                placeholder="例如：1"
              />
            </label>
          )}

          <div className="flex items-center gap-3">
            <button
              className="rounded-lg bg-amber-500 px-5 py-2 font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
              onClick={runCrud} disabled={loading}
            >
              {loading ? '執行中…' : '💾 執行'}
            </button>
            {crudMessage && (
              <span className={`text-sm font-medium ${crudMessage.startsWith('✅') ? 'text-emerald-700' : 'text-red-600'}`}>
                {crudMessage}
              </span>
            )}
          </div>

          {/* CRUD 後的資料表預覽 */}
          {preview && crudTable === selectedTable && (
            <>
              <h4 className="font-semibold text-slate-700">📋 {crudTable} 目前資料</h4>
              <DataTable columns={preview.columns} rows={preview.rows} />
            </>
          )}
        </section>
      )}
    </div>
  )
}

/**
 * 輕量 Markdown 渲染：支援 ## 標題、**粗體**、`code`、```程式區塊```、- 列表
 * 不引入外部套件，避免增加 bundle 體積。
 */
function LlmMarkdown({ text }) {
  if (!text) return null

  const lines = text.split('\n')
  const elements = []
  let codeBlock = []
  let inCode = false
  let listItems = []

  function flushList() {
    if (listItems.length === 0) return
    elements.push(
      <ul key={`ul-${elements.length}`} className="my-1 ml-4 list-disc space-y-0.5">
        {listItems.map((item, i) => (
          <li key={i} className="text-slate-700">{renderInline(item)}</li>
        ))}
      </ul>
    )
    listItems = []
  }

  function renderInline(str) {
    // **粗體** 與 `code`
    const parts = str.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**'))
        return <strong key={i}>{part.slice(2, -2)}</strong>
      if (part.startsWith('`') && part.endsWith('`'))
        return <code key={i} className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs text-violet-700">{part.slice(1, -1)}</code>
      return part
    })
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith('```')) {
      if (inCode) {
        elements.push(
          <pre key={`pre-${i}`} className="my-2 overflow-x-auto rounded-lg bg-slate-800 p-3 text-xs text-slate-100 font-mono">
            {codeBlock.join('\n')}
          </pre>
        )
        codeBlock = []
        inCode = false
      } else {
        flushList()
        inCode = true
      }
      continue
    }

    if (inCode) { codeBlock.push(line); continue }

    if (line.startsWith('## ')) {
      flushList()
      elements.push(
        <h3 key={i} className="mt-4 mb-1 text-base font-bold text-violet-800 border-b border-violet-100 pb-1">
          {line.slice(3)}
        </h3>
      )
    } else if (line.startsWith('### ')) {
      flushList()
      elements.push(
        <h4 key={i} className="mt-3 mb-0.5 text-sm font-bold text-slate-700">{line.slice(4)}</h4>
      )
    } else if (line.match(/^[-*] /)) {
      listItems.push(line.slice(2))
    } else if (line.trim() === '') {
      flushList()
      elements.push(<div key={i} className="h-2" />)
    } else {
      flushList()
      elements.push(<p key={i} className="text-sm leading-relaxed text-slate-700">{renderInline(line)}</p>)
    }
  }

  flushList()
  return <div>{elements}</div>
}
