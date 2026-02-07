import { useState } from 'react'
import type { Version, VersionCompareResponse } from '../types/document'

interface VersionDiffProps {
  comparison: VersionCompareResponse
  onClose: () => void
}

export default function VersionDiff({ comparison, onClose }: VersionDiffProps) {
  const [view, setView] = useState<'side' | 'unified'>('side')

  const renderDiff = () => {
    const diffLines = comparison.diff.split('\n')
    const fromLines = comparison.from_version.markdown_content.split('\n')
    const toLines = comparison.to_version.markdown_content.split('\n')

    if (view === 'unified') {
      return (
        <div className="space-y-0 font-mono text-sm">
          {diffLines.map((line, index) => {
            let className = 'px-4 py-1'
            if (line.startsWith('@@')) {
              className += ' bg-purple-500/20 text-purple-300'
            } else if (line.startsWith('+')) {
              className += ' bg-green-500/20 text-green-300'
            } else if (line.startsWith('-')) {
              className += ' bg-red-500/20 text-red-300'
            } else {
              className += ' text-gray-400'
            }
            return (
              <div key={index} className={className}>
                {line || '\u00A0'}
              </div>
            )
          })}
        </div>
      )
    }

    // Side by side view
    return (
      <div className="grid grid-cols-2 gap-4 font-mono text-sm">
        {/* From Version */}
        <div className="space-y-0">
          <div className="sticky top-0 bg-gray-900/90 px-4 py-2 border-b border-red-500/30 text-red-400 font-semibold">
            v{comparison.from_version.version_number} (Previous)
          </div>
          <div className="max-h-96 overflow-y-auto">
            {fromLines.map((line, index) => {
              const escapedLine = line.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
              const isRemoved = diffLines.some(
                (dl) => dl.startsWith(`-${line}`) || new RegExp(`^-.*${escapedLine}`).test(dl)
              )
              return (
                <div
                  key={index}
                  className={`px-4 py-1 ${isRemoved ? 'bg-red-500/20 text-red-300' : 'text-gray-500'}`}
                >
                  {line || '\u00A0'}
                </div>
              )
            })}
          </div>
        </div>

        {/* To Version */}
        <div className="space-y-0">
          <div className="sticky top-0 bg-gray-900/90 px-4 py-2 border-b border-green-500/30 text-green-400 font-semibold">
            v{comparison.to_version.version_number} (Current)
          </div>
          <div className="max-h-96 overflow-y-auto">
            {toLines.map((line, index) => {
              const escapedLine = line.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
              const isAdded = diffLines.some(
                (dl) => dl.startsWith(`+${line}`) || new RegExp(`^\\+.*${escapedLine}`).test(dl)
              )
              return (
                <div
                  key={index}
                  className={`px-4 py-1 ${isAdded ? 'bg-green-500/20 text-green-300' : 'text-gray-500'}`}
                >
                  {line || '\u00A0'}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="cyber-card max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div>
            <h3 className="text-xl font-bold neon-text-purple">Version Comparison</h3>
            <p className="text-sm text-gray-400 mt-1">
              Comparing v{comparison.from_version.version_number} → v{comparison.to_version.version_number}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* View Toggle */}
            <div className="flex items-center border border-gray-700 rounded">
              <button
                onClick={() => setView('side')}
                className={`px-3 py-1 text-sm ${
                  view === 'side'
                    ? 'bg-purple-500/30 text-purple-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Side by Side
              </button>
              <button
                onClick={() => setView('unified')}
                className={`px-3 py-1 text-sm ${
                  view === 'unified'
                    ? 'bg-purple-500/30 text-purple-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Unified
              </button>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-2xl"
            >
              ×
            </button>
          </div>
        </div>

        {/* Summary */}
        <div className="p-4 border-b border-gray-700 bg-gray-900/30">
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-red-400">-</span>
              <span className="text-gray-400">Removed lines</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-green-400">+</span>
              <span className="text-gray-400">Added lines</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-purple-400">≈</span>
              <span className="text-gray-400">Changed sections</span>
            </div>
          </div>
        </div>

        {/* Diff Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {comparison.diff ? (
            renderDiff()
          ) : (
            <div className="text-center py-12 text-gray-400">
              No differences found between these versions
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 flex justify-between items-center">
          <div className="text-sm text-gray-400">
            {comparison.from_version.change_summary && (
              <span className="mr-4">
                From: {comparison.from_version.change_summary}
              </span>
            )}
            {comparison.to_version.change_summary && (
              <span>
                To: {comparison.to_version.change_summary}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="cyber-btn px-6 py-2"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Simple inline diff viewer component
 */
interface InlineDiffProps {
  from: string
  to: string
}

export function InlineDiff({ from, to }: InlineDiffProps) {
  const fromLines = from.split('\n')
  const toLines = to.split('\n')
  const maxLines = Math.max(fromLines.length, toLines.length)

  return (
    <div className="font-mono text-sm space-y-0">
      {Array.from({ length: maxLines }).map((_, index) => {
        const fromLine = fromLines[index]
        const toLine = toLines[index]

        if (fromLine === toLine) {
          return (
            <div key={index} className="px-4 py-1 text-gray-500">
              {fromLine || '\u00A0'}
            </div>
          )
        }

        return (
          <div key={index} className="grid grid-cols-2 gap-2">
            {fromLine !== undefined && (
              <div className="px-4 py-1 bg-red-500/20 text-red-300">
                - {fromLine}
              </div>
            )}
            {toLine !== undefined && (
              <div className="px-4 py-1 bg-green-500/20 text-green-300">
                + {toLine}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
