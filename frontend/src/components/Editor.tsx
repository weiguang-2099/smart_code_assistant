import { Editor } from '@monaco-editor/react'
import { useEffect } from 'react'

interface EditorProps {
  language?: string
  theme?: 'vs-dark' | 'vs-light'
  value?: string
  onChange?: (value: string | undefined) => void
  height?: string
}

export default function CodeEditor({
  language = 'javascript',
  theme = 'vs-dark',
  value = '',
  onChange,
  height = '500px'
}: EditorProps) {
  useEffect(() => {
    const handleResize = () => {
      window.dispatchEvent(new Event('resize'))
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="rounded-lg overflow-hidden shadow-lg">
      <Editor
        height={height}
        defaultLanguage={language}
        theme={theme}
        value={value}
        onChange={onChange}
        options={{
          minimap: { enabled: true },
          fontSize: 14,
          lineNumbers: 'on',
          roundedSelection: true,
          scrollBeyondLastLine: false,
          readOnly: false,
          automaticLayout: true,
        }}
      />
    </div>
  )
}
