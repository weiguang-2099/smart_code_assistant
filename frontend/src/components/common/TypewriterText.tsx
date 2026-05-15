/**
 * TypewriterText - Component for typewriter effect with cursor animation
 *
 * Features:
 * - Smooth character-by-character text display
 * - Blinking cursor animation
 * - Configurable speed
 * - Support for markdown content
 */
import React, { useEffect, useState, useRef } from 'react'

interface TypewriterTextProps {
  text: string
  speed?: number
  cursor?: boolean
  cursorChar?: string
  onComplete?: () => void
  className?: string
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 30,
  cursor = true,
  cursorChar = '|',
  onComplete,
  className = '',
}) => {
  const [displayedText, setDisplayedText] = useState('')
  const [isComplete, setIsComplete] = useState(false)
  const indexRef = useRef(0)

  useEffect(() => {
    setDisplayedText('')
    setIsComplete(false)
    indexRef.current = 0

    const interval = setInterval(() => {
      if (indexRef.current < text.length) {
        setDisplayedText(text.slice(0, indexRef.current + 1))
        indexRef.current += 1
      } else {
        clearInterval(interval)
        setIsComplete(true)
        onComplete?.()
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed, onComplete])

  return (
    <span className={className}>
      {displayedText}
      {cursor && !isComplete && (
        <span className="animate-pulse ml-0.5">{cursorChar}</span>
      )}
    </span>
  )
}

interface StreamingTextProps {
  content: string
  isStreaming: boolean
  cursorChar?: string
  className?: string
}

export const StreamingText: React.FC<StreamingTextProps> = ({
  content,
  isStreaming,
  cursorChar = '▋',
  className = '',
}) => {
  return (
    <span className={className}>
      {content}
      {isStreaming && (
        <span
          className="inline-block ml-0.5 w-2 h-5 bg-current animate-pulse"
          style={{ animationDuration: '0.8s' }}
        >
          {cursorChar}
        </span>
      )}
    </span>
  )
}

interface CursorProps {
  className?: string
}

export const BlinkingCursor: React.FC<CursorProps> = ({ className = '' }) => {
  return (
    <span
      className={`inline-block w-2 h-5 bg-blue-500 ml-0.5 ${className}`}
      style={{
        animation: 'blink 1s step-end infinite',
      }}
    />
  )
}

export default TypewriterText
