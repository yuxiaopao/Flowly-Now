import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '../../../Frontend/src/utils/markdown'

describe('Markdown output safety', () => {
  it.each([
    '<script>window.untrusted = true</script>',
    '<img src="/missing.png" onerror="window.untrusted = true">',
    '<svg onload="window.untrusted = true"><circle /></svg>',
    '[unsafe link](javascript:alert(document.cookie))',
    '<a href="javascript:alert(document.cookie)">unsafe link</a>',
  ])('removes executable markup from user output: %s', input => {
    const container = document.createElement('div')
    container.innerHTML = renderMarkdown(input)
    expect(container.querySelector('script, iframe, svg, [onerror], [onload]')).toBeNull()
    for (const anchor of container.querySelectorAll('a[href]')) {
      expect(anchor.getAttribute('href')).not.toMatch(/^\s*javascript:/i)
    }
  })

  it('keeps useful tables, safe links and code examples readable', () => {
    const container = document.createElement('div')
    container.innerHTML = renderMarkdown('| Name | Value |\n| --- | --- |\n| Result | 42 |\n\n[reference](https://example.com/docs)\n\n`<img onerror="example">`')
    expect(container.querySelector('table')?.textContent).toContain('42')
    expect(container.querySelector('a')?.getAttribute('href')).toBe('https://example.com/docs')
    expect(container.querySelector('code')?.textContent).toBe('<img onerror="example">')
    expect(container.querySelector('img')).toBeNull()
  })
})
