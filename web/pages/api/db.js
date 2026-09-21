import fs from 'fs'
import path from 'path'
import Database from 'better-sqlite3'
import { inspectSqlite, previewSqlite, executeSqlite, insertSqlite, updateSqlite, deleteSqlite } from '../../lib/dbHandlers'
import { testExternal, previewExternal, executeExternal } from '../../lib/externalDbHandlers'
import url from 'url'

function getDbPath() {
  const env = process.env.DB_PATH
  if (env) return env
  // assume repo root is parent of web/
  return path.resolve(process.cwd(), '..', 'data', 'app_memory.db')
}

function ensureDb(dbPath) {
  const dir = path.dirname(dbPath)
  fs.mkdirSync(dir, { recursive: true })
  const db = new Database(dbPath)
  db.pragma('journal_mode = WAL')

  db.prepare(
    `CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)`
  ).run()
  db.prepare(
    `CREATE TABLE IF NOT EXISTS chat_sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      created_at TEXT NOT NULL
    )`
  ).run()
  db.prepare(
    `CREATE TABLE IF NOT EXISTS chat_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id INTEGER,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )`
  ).run()
  // 若舊資料庫無 session_id 欄位，自動補上（migration）
  const cols = db.prepare(`PRAGMA table_info(chat_messages)`).all()
  if (!cols.find(c => c.name === 'session_id')) {
    db.prepare(`ALTER TABLE chat_messages ADD COLUMN session_id INTEGER`).run()
  }
  if (!cols.find(c => c.name === 'meta')) {
    db.prepare(`ALTER TABLE chat_messages ADD COLUMN meta TEXT`).run()
  }
  db.prepare(
    `CREATE TABLE IF NOT EXISTS english_practice (id INTEGER PRIMARY KEY AUTOINCREMENT, english TEXT NOT NULL, translation TEXT NOT NULL, example TEXT, category TEXT, phonetic TEXT, created_at TEXT NOT NULL)`
  ).run()
  db.prepare(
    `CREATE TABLE IF NOT EXISTS study_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, test_type TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, accuracy REAL NOT NULL, created_at TEXT NOT NULL)`
  ).run()

  return db
}

