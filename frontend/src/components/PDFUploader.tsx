import { useState, useRef } from 'react'
import { documentService } from '../services/documentService'

interface PDFUploaderProps {
  token: string
  onClose: () => void
  onComplete: (documentId: number) => void
  onError: (error: string) => void
}

export default function PDFUploader({ token, onClose, onComplete, onError }: PDFUploaderProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        onError('Please select a PDF file')
        return
      }
      setFile(selectedFile)
      // Auto-fill title from filename
      if (!title) {
        setTitle(selectedFile.name.replace('.pdf', ''))
      }
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      if (droppedFile.type !== 'application/pdf') {
        onError('Please drop a PDF file')
        return
      }
      setFile(droppedFile)
      if (!title) {
        setTitle(droppedFile.name.replace('.pdf', ''))
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleUpload = async () => {
    if (!file) {
      onError('Please select a file')
      return
    }

    if (!title.trim()) {
      onError('Please enter a title')
      return
    }

    setUploading(true)
    setProgress(0)

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 10, 90))
    }, 200)

    try {
      const result = await documentService.uploadPDF(
        token,
        file,
        {
          title: title.trim(),
          description: description.trim() || undefined,
          category: category.trim() || undefined,
        }
      )

      clearInterval(progressInterval)
      setProgress(100)

      // Note: The current API returns document_id: 0 in placeholder mode
      // In production, it would return the actual document ID
      setTimeout(() => {
        onComplete(result.document_id)
      }, 500)
    } catch (err) {
      clearInterval(progressInterval)
      onError(err instanceof Error ? err.message : 'Failed to upload PDF')
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="cyber-card max-w-lg w-full p-8">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-bold neon-text-purple tracking-wider">
            {'<UPLOAD PDF />'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
            disabled={uploading}
          >
            ×
          </button>
        </div>

        <div className="space-y-6">
          {/* File Drop Zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => !uploading && fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center transition-all cursor-pointer
              ${file ? 'border-purple-500 bg-purple-500/10' : 'border-gray-600 hover:border-purple-500/50'}
              ${uploading ? 'pointer-events-none opacity-60' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileSelect}
              className="hidden"
              disabled={uploading}
            />

            {file ? (
              <div className="space-y-2">
                <div className="text-4xl">📄</div>
                <p className="text-purple-300 font-medium">{file.name}</p>
                <p className="text-gray-400 text-sm">{formatFileSize(file.size)}</p>
                {!uploading && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setFile(null)
                      setTitle('')
                    }}
                    className="text-red-400 text-sm hover:text-red-300"
                  >
                    Remove
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-4xl">📁</div>
                <p className="text-gray-300">
                  Drop your PDF here or <span className="text-purple-400">browse</span>
                </p>
                <p className="text-gray-500 text-sm">PDF files only</p>
              </div>
            )}
          </div>

          {/* Document Metadata */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-purple-300 mb-2">
                TITLE *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                placeholder="Document Title"
                disabled={uploading}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-purple-300 mb-2">
                DESCRIPTION
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all resize-none"
                placeholder="What is this document about?"
                rows={2}
                disabled={uploading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-purple-300 mb-2">
                CATEGORY
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded text-gray-100 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                disabled={uploading}
              >
                <option value="">No Category</option>
                <option value="architecture">Architecture</option>
                <option value="api">API</option>
                <option value="tutorial">Tutorial</option>
                <option value="documentation">Documentation</option>
                <option value="notes">Notes</option>
              </select>
            </div>
          </div>

          {/* Progress Bar */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-purple-300">Parsing PDF...</span>
                <span className="text-gray-400">{progress}%</span>
              </div>
              <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 to-cyan-500 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 text-center">
                PDF parsing is currently in placeholder mode. The content will be placeholder text.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4">
            <button
              onClick={onClose}
              disabled={uploading}
              className="flex-1 cyber-btn py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!file || uploading || !title.trim()}
              className="flex-1 cyber-btn py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              {uploading ? 'Parsing...' : 'Upload & Parse'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
