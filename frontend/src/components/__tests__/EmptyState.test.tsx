import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import EmptyState, {
  ErrorEmptyState,
  NoAgentsEmptyState,
  NoSearchResultsEmptyState,
  OfflineEmptyState,
} from '../EmptyState'

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="Nothing here" description="Try creating one" />)
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
    expect(screen.getByText('Try creating one')).toBeInTheDocument()
  })

  it('renders an icon when provided', () => {
    render(<EmptyState title="x" icon={<span data-testid="icon">!</span>} />)
    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('renders a button action and fires onClick', () => {
    const onClick = vi.fn()
    render(<EmptyState title="x" action={{ label: 'Create', onClick }} />)
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('renders a Link action when `to` is provided', () => {
    render(
      <MemoryRouter>
        <EmptyState title="x" action={{ label: 'Go', to: '/somewhere' }} />
      </MemoryRouter>
    )
    const link = screen.getByRole('link', { name: 'Go' })
    expect(link).toHaveAttribute('href', '/somewhere')
  })

  it('has role=status and an aria-label matching the title', () => {
    render(<EmptyState title="No Data" />)
    const wrapper = screen.getByRole('status')
    expect(wrapper).toHaveAttribute('aria-label', 'No Data')
  })
})

describe('Preset empty states', () => {
  it('NoAgentsEmptyState fires the create callback', () => {
    const onCreate = vi.fn()
    render(<NoAgentsEmptyState onCreateClick={onCreate} />)
    fireEvent.click(screen.getByRole('button', { name: /create agent/i }))
    expect(onCreate).toHaveBeenCalledTimes(1)
  })

  it('NoSearchResultsEmptyState shows the query in the description', () => {
    render(<NoSearchResultsEmptyState query="cyberpunk" />)
    expect(screen.getByText(/cyberpunk/)).toBeInTheDocument()
  })

  it('NoSearchResultsEmptyState hides the clear button when no handler is given', () => {
    render(<NoSearchResultsEmptyState query="x" />)
    expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument()
  })

  it('ErrorEmptyState renders retry button when handler provided', () => {
    const onRetry = vi.fn()
    render(<ErrorEmptyState onRetry={onRetry} />)
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('OfflineEmptyState shows the offline title', () => {
    render(<OfflineEmptyState />)
    expect(screen.getByText(/offline/i)).toBeInTheDocument()
  })
})
