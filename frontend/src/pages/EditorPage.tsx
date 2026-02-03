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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Code Editor</h2>
        <div className="space-x-2">
          <button
            className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors"
            onClick={() => console.log('Save clicked')}
          >
            Save
          </button>
          <button
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
            onClick={() => console.log('Share clicked')}
          >
            Share
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Language
          </label>
          <select className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500">
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="python">Python</option>
            <option value="java">Java</option>
            <option value="csharp">C#</option>
            <option value="go">Go</option>
            <option value="rust">Rust</option>
          </select>
        </div>

        <CodeEditor
          value={code}
          onChange={setCode}
          language="javascript"
          theme="vs-dark"
          height="600px"
        />

        <div className="mt-4 flex justify-between text-sm text-gray-600">
          <span>Lines: {code.split('\n').length}</span>
          <span>Characters: {code.length}</span>
        </div>
      </div>
    </div>
  )
}
