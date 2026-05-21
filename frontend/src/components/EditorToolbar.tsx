import type { Editor } from '@tiptap/react'
import { useCallback, useState } from 'react'

interface EditorToolbarProps {
  editor: Editor | null
}

export default function EditorToolbar({ editor }: EditorToolbarProps) {
  // All hooks must be called unconditionally before any early return.
  const [showLinkInput, setShowLinkInput] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')

  const setLink = useCallback(() => {
    if (!editor) return
    if (linkUrl) {
      editor.chain().focus().setLink({ href: linkUrl }).run()
    } else {
      editor.chain().focus().unsetLink().run()
    }
    setShowLinkInput(false)
    setLinkUrl('')
  }, [editor, linkUrl])

  const addImage = useCallback(() => {
    if (!editor) return
    const url = window.prompt('Enter image URL:')
    if (url) {
      editor.chain().focus().setImage({ src: url }).run()
    }
  }, [editor])

  if (!editor) {
    return null
  }

  const ToolbarButton = ({
    onClick,
    active,
    disabled,
    children,
    title,
  }: {
    onClick: () => void
    active?: boolean
    disabled?: boolean
    children: React.ReactNode
    title: string
  }) => (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`
        p-2 rounded transition-all
        ${active ? 'bg-cyan-500/30 text-cyan-400 border border-cyan-500/50' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {children}
    </button>
  )

  return (
    <div className="cyber-card p-2">
      <div className="flex flex-wrap items-center gap-1">
        {/* Text Formatting */}
        <div className="flex items-center gap-1 pr-3 border-r border-gray-700">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive('bold')}
            title="Bold (Ctrl+B)"
          >
            <strong className="text-sm">B</strong>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive('italic')}
            title="Italic (Ctrl+I)"
          >
            <em className="text-sm">I</em>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().toggleCode().run()}
            active={editor.isActive('code')}
            title="Inline Code"
          >
            <span className="text-xs font-mono">&lt;/&gt;</span>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().unsetAllMarks().run()}
            title="Clear Formatting"
          >
            <span className="text-xs">T×</span>
          </ToolbarButton>
        </div>

        {/* Headings */}
        <div className="flex items-center gap-1 pr-3 border-r border-gray-700">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            active={editor.isActive('heading', { level: 1 })}
            title="Heading 1"
          >
            <span className="text-sm font-bold">H1</span>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive('heading', { level: 2 })}
            title="Heading 2"
          >
            <span className="text-sm font-bold">H2</span>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            active={editor.isActive('heading', { level: 3 })}
            title="Heading 3"
          >
            <span className="text-sm font-bold">H3</span>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().setParagraph().run()}
            active={editor.isActive('paragraph')}
            title="Paragraph"
          >
            <span className="text-xs">¶</span>
          </ToolbarButton>
        </div>

        {/* Lists */}
        <div className="flex items-center gap-1 pr-3 border-r border-gray-700">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive('bulletList')}
            title="Bullet List"
          >
            <span className="text-sm">• ≡</span>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive('orderedList')}
            title="Numbered List"
          >
            <span className="text-sm">1. ≡</span>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            active={editor.isActive('blockquote')}
            title="Blockquote"
          >
            <span className="text-sm">"</span>
          </ToolbarButton>
        </div>

        {/* Code Block */}
        <div className="flex items-center gap-1 pr-3 border-r border-gray-700">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            active={editor.isActive('codeBlock')}
            title="Code Block"
          >
            <span className="text-sm font-mono">{'{ }'}</span>
          </ToolbarButton>
        </div>

        {/* Links and Images */}
        <div className="flex items-center gap-1 pr-3 border-r border-gray-700">
          <ToolbarButton
            onClick={() => setShowLinkInput(!showLinkInput)}
            active={editor.isActive('link')}
            title="Add Link"
          >
            <span className="text-sm">🔗</span>
          </ToolbarButton>

          <ToolbarButton onClick={addImage} title="Add Image">
            <span className="text-sm">🖼</span>
          </ToolbarButton>
        </div>

        {/* Horizontal Rule */}
        <div className="flex items-center gap-1">
          <ToolbarButton
            onClick={() => editor.chain().focus().setHorizontalRule().run()}
            title="Horizontal Rule"
          >
            <span className="text-sm">—</span>
          </ToolbarButton>
        </div>

        {/* Undo/Redo */}
        <div className="flex items-center gap-1 ml-auto pl-3 border-l border-gray-700">
          <ToolbarButton
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="Undo (Ctrl+Z)"
          >
            <span className="text-sm">↶</span>
          </ToolbarButton>

          <ToolbarButton
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="Redo (Ctrl+Y)"
          >
            <span className="text-sm">↷</span>
          </ToolbarButton>
        </div>
      </div>

      {/* Link Input */}
      {showLinkInput && (
        <div className="mt-3 flex items-center gap-2 p-2 bg-gray-900/50 rounded border border-cyan-500/30">
          <input
            type="text"
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-100 text-sm focus:border-cyan-500 focus:outline-none"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                setLink()
              } else if (e.key === 'Escape') {
                setShowLinkInput(false)
                setLinkUrl('')
              }
            }}
            autoFocus
          />
          <button
            onClick={setLink}
            className="cyber-btn px-4 py-2 text-sm"
            style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
          >
            Add
          </button>
          <button
            onClick={() => {
              setShowLinkInput(false)
              setLinkUrl('')
            }}
            className="cyber-btn px-4 py-2 text-sm"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  )
}
