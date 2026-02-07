import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import { common, createLowlight } from 'lowlight'
import { useEffect, useState } from 'react'
import type { TipTapContent } from '../types/document'
import EditorToolbar from './EditorToolbar'

// Initialize lowlight for syntax highlighting
const lowlight = createLowlight(common)

interface TipTapEditorProps {
  content?: TipTapContent | string
  placeholder?: string
  editable?: boolean
  onChange?: (content: TipTapContent, markdown: string) => void
  onReady?: () => void
}

export default function TipTapEditor({
  content,
  placeholder = 'Start typing...',
  editable = true,
  onChange,
  onReady,
}: TipTapEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        codeBlock: false, // Use CodeBlockLowlight instead
      }),
      Placeholder.configure({
        placeholder,
        emptyEditorClass: 'is-editor-empty',
      }),
      Image.configure({
        inline: true,
        allowBase64: true,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-cyan-400 underline hover:text-cyan-300',
        },
      }),
      CodeBlockLowlight.configure({
        lowlight,
        HTMLAttributes: {
          class: 'code-block',
        },
      }),
    ],
    content: typeof content === 'string' ? content : content,
    editable,
    editorProps: {
      attributes: {
        class: 'tiptap-editor-content',
      },
    },
    onUpdate: ({ editor }) => {
      if (onChange) {
        const json = editor.getJSON() as TipTapContent
        const markdown = editor.storage.markdown || getMarkdownFromEditor(editor)
        onChange(json, markdown)
      }
    },
    onCreate: ({ editor }) => {
      if (onReady) {
        onReady()
      }
    },
  })

  // Update content when props change
  useEffect(() => {
    if (editor && content !== undefined) {
      const currentContent = editor.getJSON()
      const newContent = typeof content === 'string' ? content : content

      // Only update if content actually changed
      if (JSON.stringify(currentContent) !== JSON.stringify(newContent)) {
        editor.commands.setContent(newContent)
      }
    }
  }, [content, editor])

  // Update editable state
  useEffect(() => {
    if (editor) {
      editor.setEditable(editable)
    }
  }, [editable, editor])

  if (!editor) {
    return (
      <div className="cyber-card p-8 text-center">
        <div className="animate-spin text-2xl neon-text">◌</div>
        <p className="text-gray-400 mt-2">Loading editor...</p>
      </div>
    )
  }

  return (
    <div className="tiptap-editor-container">
      {editable && <EditorToolbar editor={editor} />}

      <div className="cyber-card p-6">
        <EditorContent editor={editor} />
      </div>

      <style>{`
        .tiptap-editor-container {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .tiptap-editor-content {
          outline: none;
          min-height: 400px;
        }

        .tiptap-editor-content p.is-editor-empty::before {
          content: attr(data-placeholder);
          float: left;
          color: #6b7280;
          pointer-events: none;
          height: 0;
        }

        .tiptap-editor-content h1 {
          font-size: 1.875rem;
          font-weight: 700;
          margin-top: 1rem;
          margin-bottom: 0.5rem;
          color: #22d3ee;
          text-shadow: 0 0 10px rgba(34, 211, 238, 0.3);
        }

        .tiptap-editor-content h2 {
          font-size: 1.5rem;
          font-weight: 600;
          margin-top: 0.875rem;
          margin-bottom: 0.5rem;
          color: #a78bfa;
        }

        .tiptap-editor-content h3 {
          font-size: 1.25rem;
          font-weight: 600;
          margin-top: 0.75rem;
          margin-bottom: 0.5rem;
          color: #c084fc;
        }

        .tiptap-editor-content p {
          margin-bottom: 0.75rem;
          line-height: 1.75;
          color: #d1d5db;
        }

        .tiptap-editor-content strong {
          font-weight: 700;
          color: #22d3ee;
        }

        .tiptap-editor-content em {
          font-style: italic;
          color: #a78bfa;
        }

        .tiptap-editor-content code {
          background: rgba(34, 211, 238, 0.1);
          border: 1px solid rgba(34, 211, 238, 0.3);
          border-radius: 0.25rem;
          padding: 0.125rem 0.375rem;
          font-family: 'Monaco', 'Menlo', monospace;
          font-size: 0.875em;
          color: #22d3ee;
        }

        .tiptap-editor-content pre {
          background: #1a1a2e;
          border: 1px solid rgba(34, 211, 238, 0.3);
          border-radius: 0.5rem;
          padding: 1rem;
          margin: 1rem 0;
          overflow-x: auto;
        }

        .tiptap-editor-content pre code {
          background: transparent;
          border: none;
          padding: 0;
          color: #e5e7eb;
        }

        .tiptap-editor-content ul,
        .tiptap-editor-content ol {
          margin: 0.75rem 0;
          padding-left: 1.5rem;
          color: #d1d5db;
        }

        .tiptap-editor-content li {
          margin: 0.25rem 0;
        }

        .tiptap-editor-content ul li {
          list-style-type: disc;
        }

        .tiptap-editor-content ol li {
          list-style-type: decimal;
        }

        .tiptap-editor-content blockquote {
          border-left: 3px solid rgba(167, 139, 250, 0.5);
          padding-left: 1rem;
          margin: 1rem 0;
          color: #a78bfa;
          font-style: italic;
        }

        .tiptap-editor-content hr {
          border: none;
          border-top: 1px solid rgba(34, 211, 238, 0.3);
          margin: 2rem 0;
        }

        .tiptap-editor-content a {
          color: #22d3ee;
          text-decoration: underline;
          cursor: pointer;
        }

        .tiptap-editor-content a:hover {
          color: #67e8f9;
        }

        .tiptap-editor-content img {
          max-width: 100%;
          height: auto;
          border-radius: 0.5rem;
          margin: 1rem 0;
        }

        /* Syntax highlighting */
        .hljs {
          color: #e5e7eb;
        }

        .hljs-comment,
        .hljs-quote {
          color: #6b7280;
          font-style: italic;
        }

        .hljs-keyword,
        .hljs-selector-tag,
        .hljs-subst {
          color: #c084fc;
        }

        .hljs-number,
        .hljs-literal {
          color: #22d3ee;
        }

        .hljs-string,
        .hljs-doctag {
          color: #34d399;
        }

        .hljs-title,
        .hljs-section,
        .hljs-selector-id {
          color: #f472b6;
        }

        .hljs-type,
        .hljs-class .hljs-title {
          color: #fbbf24;
        }

        .hljs-tag,
        .hljs-name,
        .hljs-attribute {
          color: #22d3ee;
          font-weight: normal;
        }

        .hljs-regexp,
        .hljs-link {
          color: #34d399;
        }

        .hljs-symbol,
        .hljs-bullet {
          color: #f472b6;
        }

        .hljs-built_in,
        .hljs-builtin-name {
          color: #fbbf24;
        }

        .hljs-meta {
          color: #6b7280;
        }

        .hljs-deletion {
          background: #fecaca;
        }

        .hljs-addition {
          background: #bbf7d0;
        }

        .hljs-emphasis {
          font-style: italic;
        }

        .hljs-strong {
          font-weight: bold;
        }
      `}</style>
    </div>
  )
}

