import { useState } from 'react'

const tabs = [
  { id: 'chat', label: '💬 AI 對話' },
  { id: 'database', label: '🗄️ 資料庫管理' },
  { id: 'english', label: '📘 英文學習' },
  { id: 'documents', label: '📄 智慧文件分析' },
  { id: 'tts', label: '🎧 Markdown 轉 MP3' },
  { id: 'data', label: '📊 資料分析' },
]

export default function AppTabs({ panels, onTabChange }) {
  const [activeTab, setActiveTab] = useState('chat')

  function handleTabClick(tabId) {
    setActiveTab(tabId)
    onTabChange?.(tabId)
  }

  return (
    <div>
      <div className="overflow-x-auto border-b border-indigo-100">
        <div className="flex min-w-max gap-1 items-center" role="tablist" aria-label="應用功能">
          {tabs.map((tab) => {
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => handleTabClick(tab.id)}
                className={`border-b-2 px-4 py-3 text-sm font-semibold transition ${active
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:border-indigo-200 hover:text-indigo-600'}`}
              >
                {tab.label}
              </button>
            )
          })}
          {/* 活動歷程：開新頁，不佔 panel 空間 */}
          <a
            href="/activity"
            target="_blank"
            rel="noopener noreferrer"
            className="ml-2 border-b-2 border-transparent px-3 py-3 text-sm font-semibold text-slate-400 hover:text-indigo-600 hover:border-indigo-200 transition"
            title="查看 AI 活動歷程與 git commit 產生器"
          >
            📋 歷程
          </a>
        </div>
      </div>
      <div className="pt-6" role="tabpanel">
        {panels[activeTab]}
      </div>
    </div>
  )
}