export default async function handler(req, res) {
  const dbPath = getDbPath()
  const parsedQuery = req.query || url.parse(req.url || '', true).query || {}
  const action = (req.method === 'GET' ? parsedQuery.action : (req.body && req.body.action)) || parsedQuery.action || ''
  let db
  try {
    if (action === 'external_test' && req.method === 'POST') return res.json(await testExternal(req.body?.config || {}))
    if (action === 'external_preview' && req.method === 'POST') return res.json(await previewExternal(req.body?.config || {}, req.body.table, req.body.limit))
    if (action === 'external_sql' && req.method === 'POST') return res.json(await executeExternal(req.body?.config || {}, req.body.query))
    if (action === 'inspect' && req.method === 'POST') {
      const { filepath = 'data/app_memory.db' } = req.body || {}
      return res.json(inspectSqlite(filepath))
    }

    if (action === 'preview' && req.method === 'POST') {
      const { filepath = 'data/app_memory.db', table, limit = 10 } = req.body || {}
      return res.json(previewSqlite(filepath, table, limit))
    }

    if (action === 'execute_sql' && req.method === 'POST') {
      const { filepath = 'data/app_memory.db', query } = req.body || {}
      return res.json(executeSqlite(filepath, query))
    }

    if (action === 'insert_row' && req.method === 'POST') {
      const { filepath = 'data/app_memory.db', table, values } = req.body || {}
      return res.json(insertSqlite(filepath, table, values))
    }

    if (action === 'update_row' && req.method === 'POST') {
      const { filepath = 'data/app_memory.db', table, values, where_clause = '', where_values = [] } = req.body || {}
      return res.json(updateSqlite(filepath, table, values, where_clause, where_values))
    }

    if (action === 'delete_row' && req.method === 'POST') {
      const { filepath = 'data/app_memory.db', table, where_clause = '', where_values = [] } = req.body || {}
      return res.json(deleteSqlite(filepath, table, where_clause, where_values))
    }

    db = ensureDb(dbPath)
  } catch (err) {
    return res.status(500).json({ error: 'db_init_failed', detail: err.message })
  }

  try {
    if (action === 'test') {
      return res.json({ ok: true, dbPath })
    }

    if (action === 'add_word' && req.method === 'POST') {
      const { word, definition, example = '', category = '未分類', phonetic = '' } = req.body || {}
      const stmt = db.prepare('INSERT INTO english_practice (english, translation, example, category, phonetic, created_at) VALUES (?, ?, ?, ?, ?, ?)')
      stmt.run((word || '').toLowerCase().trim(), (definition || '').trim(), (example || '').trim(), category, phonetic, new Date().toISOString())
      return res.json({ ok: true })
    }

    if (action === 'delete_word' && req.method === 'POST') {
      const { english } = req.body || {}
      if (!english) return res.status(400).json({ error: 'missing_param', message: 'english is required' })
      const cursor = db.prepare('DELETE FROM english_practice WHERE lower(english) = ?').run(english.toLowerCase().trim())
      return res.json({ ok: true, deleted: cursor.changes })
    }

    if (action === 'list_words') {
      const limit = parseInt(parsedQuery.limit || '10')
      const rows = db.prepare('SELECT english, translation, example, category, created_at, phonetic FROM english_practice ORDER BY id DESC LIMIT ?').all(limit)
      return res.json(rows)
    }

    if (action === 'search_words') {
      const q = (parsedQuery.q || '').toLowerCase()
      const term = `%${q}%`
      const rows = db.prepare('SELECT english, translation, example, created_at, phonetic FROM english_practice WHERE lower(english) LIKE ? OR lower(translation) LIKE ? ORDER BY id DESC LIMIT 10').all(term, term)
      return res.json(rows)
    }

    // ── Session API ──────────────────────────────────────────
    if (action === 'create_session' && req.method === 'POST') {
      const { name = '新對話' } = req.body || {}
      const stmt = db.prepare('INSERT INTO chat_sessions (name, created_at) VALUES (?, ?)')
      const result = stmt.run(name.trim() || '新對話', new Date().toISOString())
      return res.json({ ok: true, id: result.lastInsertRowid, name })
    }

    if (action === 'list_sessions') {
      const rows = db.prepare(`
        SELECT s.id, s.name, s.created_at,
          COUNT(m.id) as message_count,
          MAX(m.created_at) as last_message_at
        FROM chat_sessions s
        LEFT JOIN chat_messages m ON m.session_id = s.id
        GROUP BY s.id
        ORDER BY s.id DESC
      `).all()
      return res.json(rows)
    }

    if (action === 'rename_session' && req.method === 'POST') {
      const { id, name } = req.body || {}
      if (!id || !name) return res.status(400).json({ error: 'missing_param' })
      db.prepare('UPDATE chat_sessions SET name = ? WHERE id = ?').run(name.trim(), id)
      return res.json({ ok: true })
    }

    if (action === 'delete_session' && req.method === 'POST') {
      const { id } = req.body || {}
      if (!id) return res.status(400).json({ error: 'missing_param' })
      db.prepare('DELETE FROM chat_messages WHERE session_id = ?').run(id)
      db.prepare('DELETE FROM chat_sessions WHERE id = ?').run(id)
      return res.json({ ok: true })
    }

    if (action === 'list_chats_by_session') {
      const sessionId = parsedQuery.session_id
      const limit = parseInt(parsedQuery.limit || '200')
      if (!sessionId) return res.status(400).json({ error: 'missing_session_id' })
      const rows = db.prepare(
        'SELECT id, role, content, meta, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?'
      ).all(sessionId, limit)
      return res.json(rows)
    }

    if (action === 'save_chat' && req.method === 'POST') {
      const { role, content, session_id, meta } = req.body || {}
      const stmt = db.prepare('INSERT INTO chat_messages (session_id, role, content, meta, created_at) VALUES (?, ?, ?, ?, ?)')
      stmt.run(session_id || null, role || 'user', content || '', meta ? JSON.stringify(meta) : null, new Date().toISOString())
      return res.json({ ok: true })
    }

    if (action === 'list_chats') {
      const limit = parseInt(parsedQuery.limit || '50')
      const rows = db.prepare('SELECT id, role, content, created_at FROM chat_messages ORDER BY id ASC LIMIT ?').all(limit)
      return res.json(rows)
    }

    if (action === 'clear_chats') {
      db.prepare('DELETE FROM chat_messages').run()
      return res.json({ ok: true })
    }

    if (action === 'stats') {
      const totalItems = db.prepare('SELECT COUNT(*) as c FROM english_practice').get().c
      const totalSessions = db.prepare('SELECT COUNT(*) as c FROM study_sessions').get().c
      const totalScore = db.prepare('SELECT COALESCE(SUM(score),0) as s FROM study_sessions').get().s
      const totalQuestions = db.prepare('SELECT COALESCE(SUM(total),0) as t FROM study_sessions').get().t
      const accuracy = totalQuestions ? Math.round((totalScore / totalQuestions) * 100) / 100 : 0.0
      return res.json({ total_items: totalItems, total_sessions: totalSessions, total_score: totalScore, total_questions: totalQuestions, accuracy })
    }

    if (action === 'save_study_session' && req.method === 'POST') {
      const { test_type = 'english', score = 0, total = 0 } = req.body || {}
      const accuracy = total ? Number(score) / Number(total) : 0
      db.prepare('INSERT INTO study_sessions (test_type, score, total, accuracy, created_at) VALUES (?, ?, ?, ?, ?)').run(test_type, Number(score), Number(total), accuracy, new Date().toISOString())
      return res.json({ ok: true, score: Number(score), total: Number(total), accuracy })
    }

    return res.status(400).json({ error: 'unknown_action', action })
  } catch (err) {
    return res.status(500).json({ error: 'db_error', detail: err.message })
  } finally {
    try { db.close() } catch (e) {}
  }
}