/**
 * Get markdown content from editor
 */
function getMarkdownFromEditor(editor: ReturnType<typeof useEditor>): string {
  if (!editor) return ''

  const html = editor.getHTML()
  // Simple HTML to Markdown conversion
  return html
    .replace(/<h1[^>]*>(.*?)<\/h1>/gi, '# $1\n\n')
    .replace(/<h2[^>]*>(.*?)<\/h2>/gi, '## $1\n\n')
    .replace(/<h3[^>]*>(.*?)<\/h3>/gi, '### $1\n\n')
    .replace(/<strong[^>]*>(.*?)<\/strong>/gi, '**$1**')
    .replace(/<em[^>]*>(.*?)<\/em>/gi, '*$1*')
    .replace(/<code[^>]*>(.*?)<\/code>/gi, '`$1`')
    .replace(/<pre[^>]*>(.*?)<\/pre>/gi, '```\n$1\n```')
    .replace(/<ul[^>]*>(.*?)<\/ul>/gi, '$1')
    .replace(/<ol[^>]*>(.*?)<\/ol>/gi, '$1')
    .replace(/<li[^>]*>(.*?)<\/li>/gi, '- $1\n')
    .replace(/<p[^>]*>(.*?)<\/p>/gi, '$1\n\n')
    .replace(/<br[^>]*>/gi, '\n')
    .replace(/<a href="([^"]*)"[^>]*>(.*?)<\/a>/gi, '[$2]($1)')
    .replace(/<blockquote[^>]*>(.*?)<\/blockquote>/gi, '> $1\n\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .trim()
}

/**
 * Hook to get word and character counts
 */
export function useEditorStats(editor: ReturnType<typeof useEditor> | null) {
  const [stats, setStats] = useState({ words: 0, characters: 0 })

  useEffect(() => {
    if (!editor) return

    const updateStats = () => {
      const text = editor.getText()
      const words = text.split(/\s+/).filter(Boolean).length
      const characters = text.length
      setStats({ words, characters })
    }

    updateStats()
    editor.on('update', updateStats)

    return () => {
      editor.off('update', updateStats)
    }
  }, [editor])

  return stats
}
