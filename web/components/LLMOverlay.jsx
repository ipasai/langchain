/**
 * components/LLMOverlay.jsx
 *
 * 全畫面半透明遮罩，在 LLM 處理期間顯示。
 * 阻擋所有使用者互動，避免重複觸發。
 *
 * Props:
 *   show       boolean  是否顯示遮罩
 *   model      string   模型名稱
 *   provider   string   provider
 *   elapsed    number   已等待秒數
 *   label?     string   自訂標題（預設「AI 正在處理中…」）
 */
export default function LLMOverlay({ show, model, provider, elapsed, label }) {
  if (!show) return null

  const title = label || 'AI 正在處理中…'
  const modelLabel = (model || '').split(' (')[0]

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/40 backdrop-blur-sm"
      aria-live="polite"
      aria-label={title}
    >
      {/* Spinner */}
      <svg
        className="animate-spin h-12 w-12 text-white mb-4"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>

      <span className="text-white text-lg font-semibold">{title}</span>

      {/* 模型 + 計時資訊 */}
      <div className="mt-3 flex items-center gap-2">
        {provider && (
          <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-medium text-white">
            {provider}
          </span>
        )}
        {modelLabel && (
          <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-mono text-white">
            {modelLabel}
          </span>
        )}
        {elapsed > 0 && (
          <span className="text-white/70 text-sm tabular-nums">
            ⏱ {elapsed} 秒
          </span>
        )}
      </div>
    </div>
  )
}
