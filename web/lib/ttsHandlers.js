const MAX_TEXT_LENGTH = 12000
const ALLOWED_VOICES = new Set(['alloy', 'ash', 'ballad', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer'])

export async function synthesizeSpeech({ text, voice = 'alloy', instructions = '', provider = 'openai' }) {
  const content = String(text || '').trim()
  if (!content) {
    const error = new Error('請先輸入或上傳 Markdown 文字。')
    error.status = 400
    throw error
  }
  if (content.length > MAX_TEXT_LENGTH) {
    const error = new Error(`文字超過限制，最多 ${MAX_TEXT_LENGTH} 個字元。`)
    error.status = 413
    throw error
  }

  if (provider === 'local' || provider === 'piper' || provider === 'edge') {
    const localUrl = process.env.LOCAL_TTS_URL || 'http://127.0.0.1:8002/synthesize'
    let response
    try {
      response = await fetch(localUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: content, voice, instructions, provider: provider === 'edge' ? 'edge' : 'piper' }),
        signal: AbortSignal.timeout(180000),
      })
    } catch (cause) {
      const error = new Error(`無法連線到本機 TTS 服務 (${localUrl})。請先啟動本機語音服務。`)
      error.status = 503
      throw error
    }
    if (!response.ok) {
      const error = new Error(`本機 TTS 錯誤 (${response.status}): ${(await response.text()).slice(0, 500)}`)
      error.status = response.status
      throw error
    }
    const audio = Buffer.from(await response.arrayBuffer())
    return { audio, voice, bytes: audio.length, provider }
  }

  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) {
    const error = new Error('尚未設定 OPENAI_API_KEY。若要離線使用，請改選「本機 Piper」。')
    error.status = 503
    throw error
  }
  const selectedVoice = ALLOWED_VOICES.has(voice) ? voice : 'alloy'
  const response = await fetch('https://api.openai.com/v1/audio/speech', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini-tts',
      voice: selectedVoice,
      input: content,
      instructions: instructions || 'Read the text clearly and naturally in Traditional Chinese. Keep English terms pronounced naturally.',
      response_format: 'mp3',
    }),
  })

  if (!response.ok) {
    const detail = await response.text()
    const error = new Error(`TTS 服務錯誤 (${response.status}): ${detail.slice(0, 500)}`)
    error.status = response.status
    throw error
  }
  if (!response.body) throw new Error('TTS 服務未回傳音訊資料。')

  const audio = Buffer.from(await response.arrayBuffer())
  return { audio, voice: selectedVoice, bytes: audio.length, provider: 'openai' }
}
