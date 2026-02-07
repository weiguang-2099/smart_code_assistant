/**
 * Format conversion utilities for Markdown ↔ TipTap
 * This is a client-side utility for immediate format conversion
 * Falls back to API conversion for complex cases
 */

import type { TipTapContent, TipTapNode } from '../types/document'

// ==================== Markdown to TipTap ====================

/**
 * Convert Markdown text to TipTap JSON format
 */
export function markdownToTipTap(markdown: string): TipTapContent {
  if (!markdown) {
    return { type: 'doc', content: [] }
  }

  const contentNodes: TipTapNode[] = []
  const lines = markdown.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    // Empty line - add paragraph break
    if (!trimmed) {
      if (contentNodes.length > 0 && contentNodes[contentNodes.length - 1].type !== 'paragraph') {
        contentNodes.push({ type: 'paragraph' })
      }
      i++
      continue
    }

    // Code block
    if (trimmed.startsWith('```')) {
      const codeBlock = parseCodeBlock(lines, i)
      contentNodes.push(codeBlock.node)
      i = codeBlock.endIndex
      continue
    }

    // Heading
    if (trimmed.startsWith('#')) {
      const heading = parseHeading(trimmed)
      contentNodes.push(heading)
      i++
      continue
    }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(trimmed)) {
      contentNodes.push({ type: 'horizontalRule' })
      i++
      continue
    }

    // Blockquote
    if (trimmed.startsWith('>')) {
      const blockquote = parseBlockquote(lines, i)
      contentNodes.push(blockquote.node)
      i = blockquote.endIndex
      continue
    }

    // List (unordered)
    if (/^[-*+]\s/.test(trimmed)) {
      const list = parseList(lines, i, 'bullet')
      contentNodes.push(list.node)
      i = list.endIndex
      continue
    }

    // List (ordered)
    if (/^\d+\.\s/.test(trimmed)) {
      const list = parseList(lines, i, 'ordered')
      contentNodes.push(list.node)
      i = list.endIndex
      continue
    }

    // Regular paragraph
    const paragraph = parseParagraph(line)
    contentNodes.push(paragraph)
    i++
  }

  // Remove trailing empty paragraphs
  while (contentNodes.length > 0 && isEmptyParagraph(contentNodes[contentNodes.length - 1])) {
    contentNodes.pop()
  }

  return { type: 'doc', content: contentNodes }
}

/**
 * Parse a fenced code block
 */
function parseCodeBlock(lines: string[], startIndex: number): { node: TipTapNode; endIndex: number } {
  const firstLine = lines[startIndex].trim()
  const langMatch = firstLine.match(/^```(\w+)?/)
  const language = langMatch?.[1] || ''

  const contentLines: string[] = []
  let i = startIndex + 1

  while (i < lines.length) {
    if (lines[i].trim().startsWith('```')) {
      break
    }
    contentLines.push(lines[i])
    i++
  }

  return {
    node: {
      type: 'codeBlock',
      attrs: { language },
      content: contentLines.length > 0 ? [{ type: 'text', text: contentLines.join('\n') }] : [],
    },
    endIndex: i + 1,
  }
}

/**
 * Parse a heading line
 */
