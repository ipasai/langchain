import { useMemo, useRef, useState } from 'react'

const MAX_LENGTH = 12000
const voices = [
  ['alloy', 'Alloy'], ['ash', 'Ash'], ['ballad', 'Ballad'], ['coral', 'Coral'], ['echo', 'Echo'],
  ['fable', 'Fable'], ['onyx', 'Onyx'], ['nova', 'Nova'], ['sage', 'Sage'], ['shimmer', 'Shimmer'],
]
const taiwanVoices = [
  ['zh-TW-HsiaoChenNeural', '曉臻（女聲）'],
  ['zh-TW-HsiaoYuNeural', '曉雨（女聲）'],
  ['zh-TW-YunJheNeural', '雲哲（男聲）'],
]
const mainlandVoices = [
  ['zh-CN-XiaoxiaoNeural', '曉曉（女聲）'],
  ['zh-CN-XiaoyiNeural', '曉伊（女聲）'],
  ['zh-CN-YunxiNeural', '雲希（男聲）'],
  ['zh-CN-YunyangNeural', '雲揚（男聲）'],
]

export default function MarkdownToSpeech({ settings = {} }) {
  const [text, setText] = useState('')
  const [filename, setFilename] = useState('learning-audio')
  const [provider, setProvider] = useState('edge')
  const [voice, setVoice] = useState('zh-TW-HsiaoChenNeural')
  const [chineseVariant, setChineseVariant] = useState('zh-TW')
  const [learningProvider, setLearningProvider] = useState(settings.provider || 'ollama')
  const [learningModel, setLearningModel] = useState(settings.model || '')
  const [mode, setMode] = useState('understanding')
  const [level, setLevel] = useState('beginner')
  const [chapterReview, setChapterReview] = useState(true)
  const [workflow, setWorkflow] = useState(null)
  const [working, setWorking] = useState(false)
  const [status, setStatus] = useState('')
  const [playingId, setPlayingId] = useState(null)
  const [currentSectionId, setCurrentSectionId] = useState(null)
  const audioRef = useRef(null)
  const audioUrls = useRef(new Map())

  const allBlocks = useMemo(() => workflow?.sections?.flatMap((section) => section.teaching_blocks.map((block) => ({ ...block, section_id: section.id, section_title: section.title }))) || [], [workflow])

  function loadMarkdown(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.md') && file.type !== 'text/markdown' && file.type !== 'text/plain') {
      setStatus('請選擇 Markdown 或純文字檔案。')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      setText(String(reader.result || ''))
      setFilename(file.name.replace(/\.md$/i, '') || 'learning-audio')
      setWorkflow(null)
      setStatus('Markdown 已載入。')
    }
    reader.onerror = () => setStatus('無法讀取此檔案。')
    reader.readAsText(file)
  }

  function clearAudioUrls() {
    for (const url of audioUrls.current.values()) URL.revokeObjectURL(url)
    audioUrls.current.clear()
    setPlayingId(null)
    if (audioRef.current) audioRef.current.pause()
  }

  async function createLesson() {
    if (!text.trim()) return setStatus('請先輸入或上傳 Markdown。')
    if (text.length > MAX_LENGTH) return setStatus(`文件超過限制，最多 ${MAX_LENGTH} 字元。`)
    clearAudioUrls()
    setWorking(true)
    setStatus('正在解析章節、分析內容、撰寫初學者教學稿並檢查完整性…')
    try {
      const response = await fetch('/api/learning?action=process', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          markdown: text,
          mode,
          learnerLevel: level,
          chapterReview,
          config: { provider: learningProvider, model: learningModel || undefined },
        }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || data.error || '教學稿產生失敗')
      setWorkflow(data)
      setStatus(data.tts_ready ? '品質檢查通過，可以分段合成語音。' : '品質檢查未通過；請查看問題並修正文件或重新生成。')
    } catch (error) {
      setStatus(error.message || '教學稿產生失敗。')
    } finally { setWorking(false) }
  }

  async function getAudio(block) {
    if (audioUrls.current.has(block.block_id)) return audioUrls.current.get(block.block_id)
    const response = await fetch('/api/learning?action=audio', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: block.spoken_text, voice, provider, instructions: 'Use natural Taiwanese Mandarin. Read clearly at a comfortable teaching pace.' }),
    })
    if (!response.ok) {
      let message = '語音合成失敗。'
      try { message = (await response.json()).message || message } catch (error) {}
      throw new Error(message)
    }
    const url = URL.createObjectURL(await response.blob())
    audioUrls.current.set(block.block_id, url)
    return url
  }

  async function playBlock(block) {
    try {
      setWorking(true)
      setStatus(`正在合成：「${block.section_title}」…`)
      const url = await getAudio(block)
      if (!audioRef.current) audioRef.current = new Audio()
      audioRef.current.pause()
      audioRef.current.src = url
      audioRef.current.onended = () => setPlayingId(null)
      await audioRef.current.play()
      setPlayingId(block.block_id)
      setCurrentSectionId(block.section_id)
      setStatus(`播放中：${block.section_title}`)
    } catch (error) { setStatus(error.message || '播放失敗。') }
    finally { setWorking(false) }
  }

  async function playSection(section) {
    if (!workflow?.tts_ready) return
    setCurrentSectionId(section.id)
    for (const block of section.teaching_blocks) {
      if (!workflow.tts_ready) break
      try {
        setStatus(`正在合成並播放：${section.title}`)
        const url = await getAudio(block)
        if (!audioRef.current) audioRef.current = new Audio()
        audioRef.current.src = url
        setPlayingId(block.block_id)
        await audioRef.current.play()
        await new Promise((resolve) => { audioRef.current.onended = resolve })
      } catch (error) {
        setStatus(error.message || '播放失敗。')
        setPlayingId(null)
        return
      }
    }
    setPlayingId(null)
    setStatus(`章節播放完成：${section.title}`)
  }

  async function downloadBlock(block) {
    try {
      setWorking(true)
      const url = await getAudio(block)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${filename}-${block.block_id}.mp3`
      document.body.appendChild(anchor); anchor.click(); anchor.remove()
      setStatus(`已下載區塊：${block.block_id}`)
    } catch (error) { setStatus(error.message || '下載失敗。') }
    finally { setWorking(false) }
  }

  async function downloadSection(section) {
    for (const block of section.teaching_blocks) await downloadBlock(block)
  }

  return (
    <section className="space-y-5 rounded-xl border border-indigo-100 bg-white p-4">
      <header>
        <h3 className="text-lg font-bold text-indigo-800">🎧 Markdown → AI 語音學習助教</h3>
        <p className="mt-1 text-sm text-slate-600">解析章節、生成初學者教學稿並檢查資訊完整性；只有通過檢查後才能播放或下載分段 MP3。</p>
      </header>

      <section className="space-y-3 rounded-lg bg-slate-50 p-3">
        <h4 className="font-semibold text-slate-800">1. 文件與學習設定</h4>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm font-medium">語音引擎<select className="mt-1 w-full rounded border p-2" value={provider} onChange={(event) => {
            const nextProvider = event.target.value
            setProvider(nextProvider)
            if (nextProvider === 'edge') setVoice(chineseVariant === 'zh-TW' ? taiwanVoices[0][0] : mainlandVoices[0][0])
            if (nextProvider === 'openai') setVoice('alloy')
          }}><option value="edge">Edge TTS（需網路）</option><option value="piper">本機 Piper（離線）</option><option value="openai">OpenAI TTS</option></select></label>
          {provider === 'edge' && <>
            <label className="text-sm font-medium">語言／口音<select className="mt-1 w-full rounded border p-2" value={chineseVariant} onChange={(event) => {
              const nextVariant = event.target.value
              setChineseVariant(nextVariant)
              setVoice((nextVariant === 'zh-TW' ? taiwanVoices : mainlandVoices)[0][0])
            }}><option value="zh-TW">繁體中文（台灣口音）</option><option value="zh-CN">简体中文（中国普通话）</option></select></label>
            <label className="text-sm font-medium">聲音<select className="mt-1 w-full rounded border p-2" value={voice} onChange={(event) => setVoice(event.target.value)}>{(chineseVariant === 'zh-TW' ? taiwanVoices : mainlandVoices).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
          </>}
          {provider === 'openai' && <label className="text-sm font-medium">聲音<select className="mt-1 w-full rounded border p-2" value={voice} onChange={(event) => setVoice(event.target.value)}>{voices.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>}
          {provider === 'piper' && <p className="self-end text-xs text-slate-600">Piper 語言/口音由本機 PIPER_MODEL_PATH 模型決定。</p>}
        </div>
        <label className="block text-sm font-medium text-slate-700">上傳 Markdown<input className="mt-1 block w-full rounded-lg border bg-white p-2" type="file" accept=".md,text/markdown,text/plain" onChange={(event) => loadMarkdown(event.target.files?.[0])} /></label>
        <label className="block text-sm font-medium text-slate-700">Markdown 原文<textarea className="mt-1 min-h-48 w-full rounded-lg border bg-white p-3 font-mono text-sm" value={text} onChange={(event) => { setText(event.target.value); setWorkflow(null) }} placeholder="# 章節標題\n\n貼上完整 Markdown 文件…" /><span className="mt-1 block text-right text-xs text-slate-500">{text.length.toLocaleString()} / {MAX_LENGTH.toLocaleString()}</span></label>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm font-medium">教學模式<select className="mt-1 w-full rounded border p-2" value={mode} onChange={(event) => setMode(event.target.value)}><option value="understanding">理解學習</option><option value="faithful">忠實講解</option></select></label>
          <label className="text-sm font-medium">學習者程度<select className="mt-1 w-full rounded border p-2" value={level} onChange={(event) => setLevel(event.target.value)}><option value="beginner">初學者</option><option value="intermediate">中級</option><option value="advanced">進階</option></select></label>
          <label className="text-sm font-medium">教學 LLM<select className="mt-1 w-full rounded border p-2" value={learningProvider} onChange={(event) => setLearningProvider(event.target.value)}><option value="ollama">Ollama 本機</option><option value="openai">OpenAI</option><option value="google">Google Gemini</option></select></label>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={chapterReview} onChange={(event) => setChapterReview(event.target.checked)} />每個主要章節加入小結與 2–4 個關鍵觀念複習</label>
        <button type="button" className="rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white disabled:opacity-50" onClick={createLesson} disabled={working || !text.trim() || text.length > MAX_LENGTH}>{working ? '處理中…' : '解析、生成教學稿並驗證'}</button>
      </section>

      <div role="status" className="text-sm text-slate-700">{status}</div>

      {workflow && <section className="space-y-4">
        <div className={`rounded-lg border p-3 text-sm ${workflow.tts_ready ? 'border-emerald-300 bg-emerald-50 text-emerald-900' : 'border-red-300 bg-red-50 text-red-900'}`}>
          <strong>內容完整性：{workflow.tts_ready ? '通過' : '未通過，已阻止語音合成'}</strong>
          <span className="ml-2">解析 {workflow.block_count} 個來源區塊，分成 {workflow.sections.length} 個章節。</span>
        </div>

        {workflow.validation.issues?.length > 0 && <section className="rounded-lg border border-red-200 p-3"><h4 className="font-semibold text-red-800">驗證問題</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{workflow.validation.issues.map((issue, index) => <li key={`${issue.message}-${index}`}><strong>[{issue.severity}]</strong> {issue.message} <span className="text-slate-500">{issue.source_block_ids?.join(', ')}</span></li>)}</ul></section>}

        <div className="flex flex-wrap items-center gap-3 rounded-lg border p-3">
          <strong className="text-sm">語音設定已套用：</strong>
          <span className="text-sm">{provider === 'edge' ? `${chineseVariant === 'zh-TW' ? '繁體中文（台灣）' : '简体中文（中国）'} · ${[...taiwanVoices, ...mainlandVoices].find(([id]) => id === voice)?.[1] || voice}` : provider === 'piper' ? '本機 Piper 離線模型' : `OpenAI · ${voice}`}</span>
          <span className="text-xs text-slate-500">MP3 依教學區塊分段生成，可單段下載或按章節播放。</span>
        </div>

        {workflow.sections.map((section) => <article key={section.id} className={`space-y-3 rounded-lg border p-4 ${currentSectionId === section.id ? 'border-indigo-400 bg-indigo-50/30' : ''}`}>
          <header className="flex flex-wrap items-center justify-between gap-2"><div><h4 className="font-bold text-slate-900">{section.title}</h4><p className="text-xs text-slate-500">來源第 {section.start_line} 行起 · {section.source_blocks.length} 個來源區塊 · 驗證 {section.validation.status === 'pass' ? '通過' : '未通過'}</p></div><div className="flex gap-2"><button className="rounded border px-3 py-1 text-sm disabled:opacity-50" disabled={!workflow.tts_ready || working} onClick={() => playSection(section)}>播放章節</button><button className="rounded border px-3 py-1 text-sm disabled:opacity-50" disabled={!workflow.tts_ready || working} onClick={() => downloadSection(section)}>下載章節 MP3</button></div></header>
          {section.teaching_blocks.map((block) => <div key={block.block_id} className="grid gap-3 border-t pt-3 lg:grid-cols-2"><div><div className="mb-1 flex items-center justify-between text-xs text-slate-500"><span>{block.block_id} · {block.block_type}</span><span>原文行 {block.source_blocks.map((source) => `${source.source.start_line}-${source.source.end_line}`).join(', ') || '未對應'}</span></div><p className="whitespace-pre-wrap text-sm text-slate-700">{block.spoken_text}</p>{block.added_explanation && <p className="mt-2 text-xs text-amber-800">AI 補充：{Array.isArray(block.added_explanation) ? block.added_explanation.join('；') : block.added_explanation}</p>}<div className="mt-2 flex gap-2"><button className="rounded border px-2 py-1 text-xs disabled:opacity-50" disabled={!workflow.tts_ready || working} onClick={() => playBlock(block)}>{playingId === block.block_id ? '播放中' : '重聽此段'}</button><button className="rounded border px-2 py-1 text-xs disabled:opacity-50" disabled={!workflow.tts_ready || working} onClick={() => downloadBlock(block)}>下載 MP3</button></div></div><details className="rounded bg-slate-50 p-3"><summary className="cursor-pointer text-xs font-semibold text-slate-600">查看對應原始 Markdown</summary>{block.source_blocks.map((source) => <pre key={source.block_id} className="mt-2 whitespace-pre-wrap text-xs text-slate-600">{source.source.raw_text}</pre>)}</details></div>)}
        </article>)}
        <audio ref={audioRef} controls className="w-full" onEnded={() => setPlayingId(null)} />
      </section>}
    </section>
  )
}
