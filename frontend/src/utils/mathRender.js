import katex from 'katex'
import 'katex/dist/katex.min.css'

/**
 * 将 content_html 中的 data-latex 占位符渲染为 KaTeX 公式。
 */
export function renderMathInElement(root) {
  if (!root) return

  root.querySelectorAll('.math-block').forEach((el) => {
    const latex = el.getAttribute('data-latex')
    if (!latex) return
    try {
      katex.render(latex, el, { displayMode: true, throwOnError: false })
    } catch {
      el.textContent = latex
    }
  })

  root.querySelectorAll('.math-inline').forEach((el) => {
    const latex = el.getAttribute('data-latex')
    if (!latex) return
    try {
      katex.render(latex, el, { displayMode: false, throwOnError: false })
    } catch {
      el.textContent = latex
    }
  })
}
