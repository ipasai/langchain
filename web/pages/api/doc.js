import { uploadFile, indexDocument, queryIndex, listDocs, searchDocs, mindmap, generateQuiz } from '../../lib/docHandlers'

export default async function handler(req, res) {
  const action = req.query.action || (req.method === 'POST' && req.body && req.body.action) || ''

  try {
    if (action === 'test') return res.status(200).json({ ok: true, message: 'doc api ready' })

    if (action === 'upload' && req.method === 'POST') {
      const out = await uploadFile(req.body || {})
      return res.status(200).json(out)
    }

    if (action === 'index' && req.method === 'POST') {
      const out = await indexDocument(req.body || {})
      return res.status(200).json(out)
    }

    if (action === 'query') {
      const q = req.query.q || ''
      if (!q) return res.status(400).json({ error: 'missing_q' })
      return res.status(200).json(queryIndex(q))
    }

    if (action === 'list') {
      return res.status(200).json(listDocs())
    }

    if (action === 'search') {
      const q = req.method === 'GET' ? req.query.q : (req.body && req.body.q)
      if (!q) return res.status(400).json({ error: 'missing_q' })
      const out = await searchDocs(q)
      return res.status(200).json(out)
    }

    if (action === 'mindmap' && req.method === 'POST') {
      const out = await mindmap(req.body || {})
      return res.status(200).json(out)
    }

    if (action === 'quiz' && req.method === 'POST') {
      return res.status(200).json(await generateQuiz(req.body || {}))
    }

    return res.status(400).json({ error: 'unknown_action', action })
  } catch (e) {
    return res.status(500).json({ error: 'handler_error', detail: e.message })
  }
}
