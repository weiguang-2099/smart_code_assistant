import { useRef, useState, useEffect, useCallback, memo } from 'react'

interface VirtualListProps<T> {
  items: T[]
  itemHeight: number
  containerHeight: number
  renderItem: (item: T, index: number) => React.ReactNode
  overscan?: number
  className?: string
  onScrollToEnd?: () => void
}

function VirtualListComponent<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  overscan = 3,
  className = '',
  onScrollToEnd,
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)

  const totalHeight = items.length * itemHeight

  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan)
  const endIndex = Math.min(
    items.length - 1,
    Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
  )

  const visibleItems = items.slice(startIndex, endIndex + 1)

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = e.currentTarget.scrollTop
    setScrollTop(newScrollTop)

    if (onScrollToEnd) {
      const { scrollHeight, clientHeight } = e.currentTarget
      if (scrollHeight - newScrollTop - clientHeight < itemHeight * 2) {
        onScrollToEnd()
      }
    }
  }, [itemHeight, onScrollToEnd])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleWheel = (e: WheelEvent) => {
      e.stopPropagation()
    }

    container.addEventListener('wheel', handleWheel, { passive: true })
    return () => container.removeEventListener('wheel', handleWheel)
  }, [])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        height: containerHeight,
        overflow: 'auto',
        position: 'relative',
      }}
      onScroll={handleScroll}
    >
      <div
        style={{
          height: totalHeight,
          position: 'relative',
        }}
      >
        {visibleItems.map((item, index) => (
          <div
            key={startIndex + index}
            style={{
              position: 'absolute',
              top: (startIndex + index) * itemHeight,
              height: itemHeight,
              width: '100%',
            }}
          >
            {renderItem(item, startIndex + index)}
          </div>
        ))}
      </div>
    </div>
  )
}

export const VirtualList = memo(VirtualListComponent) as typeof VirtualListComponent

interface DynamicVirtualListProps<T> {
  items: T[]
  estimatedItemHeight: number
  containerHeight: number
  renderItem: (item: T, index: number) => React.ReactNode
  className?: string
  onScrollToEnd?: () => void
  scrollRef?: React.RefObject<HTMLDivElement>
}

interface MessagePosition {
  index: number
  top: number
  height: number
}

function DynamicVirtualListComponent<T>({
  items,
  estimatedItemHeight,
  containerHeight,
  renderItem,
  className = '',
  onScrollToEnd,
  scrollRef,
}: DynamicVirtualListProps<T>) {
  const internalRef = useRef<HTMLDivElement>(null)
  const containerRef = scrollRef || internalRef
  const [scrollTop, setScrollTop] = useState(0)
  const [itemHeights, setItemHeights] = useState<Map<number, number>>(new Map())
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map())

  const getItemHeight = useCallback((index: number): number => {
    return itemHeights.get(index) || estimatedItemHeight
  }, [itemHeights, estimatedItemHeight])

  const getItemPositions = useCallback((): MessagePosition[] => {
    const positions: MessagePosition[] = []
    let top = 0

    items.forEach((_, index) => {
      const height = getItemHeight(index)
      positions.push({ index, top, height })
      top += height
    })

    return positions
  }, [items, getItemHeight])

  const positions = getItemPositions()
  const totalHeight = positions.length > 0
    ? positions[positions.length - 1].top + positions[positions.length - 1].height
    : 0

  const findStartIndex = useCallback((scrollTop: number): number => {
    let low = 0
    let high = positions.length - 1

    while (low < high) {
      const mid = Math.floor((low + high) / 2)
      if (positions[mid].top + positions[mid].height < scrollTop) {
        low = mid + 1
      } else {
        high = mid
      }
    }

    return Math.max(0, low - 2)
  }, [positions])

  const findEndIndex = useCallback((scrollBottom: number): number => {
    let low = 0
    let high = positions.length - 1

    while (low < high) {
      const mid = Math.floor((low + high) / 2)
      if (positions[mid].top < scrollBottom) {
        low = mid + 1
      } else {
        high = mid
      }
    }

    return Math.min(positions.length - 1, low + 2)
  }, [positions])

  const startIndex = findStartIndex(scrollTop)
  const endIndex = findEndIndex(scrollTop + containerHeight)
  const visibleItems = positions.slice(startIndex, endIndex + 1)

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = e.currentTarget.scrollTop
    setScrollTop(newScrollTop)

    if (onScrollToEnd) {
      const { scrollHeight, clientHeight } = e.currentTarget
      if (scrollHeight - newScrollTop - clientHeight < estimatedItemHeight * 2) {
        onScrollToEnd()
      }
    }
  }, [estimatedItemHeight, onScrollToEnd])

  useEffect(() => {
    const resizeObserver = new ResizeObserver((entries) => {
      const newHeights = new Map(itemHeights)

      entries.forEach((entry) => {
        const index = Number(entry.target.getAttribute('data-index'))
        if (!isNaN(index)) {
          const newHeight = entry.contentRect.height
          if (newHeights.get(index) !== newHeight) {
            newHeights.set(index, newHeight)
          }
        }
      })

      if (newHeights.size !== itemHeights.size ||
        Array.from(newHeights.entries()).some(([k, v]) => itemHeights.get(k) !== v)) {
        setItemHeights(newHeights)
      }
    })

    itemRefs.current.forEach((el) => {
      resizeObserver.observe(el)
    })

    return () => resizeObserver.disconnect()
  }, [visibleItems, itemHeights])

  const setItemRef = useCallback((index: number) => (el: HTMLDivElement | null) => {
    if (el) {
      itemRefs.current.set(index, el)
    } else {
      itemRefs.current.delete(index)
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        height: containerHeight,
        overflow: 'auto',
        position: 'relative',
      }}
      onScroll={handleScroll}
    >
      <div
        style={{
          height: totalHeight,
          position: 'relative',
        }}
      >
        {visibleItems.map(({ index, top }) => (
          <div
            key={index}
            ref={setItemRef(index)}
            data-index={index}
            style={{
              position: 'absolute',
              top,
              width: '100%',
            }}
          >
            {renderItem(items[index], index)}
          </div>
        ))}
      </div>
    </div>
  )
}

export const DynamicVirtualList = memo(DynamicVirtualListComponent) as typeof DynamicVirtualListComponent

export function useScrollToBottom<T extends HTMLElement>() {
  const ref = useRef<T>(null)

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    if (ref.current) {
      ref.current.scrollTo({
        top: ref.current.scrollHeight,
        behavior,
      })
    }
  }, [])

  return { ref, scrollToBottom }
}
