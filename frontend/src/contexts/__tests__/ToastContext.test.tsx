import { act, render, renderHook, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider, useToast } from '../ToastContext'

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <ToastProvider>{children}</ToastProvider>
)

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useToast', () => {
  it('throws if used outside the provider', () => {
    // Suppress React's expected console.error from the throw.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => renderHook(() => useToast())).toThrow(/within a ToastProvider/)
    spy.mockRestore()
  })

  it('starts with an empty toast list', () => {
    const { result } = renderHook(() => useToast(), { wrapper })
    expect(result.current.toasts).toEqual([])
  })

  it('addToast inserts a toast with the correct shape', () => {
    const { result } = renderHook(() => useToast(), { wrapper })
    act(() => {
      result.current.addToast('success', 'Saved')
    })
    expect(result.current.toasts).toHaveLength(1)
    const [toast] = result.current.toasts
    expect(toast.type).toBe('success')
    expect(toast.message).toBe('Saved')
    expect(toast.id).toBeTruthy()
  })

  it('helper methods route to the right type', () => {
    const { result } = renderHook(() => useToast(), { wrapper })
    act(() => {
      result.current.success('s')
      result.current.error('e')
      result.current.warning('w')
      result.current.info('i')
    })
    const types = result.current.toasts.map((t) => t.type)
    expect(types).toEqual(['success', 'error', 'warning', 'info'])
  })

  it('auto-dismisses after the duration', () => {
    const { result } = renderHook(() => useToast(), { wrapper })
    act(() => {
      result.current.addToast('info', 'fades soon', 1000)
    })
    expect(result.current.toasts).toHaveLength(1)
    act(() => {
      vi.advanceTimersByTime(1001)
    })
    expect(result.current.toasts).toHaveLength(0)
  })

  it('duration of 0 disables auto-dismiss', () => {
    const { result } = renderHook(() => useToast(), { wrapper })
    act(() => {
      result.current.addToast('info', 'sticky', 0)
    })
    expect(result.current.toasts).toHaveLength(1)
    act(() => {
      vi.advanceTimersByTime(60_000)
    })
    expect(result.current.toasts).toHaveLength(1)
  })

  it('removeToast removes by id', () => {
    const { result } = renderHook(() => useToast(), { wrapper })
    act(() => {
      result.current.addToast('info', 'keep me', 0)
      result.current.addToast('info', 'remove me', 0)
    })
    const toRemove = result.current.toasts[1].id
    act(() => {
      result.current.removeToast(toRemove)
    })
    expect(result.current.toasts).toHaveLength(1)
    expect(result.current.toasts[0].message).toBe('keep me')
  })
})

describe('ToastContainer rendering', () => {
  function Trigger() {
    const t = useToast()
    return (
      <button onClick={() => t.success('hello world', 0)}>fire</button>
    )
  }

  it('renders nothing until a toast is added', () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>
    )
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('renders the toast message after firing', () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>
    )
    act(() => {
      screen.getByText('fire').click()
    })
    expect(screen.getByRole('alert')).toHaveTextContent('hello world')
  })
})
