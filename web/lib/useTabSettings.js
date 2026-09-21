/**
 * lib/useTabSettings.js
 *
 * 管理「每個 tab 獨立的設定記憶」與 localStorage 持久化。
 *
 * 功能：
 *  - saveTabSettings(tabId, settings)  → 寫入 localStorage
 *  - loadTabSettings(tabId)            → 從 localStorage 讀取
 *  - useTabSettings()                  → React hook，提供完整介面
 *
 * localStorage key 格式：`tab_settings_<tabId>`
 */

import { useCallback, useRef } from 'react'

const LS_PREFIX = 'tab_settings_'

/**
 * 將設定存入 localStorage。
 * 只儲存 provider / model / temperature / persona / systemPrompt，
 * 不儲存暫態 UI 狀態。
 */
export function saveTabSettings(tabId, settings) {
  if (typeof window === 'undefined') return
  try {
    const payload = {
      provider:     settings.provider,
      model:        settings.model,
      temperature:  settings.temperature,
      persona:      settings.persona,
      systemPrompt: settings.systemPrompt,
    }
    localStorage.setItem(LS_PREFIX + tabId, JSON.stringify(payload))
  } catch (e) {
    // 私密瀏覽模式或儲存空間滿時忽略
  }
}

/**
 * 從 localStorage 讀取指定 tab 的設定。
 * 回傳 null 表示尚無記錄。
 */
export function loadTabSettings(tabId) {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(LS_PREFIX + tabId)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

/**
 * React hook：提供 per-tab 設定讀寫。
 *
 * 使用方式：
 *   const { saveTab, loadTab } = useTabSettings()
 *
 *   // 離開 tab 或 settings 變動時儲存
 *   saveTab(currentTabId, settings)
 *
 *   // 進入新 tab 時讀取（若無記錄回傳 null）
 *   const saved = loadTab(newTabId)
 *   if (saved) setSettings(prev => ({ ...prev, ...saved }))
 */
export function useTabSettings() {
  // 用 ref 追蹤「目前 tab」，避免 closure 過期問題
  const currentTabRef = useRef(null)

  const saveTab = useCallback((tabId, settings) => {
    saveTabSettings(tabId, settings)
  }, [])

  const loadTab = useCallback((tabId) => {
    return loadTabSettings(tabId)
  }, [])

  const setCurrentTab = useCallback((tabId) => {
    currentTabRef.current = tabId
  }, [])

  return { saveTab, loadTab, setCurrentTab, currentTabRef }
}
