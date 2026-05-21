/**
 * Vitest setup - runs before each test file.
 *
 * Wires up jest-dom matchers, a fresh localStorage between tests, and
 * stubs window APIs jsdom doesn't implement (matchMedia, IntersectionObserver).
 */
import '@testing-library/jest-dom/vitest'
import { afterEach, beforeAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
  localStorage.clear()
  sessionStorage.clear()
  vi.restoreAllMocks()
})

beforeAll(() => {
  // jsdom lacks matchMedia; some components query it.
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })

  // IntersectionObserver stub - virtual list / lazy load components rely on it.
  class IO {
    observe = vi.fn()
    unobserve = vi.fn()
    disconnect = vi.fn()
    takeRecords = vi.fn().mockReturnValue([])
  }
  ;(window as unknown as { IntersectionObserver: typeof IO }).IntersectionObserver = IO
})
