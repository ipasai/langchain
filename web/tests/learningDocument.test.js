import { describe, expect, it } from 'vitest'
import { criticalTokenPresent, extractCriticalTokens, parseLearningDocument } from '../lib/learningDocument'

describe('learning Markdown parser', () => {
  it('preserves section hierarchy locations, GFM tables, and code blocks', () => {
    const source = '# Intro\n\nText.\n\n## Table\n\n| A | B |\n| -- | -- |\n| x | y |\n\n```js\nconst x = 1\n```'
    const document = parseLearningDocument(source)
    expect(document.sections.map((section) => section.title)).toEqual(['Intro', 'Table'])
    expect(document.sections[1].blocks.map((block) => block.type)).toContain('table')
    expect(document.sections[1].blocks.map((block) => block.type)).toContain('code')
    expect(document.sections[1].blocks.every((block) => block.source.start_line > 0 && block.block_id)).toBe(true)
  })

  it('detects numbers, units, and Traditional Chinese conditions', () => {
    expect(extractCriticalTokens('至少必須保留 3 個項目，誤差不超過 5%。')).toEqual(expect.arrayContaining(['至少', '必須', '3 個', '5%', '不超過']))
  })

  it('accepts equivalent spoken Chinese numerals but not omitted facts', () => {
    expect(criticalTokenPresent('3 個', '必須保留三個項目。')).toBe(true)
    expect(criticalTokenPresent('5%', '提升百分之五。')).toBe(true)
    expect(criticalTokenPresent('3 個', '必須保留相關項目。')).toBe(false)
  })
})
