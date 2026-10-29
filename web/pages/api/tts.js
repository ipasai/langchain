import { synthesizeSpeech } from '../../lib/ttsHandlers'

export const config = {
  api: { bodyParser: { sizeLimit: '128kb' } },
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ error: 'method_not_allowed' })
  }

  try {
    const { audio, voice, provider } = await synthesizeSpeech(req.body || {})
    const filename = String(req.body?.filename || 'markdown-audio').replace(/[^a-zA-Z0-9._-]/g, '_').replace(/\.md$/i, '')
    res.setHeader('Content-Type', 'audio/mpeg')
    res.setHeader('Content-Length', String(audio.length))
    res.setHeader('Content-Disposition', `attachment; filename="${filename || 'markdown-audio'}.mp3"`)
    res.setHeader('X-TTS-Voice', voice)
    res.setHeader('X-TTS-Provider', provider)
    return res.status(200).send(audio)
  } catch (error) {
    return res.status(error.status || 500).json({ error: 'tts_failed', message: error.message })
  }
}
