/**
 * lib/activityLog.js
 * 活動歷程讀寫工具 —— 記錄每次 LLM 呼叫與功能操作，存於 localStorage。
 * 最多保留 500 筆，超過自動丟棄最舊的。
 */

const LS_KEY = 'activity_log'
const MAX_ENTRIES = 500

/**
 * 記錄一筆活動。
 * @param {{
 *   feature: string,   // 功能名稱，例如 'chat'、'db_analysis'、'doc_upload'
 *   action:  string,   // 動作描述，例如 '送出訊息'、'分析資料庫'
 *   model:   string,   // 使用的模型
 *   provider:string,   // provider
 *   thinkMs: number,   // 耗時 ms
 *   note:    string,   // 附加說明（可空）
 * }} entry
 */
export function recordActivity(entry) {
  if (typeof window === 'undefined') return
  try {
    const list = getActivities()
    list.unshift({
      ...entry,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    })
    if (list.length > MAX_ENTRIES) list.length = MAX_ENTRIES
    localStorage.setItem(LS_KEY, JSON.stringify(list))
  } catch (_) {}
}

/** 取得所有活動記錄（最新在前）。 */
export function getActivities() {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '[]')
  } catch (_) {
    return []
  }
}

/** 清除所有活動記錄。 */
export function clearActivities() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(LS_KEY)
}

/**
 * 根據近期記錄生成 git commit 摘要字串。
 * @param {number} limit 取最近幾筆，預設 20
 * @returns {string}
 */
export function generateCommitSummary(limit = 20) {
  const list = getActivities().slice(0, limit)
  if (list.length === 0) return '(尚無活動記錄)'

  // 以 feature 分組計數
  const groups = {}
  for (const item of list) {
    groups[item.feature] = (groups[item.feature] || 0) + 1
  }

  const lines = Object.entries(groups)
    .map(([f, c]) => `- ${f}: ${c} 次`)
    .join('\n')

  const latest = list[0]
  const date = latest.timestamp.slice(0, 10)

  return `feat: AI 功能操作紀錄 (${date})\n\n${lines}\n\n最近操作：${latest.feature} / ${latest.action}`
}
