import { useState, useEffect } from 'react'
import MonacoEditor from '@monaco-editor/react'

interface MarkdownEditorProps {
  content?: string
  placeholder?: string
  editable?: boolean
  onChange?: (markdown: string) => void
  onReady?: () => void
}

export default function MarkdownEditor({
  content = '',
  placeholder = 'Start writing markdown...',
  editable = true,
  onChange,
  onReady,
}: MarkdownEditorProps) {
  const [value, setValue] = useState(content)

  // Update value when content prop changes
  useEffect(() => {
    console.log('MarkdownEditor received content, length:', content?.length || 0)
    console.log('Content preview:', content?.substring(0, 100))
    setValue(content)
  }, [content])

  const handleEditorChange = (newValue: string | undefined) => {
    const markdown = newValue || ''
    setValue(markdown)
    if (onChange) {
      onChange(markdown)
    }
  }

  return (
    <div className="cyber-card overflow-hidden h-full">
      <MonacoEditor
        height="600px"
        language="markdown"
        value={value}
        onChange={handleEditorChange}
        onMount={() => {
          if (onReady) onReady()
        }}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          wordWrap: 'on',
          readOnly: !editable,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          padding: { top: 16, bottom: 16 },
          theme: 'vs-dark',
        }}
      />
    </div>
  )
}
