import fs from 'fs'
import path from 'path'
import Database from 'better-sqlite3'

function resolvePath(filepath) {
  const configured = filepath || 'app_memory.db'
  return path.isAbsolute(configured) ? configured : path.resolve(/* turbopackIgnore: true */ process.cwd(), '..', configured)
}

export function openSqlite(filepath) {
  const dbPath = resolvePath(filepath)
  fs.mkdirSync(path.dirname(dbPath), { recursive: true })
  const db = new Database(dbPath)
  db.pragma('journal_mode = WAL')
  return { db, dbPath }
}

export function inspectSqlite(filepath) {
  const { db, dbPath } = openSqlite(filepath)
  try {
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all()
    const details = tables.map(({ name }) => {
      const columns = db.prepare(`PRAGMA table_info("${name.replace(/"/g, '""')}")`).all()
      const rowCount = db.prepare(`SELECT COUNT(*) AS count FROM "${name.replace(/"/g, '""')}"`).get().count
      return {
        name,
        row_count: rowCount,
        columns: columns.map((column) => ({ name: column.name, type: column.type, pk: Boolean(column.pk), nullable: !column.notnull })),
        relationships: [],
      }
    })
    return { ok: true, db_type: 'sqlite', database: dbPath, version: db.prepare('SELECT sqlite_version() AS version').get().version, tables: details }
  } finally {
    db.close()
  }
}

export function previewSqlite(filepath, table, limit = 10) {
  if (!table) throw new Error('請選擇資料表。')
  const { db } = openSqlite(filepath)
  try {
    const safeTable = String(table).replace(/"/g, '""')
    const rows = db.prepare(`SELECT * FROM "${safeTable}" LIMIT ?`).all(Math.max(1, Math.min(Number(limit) || 10, 100)))
    return { ok: true, table, columns: rows.length ? Object.keys(rows[0]) : getSqliteColumns(db, safeTable), rows, row_count: rows.length }
  } finally {
    db.close()
  }
}

function getSqliteColumns(db, table) {
  return db.prepare(`PRAGMA table_info("${table}")`).all().map((column) => column.name)
}

export function executeSqlite(filepath, query) {
  if (!query || !query.trim()) throw new Error('請輸入 SQL 查詢。')
  const { db } = openSqlite(filepath)
  try {
    const statement = db.prepare(query)
    if (statement.reader) {
      const rows = statement.all()
      return { ok: true, operation: 'SELECT', columns: rows.length ? Object.keys(rows[0]) : [], rows, row_count: rows.length }
    }
    const result = statement.run()
    return { ok: true, operation: 'DML', columns: [], rows: [], row_count: result.changes }
  } finally {
    db.close()
  }
}

export function insertSqlite(filepath, table, values) {
  const keys = Object.keys(values || {})
  if (!table || !keys.length) throw new Error('請提供資料表名稱與欄位值。')
  const { db } = openSqlite(filepath)
  try {
    const quoted = keys.map((key) => `"${key.replace(/"/g, '""')}"`).join(', ')
    const placeholders = keys.map(() => '?').join(', ')
    const result = db.prepare(`INSERT INTO "${table.replace(/"/g, '""')}" (${quoted}) VALUES (${placeholders})`).run(keys.map((key) => values[key]))
    return { ok: true, row_count: result.changes }
  } finally { db.close() }
}

export function updateSqlite(filepath, table, values, whereClause = '', whereValues = []) {
  const keys = Object.keys(values || {})
  if (!table || !keys.length) throw new Error('請提供資料表名稱與更新欄位。')
  const { db } = openSqlite(filepath)
  try {
    const assignments = keys.map((key) => `"${key.replace(/"/g, '""')}" = ?`).join(', ')
    const query = `UPDATE "${table.replace(/"/g, '""')}" SET ${assignments}${whereClause ? ` WHERE ${whereClause}` : ''}`
    const result = db.prepare(query).run([...keys.map((key) => values[key]), ...whereValues])
    return { ok: true, row_count: result.changes }
  } finally { db.close() }
}

export function deleteSqlite(filepath, table, whereClause = '', whereValues = []) {
  if (!table) throw new Error('請提供資料表名稱。')
  const { db } = openSqlite(filepath)
  try {
    const query = `DELETE FROM "${table.replace(/"/g, '""')}"${whereClause ? ` WHERE ${whereClause}` : ''}`
    const result = db.prepare(query).run(whereValues)
    return { ok: true, row_count: result.changes }
  } finally { db.close() }
}
