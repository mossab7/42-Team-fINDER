import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Navigation } from '../App'
import { api } from '../services/api'

vi.mock('../services/api', () => ({
  api: { matches: vi.fn() },
}))

const renderNavigation = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<MemoryRouter initialEntries={['/discover']}><QueryClientProvider client={queryClient}><Navigation /></QueryClientProvider></MemoryRouter>)
}

describe('Navigation match indicator', () => {
  beforeEach(() => vi.clearAllMocks())

  it('turns the Matches icon red when a match is waiting', async () => {
    vi.mocked(api.matches).mockResolvedValue({ items: [{
      id: 9,
      project_id: 42,
      project_name: 'ft_transcendence',
      created_at: '2026-11-22T18:00:00Z',
      profile: { user_id: 7, login: 'ada', display_name: 'Ada Lovelace', biography: '', skills: [], languages: [], availability: '', working_hours: '', visible: true },
    }] })

    renderNavigation()

    expect(await screen.findByRole('link', { name: 'Matches, 1 waiting' })).toBeInTheDocument()
    expect(screen.getByTestId('matches-nav-icon')).toHaveClass('text-brand-pink')
    expect(screen.getByTestId('matches-nav-icon')).toHaveAttribute('fill', 'currentColor')
  })

  it('leaves the Matches icon neutral when there are no matches', async () => {
    vi.mocked(api.matches).mockResolvedValue({ items: [] })

    renderNavigation()

    expect(await screen.findByRole('link', { name: 'Matches' })).toBeInTheDocument()
    expect(screen.getByTestId('matches-nav-icon')).not.toHaveClass('text-brand-pink')
    expect(screen.getByTestId('matches-nav-icon')).toHaveAttribute('fill', 'none')
  })
})
