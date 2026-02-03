import { useState } from 'react'
import CodeEditor from '../components/Editor'

export default function EditorPage() {
  const [code, setCode] = useState(`// Welcome to Smart Code Assistant
// Start writing your code here...

function example() {
  console.log('Hello, World!')
  return true
}

example()`)

  const [language, setLanguage] = useState('javascript')

  return (
    <div className="space-y-6">
      <div className="cyber-card p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold neon-text tracking-wider">{'<CODE/>'}</h2>
            <p className="text-sm text-gray-400 mt-1">Neural Code Editor v1.0</p>
          </div>
          <div className="flex gap-3">
            <button
              className="cyber-btn px-6 py-2"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
              onClick={() => console.log('Save clicked')}
            >
              ► SAVE
            </button>
            <button
              className="cyber-btn px-6 py-2"
              onClick={() => console.log('Share clicked')}
            >
              ► SHARE
            </button>
          </div>
        </div>
      </div>

      <div className="cyber-card p-6">
        <div className="mb-6">
          <label className="block text-sm font-medium text-cyan-300 mb-2 tracking-wider">
            PROGRAMMING LANGUAGE
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full bg-gray-900/50 border border-cyan-500/30 rounded px-4 py-3 text-sm text-gray-100 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all cursor-pointer"
          >
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="python">Python</option>
            <option value="java">Java</option>
            <option value="csharp">C#</option>
            <option value="go">Go</option>
            <option value="rust">Rust</option>
          </select>
        </div>

        <div className="relative">
          <div className="absolute -top-3 left-4 px-2 bg-gray-900 text-xs text-cyan-400 border border-cyan-500/30 rounded">
            SOURCE CODE
          </div>
          <CodeEditor
            value={code}
            onChange={setCode}
            language={language}
            theme="vs-dark"
            height="600px"
          />
        </div>

        <div className="mt-6 flex justify-between items-center pt-4 border-t border-gray-700">
          <div className="flex gap-6 text-sm">
            <span className="text-gray-400">
              LINES: <span className="text-cyan-400 font-mono">{code.split('\n').length}</span>
            </span>
            <span className="text-gray-400">
              CHARS: <span className="text-cyan-400 font-mono">{code.length}</span>
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            AUTO-SAVE ENABLED
          </div>
        </div>
      </div>
    </div>
  )
}
