import { useEffect, useRef, useState } from 'react'
import { PERSONAS } from '../lib/personas'
import { detectDeviceProfile, getTabRecommendation } from '../lib/deviceProfile'

const providers = [
  { value: 'ollama', label: 'Ollama（本地）' },
  { value: 'openai', label: 'OpenAI（雲端）' },
  { value: 'google', label: 'Google Gemini（雲端）' },
]

// 角色清單從共用模組取得，所有功能使用同一份資料
const personas = PERSONAS

/** tier → 視覺樣式 */
const TIER_STYLE = {
  high: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', badge: 'bg-emerald-100 text-emerald-700' },
  mid:  { bg: 'bg-amber-50',   border: 'border-amber-200',   text: 'text-amber-800',   badge: 'bg-amber-100 text-amber-700' },
  low:  { bg: 'bg-sky-50',     border: 'border-sky-200',     text: 'text-sky-800',     badge: 'bg-sky-100 text-sky-700' },
}

export default function SettingsSidebar({ settings, onChange, onClearHistory, activeTab }) {
  const [models, setModels] = useState([])
  const [recommendation, setRecommendation] = useState('')
  const [deviceProfile, setDeviceProfile] = useState(null)
  const [tabRec, setTabRec] = useState(null)

  // 記住「等清單載入後要自動選的 model」
  const pendingModelRef = useRef(null)

  // 偵測裝置等級（只在客戶端執行一次）
  useEffect(() => {
    const profile = detectDeviceProfile()
    setDeviceProfile(profile)
  }, [])

  // 當 tab 切換時，計算該 tab 的推薦 provider/model
  useEffect(() => {
    if (!deviceProfile || !activeTab) return
    setTabRec(getTabRecommendation(deviceProfile, activeTab))
  }, [deviceProfile, activeTab])

  // provider 變動時重新拉取模型清單
  useEffect(() => {
    let cancelled = false
    fetch(`/api/llm?action=get_models&provider=${encodeURIComponent(settings.provider)}`)
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return
        const nextModels = data.models || []
        setModels(nextModels)

        if (nextModels.length === 0) return

        // 若有待套用的推薦 model，找最接近的選項
        const pending = pendingModelRef.current
        if (pending) {
          pendingModelRef.current = null
          // 完全比對 → 前綴比對 → fallback 第一項
          const exact = nextModels.find((m) => m === pending)
          const prefix = nextModels.find((m) => m.startsWith(pending.split(':')[0]))
          const selected = exact ?? prefix ?? nextModels[0]
          onChange({ ...settings, model: selected })
        } else if (!settings.model || !nextModels.includes(settings.model)) {
          // provider 切換後舊 model 不在新清單，自動選第一項
          onChange({ ...settings, model: nextModels[0] })
        }
      })
      .catch(() => !cancelled && setModels([]))
    return () => { cancelled = true }
  // settings.provider 變動才重跑；故意排除 settings / onChange 避免無限迴圈
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.provider])

  useEffect(() => {
    if (!settings.model) return
    fetch(`/api/llm?action=get_recommendation&model=${encodeURIComponent(settings.model)}`)
      .then((res) => res.json())
      .then((data) => setRecommendation(data.recommendation || ''))
      .catch(() => setRecommendation(''))
  }, [settings.model])

  function update(key, value) {
    onChange({ ...settings, [key]: value })
  }

  /** 一鍵套用裝置推薦的 provider + model */
  function applyDeviceRecommendation() {
    if (!tabRec) return

    if (tabRec.provider !== settings.provider) {
      // provider 要換：先把目標 model 記到 pending，等清單載入後再套用
      pendingModelRef.current = tabRec.model
      onChange({ ...settings, provider: tabRec.provider, model: '' })
    } else {
      // 同 provider：清單已在，直接找最接近的選項套用
      const exact = models.find((m) => m === tabRec.model)
      const prefix = models.find((m) => m.startsWith(tabRec.model.split(':')[0]))
      const selected = exact ?? prefix ?? models[0] ?? tabRec.model
      onChange({ ...settings, model: selected })
    }
  }

  const tierStyle = deviceProfile ? TIER_STYLE[deviceProfile.tier] : null

  return (
    <aside className="rounded-2xl border border-indigo-100 bg-white p-4 shadow-sm lg:sticky lg:top-6 space-y-4">
      <h2 className="text-lg font-bold text-indigo-700">⚙️ 應用設定</h2>

      {/* 裝置推薦提示區 */}
      {deviceProfile && tabRec && tierStyle && (
        <div className={`rounded-xl border p-3 text-xs ${tierStyle.bg} ${tierStyle.border}`}>
          <div className="flex items-center justify-between mb-1">
            <span className={`font-semibold text-sm ${tierStyle.text}`}>
              🖥️ 裝置偵測
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tierStyle.badge}`}>
              {deviceProfile.label}
            </span>
          </div>
          <p className={`leading-5 mb-2 ${tierStyle.text}`}>{deviceProfile.description}</p>
          <div className={`mb-2 font-medium ${tierStyle.text}`}>
            推薦：<code className="bg-white/60 px-1 rounded">{tabRec.provider}</code>
            {tabRec.model && <> · <code className="bg-white/60 px-1 rounded">{tabRec.model}</code></>}
          </div>
          {/* 僅當目前設定與推薦不同時才顯示套用按鈕 */}
          {(settings.provider !== tabRec.provider || settings.model !== tabRec.model) && (
            <button
              type="button"
              onClick={applyDeviceRecommendation}
              className={`w-full rounded-lg border py-1.5 text-xs font-semibold transition
                ${tierStyle.border} ${tierStyle.text} bg-white/70 hover:bg-white`}
            >
              ⚡ 套用推薦設定
            </button>
          )}
          {settings.provider === tabRec.provider && settings.model === tabRec.model && (
            <p className={`text-center text-xs font-medium ${tierStyle.text}`}>✓ 已使用推薦設定</p>
          )}
        </div>
      )}

      {/* Provider 選單 */}
      <label className="block text-sm font-medium text-slate-700">
        AI 模型提供者
        <select
          className="mt-1 w-full rounded-lg border p-2"
          value={settings.provider}
          onChange={(e) => update('provider', e.target.value)}
        >
          {providers.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </label>

      {/* Model 選單 */}
      <label className="block text-sm font-medium text-slate-700">
        選擇 AI 模型
        <select
          className="mt-1 w-full rounded-lg border p-2"
          value={settings.model}
          onChange={(e) => update('model', e.target.value)}
        >
          {models.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>

      {/* 溫度 */}
      <label className="block text-sm font-medium text-slate-700">
        溫度：{settings.temperature.toFixed(1)}
        <input
          className="mt-2 w-full"
          type="range" min="0" max="1" step="0.1"
          value={settings.temperature}
          onChange={(e) => update('temperature', Number(e.target.value))}
        />
      </label>

      {/* 角色設定 */}
      <label className="block text-sm font-medium text-slate-700">
        👤 角色設定
        <select
          className="mt-1 w-full rounded-lg border p-2"
          value={settings.persona}
          onChange={(e) => update('persona', e.target.value)}
        >
          {Object.keys(personas).map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </label>

      {settings.persona === '✏️ 自訂角色' ? (
        <textarea
          className="min-h-24 w-full rounded-lg border p-2 text-sm"
          value={settings.systemPrompt}
          onChange={(e) => update('systemPrompt', e.target.value)}
        />
      ) : (
        <p className="text-xs leading-5 text-slate-500">{personas[settings.persona]}</p>
      )}

      {/* 目前設定摘要 */}
      <div className="rounded-lg bg-indigo-50 p-3 text-xs text-indigo-900">
        <div><strong>提供者：</strong>{settings.provider.toUpperCase()}</div>
        <div><strong>模型：</strong>{settings.model || '尚未取得模型'}</div>
        {recommendation && <div className="mt-1"><strong>建議用途：</strong>{recommendation}</div>}
      </div>

      <button
        type="button"
        className="w-full rounded-lg bg-red-500 px-3 py-2 text-sm font-semibold text-white hover:bg-red-600"
        onClick={onClearHistory}
      >
        🗑️ 清除對話歷史
      </button>
    </aside>
  )
}
