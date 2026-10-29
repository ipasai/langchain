import { processLearningDocument } from '../../lib/learningWorkflow'
import { synthesizeSpeech } from '../../lib/ttsHandlers'
import { getValidatedTeachingBlock, saveLearningJob } from '../../lib/learningStore'

export const config = {
  api: { bodyParser: { sizeLimit: '2mb' } },
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ error: 'method_not_allowed' })
  }
  const action = req.query.action || req.body?.action || ''
  try {
    if (action === 'process') {
      const progress = []
      const result = await processLearningDocument({ ...(req.body || {}), onProgress: (stage) => progress.push(stage) })
      result.progress = progress
      result.job_id = saveLearningJob(result)
      return res.status(200).json(result)
    }
    if (action === 'audio') {
      const { job_id, block_id, voice, provider } = req.body || {}
      if (!job_id || !block_id) return res.status(400).json({ error: 'missing_block_reference', message: '需要 job_id 與已驗證的 block_id。' })
      const block = getValidatedTeachingBlock(job_id, block_id)
      const { audio, voice: selectedVoice, provider: selectedProvider } = await synthesizeSpeech({ text: block.spoken_text, voice, provider, instructions: 'Use natural Taiwanese Mandarin. Read clearly at a comfortable teaching pace.' })
      res.setHeader('Content-Type', 'audio/mpeg')
      res.setHeader('Content-Length', String(audio.length))
      res.setHeader('X-TTS-Voice', selectedVoice)
      res.setHeader('X-TTS-Provider', selectedProvider)
      return res.status(200).send(audio)
    }
    return res.status(400).json({ error: 'unknown_action', action })
  } catch (error) {
    return res.status(error.status || 500).json({ error: 'learning_workflow_failed', message: error.message })
  }
}
