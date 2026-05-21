import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  LoadingPage,
  LoadingSpinner,
  Skeleton,
  SkeletonCard,
  SkeletonList,
} from '../Loading'

describe('LoadingSpinner', () => {
  it('renders with default medium size', () => {
    const { container } = render(<LoadingSpinner />)
    const spinner = container.firstChild as HTMLElement
    expect(spinner).toHaveClass('animate-spin')
    expect(spinner).toHaveClass('w-8', 'h-8')
  })

  it('applies sm and lg size classes', () => {
    const { container, rerender } = render(<LoadingSpinner size="sm" />)
    expect(container.firstChild).toHaveClass('w-4', 'h-4')

    rerender(<LoadingSpinner size="lg" />)
    expect(container.firstChild).toHaveClass('w-12', 'h-12')
  })

  it('merges custom className', () => {
    const { container } = render(<LoadingSpinner className="custom-extra" />)
    expect(container.firstChild).toHaveClass('custom-extra')
  })
})

describe('LoadingPage', () => {
  it('renders the default message', () => {
    render(<LoadingPage />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders a custom message when provided', () => {
    render(<LoadingPage message="Fetching projects..." />)
    expect(screen.getByText('Fetching projects...')).toBeInTheDocument()
  })

  it('includes a large spinner', () => {
    const { container } = render(<LoadingPage />)
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('w-12', 'h-12')
  })
})

describe('Skeleton', () => {
  it('defaults to rectangular variant with rounded-lg', () => {
    const { container } = render(<Skeleton />)
    expect(container.firstChild).toHaveClass('rounded-lg')
  })

  it('applies circular variant', () => {
    const { container } = render(<Skeleton variant="circular" />)
    expect(container.firstChild).toHaveClass('rounded-full')
  })

  it('honors explicit width/height', () => {
    const { container } = render(<Skeleton width={120} height={40} />)
    const el = container.firstChild as HTMLElement
    expect(el.style.width).toBe('120px')
    expect(el.style.height).toBe('40px')
  })
})

describe('SkeletonCard', () => {
  it('renders a header line plus N body lines', () => {
    const { container } = render(<SkeletonCard lines={4} />)
    // 1 header + 4 lines = 5 skeleton blocks total
    const blocks = container.querySelectorAll('.animate-pulse')
    expect(blocks.length).toBe(5)
  })
})

describe('SkeletonList', () => {
  it('renders the requested number of cards', () => {
    const { container } = render(<SkeletonList count={3} />)
    // Each card has 1 header + 2 body lines = 3 skeleton blocks; 3 cards = 9
    const blocks = container.querySelectorAll('.animate-pulse')
    expect(blocks.length).toBe(9)
  })
})
