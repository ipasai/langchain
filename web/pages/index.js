import { useState, useEffect } from 'react'
import Chat from '../components/Chat'
import DBManager from '../components/DBManager'
import EnglishLearning from '../components/EnglishLearning'
import DocAnalyzer from '../components/DocAnalyzer'
import DataAnalysis from '../components/DataAnalysis'
import AppTabs from '../components/AppTabs'
import SettingsSidebar from '../components/SettingsSidebar'
import { DEFAULT_SETTINGS, TAB_DEFAULT_PERSONA, PERSONAS } from '../lib/personas'
import { useTabSettings } from '../lib/useTabSettings'
import { detectDeviceProfile, getTabRecommendation } from '../lib/deviceProfile'

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('chat')
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const { saveTab, loadTab } = useTabSettings()

  /**
   * 初始化：偵測裝置等級，若 localStorage 無記錄則套用裝置推薦
   */
  useEffect(() => {
    const saved = loadTab('chat')
    if (saved) {
      setSettings((prev) => ({ ...prev, ...saved }))
    } else {
      // 第一次訪問：依裝置等級設定預設 provider/model
      const profile = detectDeviceProfile()
      if (profile) {
        const rec = getTabRecommendation(profile, 'chat')
        setSettings((prev) => ({ ...prev, provider: rec.provider, model: rec.model }))
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /**
   * settings 變動時，自動儲存當前 tab 的設定到 localStorage
   */
  useEffect(() => {
    saveTab(activeTab, settings)
  }, [settings, activeTab, saveTab])

  /**
   * 切換 tab 時：
   * 1. 儲存離開的 tab 設定
   * 2. 還原新 tab 的上次設定（若有），否則套用角色預設 + 裝置推薦
   */
  function handleTabChange(newTabId) {
    // 儲存目前 tab
    saveTab(activeTab, settings)

    // 讀取新 tab 的儲存設定
    const saved = loadTab(newTabId)

    if (saved) {
      // 有記錄：直接還原
      setSettings((prev) => ({ ...prev, ...saved }))
    } else {
      // 無記錄：套用角色預設 + 裝置推薦 provider/model
      const persona = TAB_DEFAULT_PERSONA[newTabId]
      const profile = detectDeviceProfile()
      const rec = profile ? getTabRecommendation(profile, newTabId) : null

      setSettings((prev) => {
        const next = { ...prev }

        // 角色
        if (persona) {
          const systemPrompt = PERSONAS[persona]
          next.persona = persona
          if (systemPrompt !== 'custom') next.systemPrompt = systemPrompt
        }

        // provider / model
        if (rec) {
          next.provider = rec.provider
          next.model = rec.model
        }

        return next
      })
    }

    setActiveTab(newTabId)
  }

  async function clearHistory() {
    await fetch('/api/db', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'clear_chats' }),
    })
    window.dispatchEvent(new Event('chat-history-cleared'))
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-6">
      <header className="mx-auto mb-6 max-w-7xl">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">🤖 LangChain 多模型應用</h1>
            <p className="mt-1 text-slate-600">功能依照 Streamlit 版本分頁呈現，設定集中於側邊欄。</p>
          </div>
          <button
            type="button"
            aria-controls="settings-sidebar"
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen((open) => !open)}
            className="rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm font-semibold text-indigo-700 shadow-sm hover:bg-indigo-50"
          >
            {sidebarOpen ? '隱藏左側設定' : '顯示左側設定'}
          </button>
        </div>
      </header>

      <main className={`mx-auto grid max-w-7xl gap-6 ${sidebarOpen ? 'lg:grid-cols-[260px_minmax(0,1fr)]' : 'grid-cols-1'}`}>
        {sidebarOpen && (
          <div id="settings-sidebar">
            <SettingsSidebar
              settings={settings}
              onChange={setSettings}
              onClearHistory={clearHistory}
              activeTab={activeTab}
            />
          </div>
        )}
        <section className="min-w-0 rounded-2xl border border-indigo-100 bg-white p-4 shadow-sm md:p-6">
          <AppTabs onTabChange={handleTabChange} panels={{
            chat:      <Chat settings={settings} />,
            database:  <DBManager />,
            english:   <EnglishLearning />,
            documents: <DocAnalyzer />,
            data:      <DataAnalysis />,
          }} />
        </section>
      </main>
    </div>
  )
}
