import { chartData, columnRoles, deleteHistory, getHistory, parseData, saveAnalysis } from '../../lib/dataHandlers'

export default function handler(req, res) {
  const action = req.query.action || req.body?.action || ''
  try {
    if (action === 'test') return res.json({ ok: true, message: 'data api ready' })
    if (action === 'history') return res.json(getHistory(req.query.search || ''))
    if (action === 'delete_history' && req.method === 'POST') return res.json(deleteHistory(Number(req.body.index)))

    if (action === 'analyze' && req.method === 'POST') {
      const { filename, content_base64 } = req.body || {}
      if (!filename || !content_base64) return res.status(400).json({ error: 'missing_params' })
      const rows = parseData(filename, Buffer.from(content_base64, 'base64'))
      const roles = columnRoles(rows)
      const xColumn = roles.categorical[0] || roles.numeric[0] || ''
      const yColumn = roles.numeric[0] || ''
      return res.json({ ok: true, filename, rows_preview: rows.slice(0, 5), rows, columns: Object.keys(rows[0] || {}), ...roles, suggestion: roles.numeric.length && roles.categorical.length ? 'bar' : roles.numeric.length ? 'histogram' : 'bar', defaults: { xColumn, yColumn } })
    }

    if (action === 'chart' && req.method === 'POST') {
      const { filename, rows = [], chart_type = 'bar', x_col, y_col, aggregation = 'count', title = '' } = req.body || {}
      if (!x_col) return res.status(400).json({ error: 'missing_x_col' })
      const data = chartData(rows, chart_type, x_col, y_col, aggregation)
      const entry = { file_name: filename || '', x_col, y_col: y_col || '', chart_type, aggregation, title: title || `${x_col} vs ${y_col || '數量'}`, data }
      return res.json({ ok: true, ...entry })
    }

    if (action === 'save_history' && req.method === 'POST') return res.json(saveAnalysis(req.body.entry || {}))
    return res.status(400).json({ error: 'unknown_action', action })
  } catch (error) {
    return res.status(500).json({ error: 'data_error', detail: error.message })
  }
}
