import { describe, expect, it, vi, afterEach } from 'vitest'
import { synthesizeSpeech } from '../lib/ttsHandlers'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('Markdown speech handler', () => {
  it('rejects empty text before calling the provider', async () => {
    vi.stubEnv('OPENAI_API_KEY', 'test-key')
    await expect(synthesizeSpeech({ text: '   ' })).rejects.toThrow('請先輸入或上傳 Markdown 文字。')
  })

  it('rejects text above the limit', async () => {
    vi.stubEnv('OPENAI_API_KEY', 'test-key')
    await expect(synthesizeSpeech({ text: 'a'.repeat(12001) })).rejects.toThrow('文字超過限制')
  })

  it('returns MP3 bytes from the provider', async () => {
    vi.stubEnv('OPENAI_API_KEY', 'test-key')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: {}, arrayBuffer: async () => Uint8Array.from([1, 2, 3]).buffer }))
    const result = await synthesizeSpeech({ text: '# 測試', voice: 'nova' })
    expect(result.audio).toEqual(Buffer.from([1, 2, 3]))
    expect(result.voice).toBe('nova')
  })

  it('uses the configured local TTS endpoint without an OpenAI key', async () => {
    vi.stubEnv('OPENAI_API_KEY', '')
    vi.stubEnv('LOCAL_TTS_URL', 'http://127.0.0.1:8002/synthesize')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => Uint8Array.from([4, 5, 6]).buffer }))
    const result = await synthesizeSpeech({ text: '本機語音', provider: 'local' })
    expect(result.audio).toEqual(Buffer.from([4, 5, 6]))
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8002/synthesize', expect.objectContaining({ method: 'POST' }))
  })

  it('routes Taiwan Edge TTS through the local server without an OpenAI key', async () => {
    vi.stubEnv('OPENAI_API_KEY', '')
    vi.stubEnv('LOCAL_TTS_URL', 'http://127.0.0.1:8002/synthesize')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => Uint8Array.from([7, 8, 9]).buffer }))
    const result = await synthesizeSpeech({ text: '繁體中文語音', provider: 'edge', voice: 'zh-TW-HsiaoChenNeural' })
    expect(result.provider).toBe('edge')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toMatchObject({ provider: 'edge', voice: 'zh-TW-HsiaoChenNeural' })
  })

  it('routes Simplified Chinese Edge TTS voice through the local server', async () => {
    vi.stubEnv('OPENAI_API_KEY', '')
    vi.stubEnv('LOCAL_TTS_URL', 'http://127.0.0.1:8002/synthesize')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => Uint8Array.from([10, 11]).buffer }))
    const result = await synthesizeSpeech({ text: '简体中文语音', provider: 'edge', voice: 'zh-CN-XiaoxiaoNeural' })
    expect(result.provider).toBe('edge')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toMatchObject({ provider: 'edge', voice: 'zh-CN-XiaoxiaoNeural' })
  })
})