function parseHeading(line: string): TipTapNode {
  const match = line.match(/^(#{1,6})\s+(.*)$/)
  if (match) {
    const level = match[1].length
    const text = match[2]
    return {
      type: 'heading',
      attrs: { level },
      content: text ? [{ type: 'text', text }] : [],
    }
  }
  return { type: 'paragraph', content: [] }
}

/**
 * Parse a blockquote
 */
function parseBlockquote(lines: string[], startIndex: number): { node: TipTapNode; endIndex: number } {
  const contentLines: string[] = []
  let i = startIndex

  while (i < lines.length) {
    const trimmed = lines[i].trim()
    if (!trimmed.startsWith('>')) {
      break
    }
    contentLines.push(trimmed.substring(1).trim())
    i++
  }

  const paragraphs = contentLines
    .filter((line) => line)
    .map((line) => ({
      type: 'paragraph',
      content: parseInlineText(line),
    }))

  return {
    node: {
      type: 'blockquote',
      content: paragraphs,
    },
    endIndex: i,
  }
}

/**
 * Parse a list (bullet or ordered)
 */
function parseList(
  lines: string[],
  startIndex: number,
  listType: 'bullet' | 'ordered'
): { node: TipTapNode; endIndex: number } {
  const items: TipTapNode[] = []
  let i = startIndex

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    let content = ''
    let isItem = false

    if (listType === 'bullet') {
      const match = trimmed.match(/^[-*+]\s+(.*)/)
      if (match) {
        content = match[1]
        isItem = true
      }
    } else {
      const match = trimmed.match(/^\d+\.\s+(.*)/)
      if (match) {
        content = match[1]
        isItem = true
      }
    }

    if (!isItem) {
      break
    }

    items.push({
      type: 'listItem',
      content: [
        {
          type: 'paragraph',
          content: parseInlineText(content),
        },
      ],
    })
    i++
  }

  return {
    node: {
      type: listType === 'bullet' ? 'bulletList' : 'orderedList',
      content: items,
    },
    endIndex: i,
  }
}

/**
 * Parse a regular paragraph
 */
function parseParagraph(line: string): TipTapNode {
  return {
    type: 'paragraph',
    content: parseInlineText(line),
  }
}

/**
 * Parse inline formatting (bold, italic, code, links)
 */
function parseInlineText(text: string): TipTapNode[] {
  if (!text) {
    return []
  }

  const nodes: TipTapNode[] = []
  let remaining = text

  const patterns = [
    { regex: /\*\*\*(.+?)\*\*\*/g, type: 'bold_italic' },
    { regex: /___(.+?)___/g, type: 'bold_italic' },
    { regex: /\*\*(.+?)\*\*/g, type: 'bold' },
    { regex: /__(.+?)__/g, type: 'bold' },
    { regex: /\*(.+?)\*/g, type: 'italic' },
    { regex: /_(.+?)_/g, type: 'italic' },
    { regex: /`(.+?)`/g, type: 'code' },
    { regex: /\[(.+?)\]\((.+?)\)/g, type: 'link' },
  ]

  while (remaining) {
    let earliestMatch: { index: number; length: number; pattern: typeof patterns[0] } | null = null

    for (const pattern of patterns) {
      pattern.regex.lastIndex = 0
      const match = pattern.regex.exec(remaining)
      if (match && match.index !== undefined) {
        if (!earliestMatch || match.index < earliestMatch.index) {
          earliestMatch = { index: match.index, length: match[0].length, pattern }
        }
      }
    }

    if (earliestMatch) {
      // Add text before the match
      if (earliestMatch.index > 0) {
        nodes.push({ type: 'text', text: remaining.substring(0, earliestMatch.index) })
      }

      // Add the formatted text
      const { regex, type } = earliestMatch.pattern
      regex.lastIndex = 0
      const match = regex.exec(remaining.substring(earliestMatch.index))

      if (match) {
        const innerText = match[1]

        if (type === 'link') {
          nodes.push({
            type: 'text',
            marks: [{ type: 'link', attrs: { href: match[2] } }],
            text: innerText,
          })
        } else if (type === 'code') {
          nodes.push({ type: 'code', text: innerText })
        } else if (type === 'bold') {
          nodes.push({
            type: 'text',
            marks: [{ type: 'bold' }],
            text: innerText,
          })
        } else if (type === 'italic') {
          nodes.push({
            type: 'text',
            marks: [{ type: 'italic' }],
            text: innerText,
          })
        } else if (type === 'bold_italic') {
          nodes.push({
            type: 'text',
            marks: [{ type: 'bold' }, { type: 'italic' }],
            text: innerText,
          })
        }
      }

      remaining = remaining.substring(earliestMatch.index + earliestMatch.length)
    } else {
      // No more matches
      nodes.push({ type: 'text', text: remaining })
      break
    }
  }

  return nodes.length > 0 ? nodes : [{ type: 'text', text }]
}

// ==================== TipTap to Markdown ====================

/**
 * Convert TipTap JSON to Markdown text
 */
export function tipTapToMarkdown(tiptap: TipTapContent): string {
  if (!tiptap || tiptap.type !== 'doc') {
    return ''
  }

  const content = tiptap.content || []
  if (content.length === 0) {
    return ''
  }

  const lines: string[] = []

  for (const node of content) {
    const markdown = nodeToMarkdown(node, 0)
    if (markdown) {
      lines.push(markdown)
    }
  }

  return lines.join('\n')
}

/**
 * Convert a TipTap node to Markdown
 */
function nodeToMarkdown(node: TipTapNode, indentLevel: number): string {
  const indent = '  '.repeat(indentLevel)
  const type = node.type
  const content = node.content || []

  switch (type) {
    case 'paragraph':
      const text = contentToText(content)
      return text ? `${indent}${text}` : ''

    case 'heading':
      const level = node.attrs?.level || 1
      const headingText = contentToText(content)
      return `${indent}${'#'.repeat(level)} ${headingText}`

    case 'codeBlock':
      const lang = (node.attrs?.language as string) || ''
      const codeText = contentToText(content, true)
      return `${indent}\`\`\`${lang}\n${indent}${codeText}\n${indent}\`\`\``

    case 'blockquote':
      const quotedLines = content.map((child) => {
        const childText = nodeToMarkdown(child, indentLevel)
        return childText.split('\n').map((line) => `${indent}> ${line}`).join('\n')
      })
      return quotedLines.join('\n')

    case 'bulletList':
      return content
        .map((child, idx) => {
          if (child.type === 'listItem') {
            const itemText = contentToText(child.content || [])
            return `${indent}- ${itemText}`
          }
          return ''
        })
        .filter(Boolean)
        .join('\n')

    case 'orderedList':
      return content
        .map((child, idx) => {
          if (child.type === 'listItem') {
            const itemText = contentToText(child.content || [])
            return `${indent}${idx + 1}. ${itemText}`
          }
          return ''
        })
        .filter(Boolean)
        .join('\n')

    case 'horizontalRule':
      return `${indent}---`

    case 'hardBreak':
      return '\n'

    case 'text': {
      let text = node.text || ''
      const marks = node.marks || []

      for (const mark of marks.reverse()) {
        const markType = mark.type
        if (markType === 'bold') {
          text = `**${text}**`
        } else if (markType === 'italic') {
          text = `*${text}*`
        } else if (markType === 'code') {
          text = `\`${text}\``
        } else if (markType === 'link') {
          const href = mark.attrs?.href || ''
          text = `[${text}](${href})`
        }
      }

      return text
    }

    case 'code':
      return `\`${node.text || ''}\``

    default:
      return content.map((child) => nodeToMarkdown(child, indentLevel)).join('')
  }
}

/**
 * Convert content nodes to plain text
 */
function contentToText(content: TipTapNode[], preserveNewlines = false): string {
  if (!content || content.length === 0) {
    return ''
  }

  const parts: string[] = []

  for (const node of content) {
    if (node.type === 'text') {
      let text = node.text || ''
      const marks = node.marks || []

      for (const mark of marks.reverse()) {
        const markType = mark.type
        if (markType === 'bold') {
          text = `**${text}**`
        } else if (markType === 'italic') {
          text = `*${text}*`
        } else if (markType === 'code') {
          text = `\`${text}\``
        } else if (markType === 'link') {
          const href = mark.attrs?.href || ''
          text = `[${text}](${href})`
        }
      }

      parts.push(text)
    } else if (node.type === 'hardBreak') {
      parts.push(preserveNewlines ? '\n' : ' ')
    } else if (node.type === 'code') {
      parts.push(`\`${node.text || ''}\``)
    } else {
      // Recursively handle nested content
      parts.push(nodeToMarkdown(node, 0))
    }
  }

  let result = parts.join('')
  if (!preserveNewlines) {
    result = result.replace(/\n/g, ' ')
  }

  return result
}

/**
 * Check if a node is an empty paragraph
 */
function isEmptyParagraph(node: TipTapNode): boolean {
  return node.type === 'paragraph' && (!node.content || node.content.length === 0)
}

// ==================== Utility Functions ====================

/**
 * Get plain text from TipTap content (strips formatting)
 */
export function getPlainText(tiptap: TipTapContent): string {
  if (!tiptap || !tiptap.content) {
    return ''
  }

  return tiptap.content
    .map((node) => getTextFromNode(node))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * Get text from a single node
 */
function getTextFromNode(node: TipTapNode): string {
  if (node.type === 'text') {
    return node.text || ''
  }

  if (node.content) {
    return node.content.map(getTextFromNode).join('')
  }

  return ''
}

/**
 * Count words in TipTap content
 */
export function countWords(tiptap: TipTapContent): number {
  const text = getPlainText(tiptap)
  return text.split(/\s+/).filter(Boolean).length
}

/**
 * Count characters in TipTap content
 */
export function countCharacters(tiptap: TipTapContent, includeSpaces = true): number {
  const text = getPlainText(tiptap)
  return includeSpaces ? text.length : text.replace(/\s/g, '').length
}
