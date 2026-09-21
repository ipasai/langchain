function configValue(config, key, fallback = '') {
  return config?.[key] || fallback
}

async function openSql(config) {
  const type = config.type === 'mariadb' ? 'mysql' : config.type
  if (type === 'mysql') {
    const mysql = require('mysql2/promise')
    return { type, connection: await mysql.createConnection({ host: configValue(config, 'host', 'localhost'), port: Number(configValue(config, 'port', 3306)), user: configValue(config, 'user', 'root'), password: configValue(config, 'password'), database: configValue(config, 'database'), charset: configValue(config, 'charset', 'utf8mb4') }) }
  }
  if (type === 'postgres') {
    const { Client } = require('pg')
    const connection = new Client({ host: configValue(config, 'host', 'localhost'), port: Number(configValue(config, 'port', 5432)), user: configValue(config, 'user', 'postgres'), password: configValue(config, 'password'), database: configValue(config, 'database', 'postgres') })
    await connection.connect()
    return { type, connection }
  }
  throw new Error(`不支援的 SQL 類型：${config.type}`)
}

async function closeSql(client) {
  if (client?.type === 'postgres') await client.connection.end()
  else if (client?.connection) await client.connection.end()
}

export async function testExternal(config) {
  if (config.type === 'redis') {
    const Redis = require('ioredis')
    const client = new Redis({ host: configValue(config, 'host', 'localhost'), port: Number(configValue(config, 'port', 6379)), password: configValue(config, 'password') || undefined, db: Number(configValue(config, 'db', 0)), lazyConnect: true })
    await client.connect(); const info = await client.info('server'); await client.quit()
    return { ok: true, db_type: 'redis', version: info.match(/redis_version:([^\r\n]+)/)?.[1] || '', tables: [] }
  }
  if (config.type === 'mongodb') {
    const { MongoClient } = require('mongodb')
    const client = new MongoClient(configValue(config, 'uri'))
    await client.connect(); const db = client.db(configValue(config, 'database')); const collections = await db.listCollections().toArray(); await client.close()
    return { ok: true, db_type: 'mongodb', database: config.database, collections: collections.map((item) => ({ name: item.name })) }
  }
  const client = await openSql(config)
  try {
    const tables = client.type === 'postgres'
      ? (await client.connection.query("SELECT table_name AS name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")).rows
      : (await client.connection.query('SHOW TABLES'))[0].map((row) => ({ name: Object.values(row)[0] }))
    const details = []
    for (const table of tables) {
      const name = table.name
      const columns = client.type === 'postgres'
        ? (await client.connection.query('SELECT column_name AS name, data_type AS type FROM information_schema.columns WHERE table_schema=$1 AND table_name=$2 ORDER BY ordinal_position', ['public', name])).rows
        : (await client.connection.query(`SHOW COLUMNS FROM \`${name.replace(/`/g, '``')}\``))[0].map((row) => ({ name: row.Field, type: row.Type }))
      const countResult = await client.connection.query(`SELECT COUNT(*) AS count FROM ${quoteIdentifier(name, client.type)}`)
      details.push({ name, columns, row_count: Number(countResult.rows?.[0]?.count ?? countResult[0]?.[0]?.count ?? 0), relationships: [] })
    }
    return { ok: true, db_type: client.type, tables: details }
  } finally { await closeSql(client) }
}

function quoteIdentifier(name, type) { return type === 'postgres' ? `"${String(name).replace(/"/g, '""')}"` : `\`${String(name).replace(/`/g, '``')}\`` }

export async function executeExternal(config, query) {
  const client = await openSql(config)
  try {
    const result = client.type === 'postgres' ? await client.connection.query(query) : await client.connection.query(query)
    const rows = result.rows || result[0] || []
    return { ok: true, operation: rows.length || result.fields ? 'SELECT' : 'DML', columns: result.fields ? result.fields.map((field) => field.name) : rows.length ? Object.keys(rows[0]) : [], rows, row_count: rows.length || result[0]?.affectedRows || result.rowCount || 0 }
  } finally { await closeSql(client) }
}

export async function previewExternal(config, table, limit = 10) {
  return executeExternal(config, `SELECT * FROM ${quoteIdentifier(table, config.type === 'postgres' ? 'postgres' : 'mysql')} LIMIT ${Math.max(1, Math.min(Number(limit) || 10, 100))}`)
}
