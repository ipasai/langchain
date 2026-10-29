import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkGfm from 'remark-gfm'

const parser = unified().use(remarkParse).use(remarkGfm)
const TEXT_TYPES = new Set(['paragraph', 'heading', 'blockquote', 'list', 'table', 'code', 'html', 'thematicBreak'])

function sourceText(markdown, node) {
  const start = Math.max(0, (node.position?.start?.line || 1) - 1)
  const end = Math.max(start + 1, node.position?.end?.line || start + 1)
  return markdown.split(/\r?\n/).slice(start, end).join('\n')
}

export function parseLearningDocument(markdown) {
  const tree = parser.parse(markdown)
  const sections = []
  let current = null
  let blockIndex = 0

  for (const node of tree.children) {
    if (node.type === 'heading') {
      const title = sourceText(markdown, node).replace(/^#+\s*/, '').trim()
      current = {
        id: `section_${String(sections.length + 1).padStart(3, '0')}`,
        title: title || `第 ${sections.length + 1} 節`,
        depth: node.depth,
        start_line: node.position?.start?.line || 1,
        blocks: [],
      }
      sections.push(current)
      continue
    }

    if (!TEXT_TYPES.has(node.type)) continue
    if (!current) {
      current = { id: 'section_000', title: '文件導讀', depth: 1, start_line: 1, blocks: [] }
      sections.push(current)
    }

    const raw = sourceText(markdown, node).trim()
    if (!raw) continue
    blockIndex += 1
    current.blocks.push({
      block_id: `block_${String(blockIndex).padStart(5, '0')}`,
      parent_block_id: current.id,
      type: node.type,
      source: {
        start_line: node.position?.start?.line || 1,
        end_line: node.position?.end?.line || node.position?.start?.line || 1,
        raw_text: raw,
      },
    })
  }

  const nonEmpty = sections.filter((section) => section.blocks.length > 0)
  return {
    schema_version: '1.0',
    document_id: `doc_${Date.now()}`,
    sections: nonEmpty,
    block_count: nonEmpty.reduce((sum, section) => sum + section.blocks.length, 0),
  }
}

export function extractCriticalTokens(text) {
  const patterns = [
    /(?<![\p{L}\p{N}])[-+]?\d+(?:[.,]\d+)*(?:\s?(?:%|％|倍|毫秒|秒|分鐘|小時|天|年|KB|MB|GB|TB|ms|s|kg|g|km|cm|mm|°C|℃|元|美元|項|個|次|年|月|日))?/giu,
    /(?:不超過|不得超過|不低於|不高於|超過|低於|高於|大於|小於|以上|以下|不|未|無法|除非|只有|僅當|至少|至多|不得|必須|必要|例外|限制|條件|otherwise|unless|only if|must not|at least|at most)/giu,
  ]
  const matches = []
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      const token = match[0].trim()
      if (token && !matches.includes(token)) matches.push(token)
    }
  }
  return matches
}

const chineseDigits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']

function chineseInteger(value) {
  if (!Number.isInteger(value) || value < 0 || value >= 10000) return String(value)
  if (value === 0) return '零'
  const units = ['', '十', '百', '千']
  const digits = String(value).split('').map(Number)
  let output = ''
  let pendingZero = false
  for (let index = 0; index < digits.length; index += 1) {
    const digit = digits[index]
    const place = digits.length - index - 1
    if (digit === 0) {
      if (output) pendingZero = true
      continue
    }
    if (pendingZero) output += '零'
    pendingZero = false
    if (!(digit === 1 && place === 1 && output === '')) output += chineseDigits[digit]
    output += units[place]
  }
  return output
}

function chineseNumber(value) {
  const [integer, decimal] = String(value).replace(',', '.').split('.')
  const whole = chineseInteger(Number(integer))
  if (!decimal) return whole
  return `${whole}點${decimal.split('').map((digit) => chineseDigits[Number(digit)] || digit).join('')}`
}

export function criticalTokenPresent(token, script) {
  if (script.includes(token)) return true
  const match = token.match(/^([-+]?\d+(?:[.,]\d+)*)(\s?.*)$/u)
  if (!match) return false
  const [, numeric, unit] = match
  const chinese = chineseNumber(numeric)
  const compact = (value) => value.replace(/\s+/gu, '')
  const text = compact(script)
  const unitText = compact(unit)
  if (unitText.includes('%') || unitText.includes('％')) {
    return text.includes(`百分之${chinese}`) || text.includes(`${chinese}%`) || text.includes(`${chinese}％`)
  }
  return Boolean(unitText && text.includes(`${chinese}${unitText}`))
}
