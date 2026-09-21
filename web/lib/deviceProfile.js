/**
 * lib/deviceProfile.js
 *
 * 在瀏覽器端偵測裝置效能等級，並回傳對應的推薦 provider / model。
 *
 * 偵測依據（皆為非精確估算，僅供參考）：
 *   - navigator.hardwareConcurrency  CPU 邏輯核心數
 *   - navigator.deviceMemory         裝置記憶體 GB（Chrome/Edge 限定）
 *   - navigator.connection.effectiveType  網路類型（4g/3g/2g/slow-2g）
 *
 * 等級定義：
 *   high   ≥ 8 核心 或 ≥ 8 GB RAM  → 可跑本地大模型 (ollama)
 *   mid    4–7 核心 或 4–7 GB RAM  → 本地輕量模型 / 雲端皆可
 *   low    < 4 核心 或 < 4 GB RAM  → 優先使用雲端 API
 */

/** 三個等級的推薦設定 */
const PROFILES = {
  high: {
    tier: 'high',
    label: '高效能裝置',
    description: '偵測到多核心 / 大記憶體，建議使用本地 Ollama 模型，速度快且隱私性佳。',
    provider: 'ollama',
    model: 'llama3',          // 預設高效能本地模型；實際清單由 API 決定
    fallbackModel: 'mistral',
  },
  mid: {
    tier: 'mid',
    label: '中階裝置',
    description: '偵測到中階硬體，建議使用本地輕量模型或 OpenAI 雲端服務。',
    provider: 'ollama',
    model: 'phi3',
    fallbackModel: 'tinyllama',
  },
  low: {
    tier: 'low',
    label: '低效能 / 行動裝置',
    description: '偵測到低效能硬體或行動網路，建議使用 OpenAI / Google 雲端服務，減少本地負擔。',
    provider: 'openai',
    model: 'gpt-4o-mini',
    fallbackModel: 'gpt-3.5-turbo',
  },
}

/**
 * 偵測裝置效能並回傳推薦 profile。
 * 只能在瀏覽器端呼叫（SSR 時回傳 null）。
 *
 * @returns {{ tier: string, label: string, description: string, provider: string, model: string } | null}
 */
export function detectDeviceProfile() {
  if (typeof navigator === 'undefined') return null   // SSR guard

  const cores  = navigator.hardwareConcurrency || 2
  const memory = navigator.deviceMemory || 0           // 0 = 未知（Safari/Firefox 不支援）
  const connType = navigator.connection?.effectiveType ?? '4g'

  // 行動網路強制推薦雲端
  if (connType === 'slow-2g' || connType === '2g' || connType === '3g') {
    return PROFILES.low
  }

  // 以 cores 為主要判斷依據，memory 為輔
  if (cores >= 8 || memory >= 8) return PROFILES.high
  if (cores >= 4 || memory >= 4) return PROFILES.mid
  return PROFILES.low
}

/**
 * 根據 tab 功能，調整推薦的 model（部分功能對 model 有特定偏好）。
 *
 * @param {ReturnType<typeof detectDeviceProfile>} profile
 * @param {string} tabId
 * @returns {{ provider: string, model: string }}
 */
export function getTabRecommendation(profile, tabId) {
  if (!profile) return { provider: 'openai', model: 'gpt-4o-mini' }

  // 資料庫 / 文件分析需要較強推理能力，低階裝置也升級一點
  const needsStronger = tabId === 'database' || tabId === 'documents' || tabId === 'data'

  if (needsStronger && profile.tier === 'low') {
    return { provider: 'openai', model: 'gpt-4o-mini' }
  }
  if (needsStronger && profile.tier === 'mid') {
    return { provider: profile.provider, model: profile.model }
  }

  return { provider: profile.provider, model: profile.model }
}
