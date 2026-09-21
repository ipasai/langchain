import { useEffect, useRef, useState } from 'react'

export default function MermaidRenderer({ code }) {
  const ref = useRef(null)
  const [svg, setSvg] = useState('')

  useEffect(() => {
    if (!code) { setSvg(''); return }
    let mounted = true
    ;(async () => {
      if (typeof window === 'undefined') return
      try {
        const mermaid = (await import('mermaid'))
        mermaid.initialize({ startOnLoad: false })
        const id = 'mmd_' + Date.now()
        mermaid.mermaidAPI.render(id, code, (svgCode) => {
          if (mounted) setSvg(svgCode)
        })
      } catch (e) {
        console.error('mermaid render error', e)
      }
    })()
    return () => { mounted = false }
  }, [code])

  function downloadSvg() {
    if (!svg) return
    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'mindmap.svg'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      {svg && (
        <div className="mb-3 p-3 bg-white border rounded">
          <div className="flex justify-between">
            <div className="font-medium">心智圖</div>
            <div>
              <button onClick={downloadSvg} className="px-2 py-1 bg-gray-200 rounded mr-2">下載 SVG</button>
            </div>
          </div>
          <div className="mt-2" dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
      )}
    </div>
  )
}
