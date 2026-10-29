import { afterEach, describe, expect, it, vi } from 'vitest'
import { processLearningDocument } from '../lib/learningWorkflow'

afterEach(() => vi.unstubAllGlobals())

describe('learning workflow validation gate', () => {
  it('blocks TTS when an exact source number is paraphrased away', async () => {
    const sourceBlockId = 'block_00001'
    const fetchMock = vi.fn(async (_url, options) => {
      const prompt = JSON.parse(options.body).prompt
      let response
      if (prompt.includes('TASK A - ANALYZE')) response = JSON.stringify({ chapter_purpose: 'test' })
      else if (prompt.includes('TASK B - TEACHING SCRIPT')) response = JSON.stringify([{ block_id: 'teach_1', source_block_ids: [sourceBlockId], block_type: 'explanation', spoken_text: '必須保留相關項目。' }])
      else response = JSON.stringify({ status: 'pass', issues: [] })
      return { ok: true, json: async () => ({ response }) }
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await processLearningDocument({
      markdown: '必須保留 3 個項目。',
      config: { provider: 'ollama', model: 'test-model' },
    })

    expect(result.validation.status).toBe('fail')
    expect(result.tts_ready).toBe(false)
    expect(result.validation.issues.some((issue) => issue.severity === 'critical' && issue.message.includes('3 個'))).toBe(true)
  })
})
