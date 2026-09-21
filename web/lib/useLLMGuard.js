/**
 * lib/useLLMGuard.js
 *
 * 共用 React hook，為所有 LLM 操作提供：
 *  1. 全畫面鎖定（loading state）
 *  2. 即時計時（elapsedSec）
 *  3. 操作完成後自動寫入 activityLog
 *
 * 使用方式：
 *   const { loading, elapsedSec, run } = useLLMGuard()
 *
 *   await run(
 *     async () => { /* 你的 LLM 呼叫邏輯 *\/ },
 *     { feature: 'chat', action: '送出訊息', model: 'gpt-4o-mini', provider: 'openai', note: '' }
 *   )
 */

import { useState, useRef, useCallback } from 'react'
import { recordActivity } from './activityLog'

export function useLLMGuard() {
  const [loading, setLoading] = useState(false)
  const [elapsedSec, setElapsedSec] = useState(0)
  const timerRef = useRef(null)

  /**
   * 執行 LLM 操作，自動處理 loading / 計時 / 活動記錄。
   *
   * @param {() => Promise<any>} fn      要執行的非同步函式
   * @param {{
   *   feature:  string,
   *   action:   string,
   *   model?:   string,
   *   provider?:string,
   *   note?:    string,
   * }} meta  活動記錄 metadata
   * @returns {Promise<any>}  fn 的回傳值
   */
  const run = useCallback(async (fn, meta = {}) => {
    setLoading(true)
    setElapsedSec(0)
    const start = Date.now()

    clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - start) / 1000))
    }, 1000)

    let result
    try {
      result = await fn()
    } finally {
      clearInterval(timerRef.current)
      const thinkMs = Date.now() - start
      setLoading(false)

      // 自動記錄活動歷程
      recordActivity({
        feature:  meta.feature  || 'unknown',
        action:   meta.action   || 'LLM 呼叫',
        model:    meta.model    || '',
        provider: meta.provider || '',
        thinkMs,
        note:     meta.note     || '',
      })
    }
    return result
  }, [])

  return { loading, elapsedSec, run }
}
