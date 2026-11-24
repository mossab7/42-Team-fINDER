import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../services/api'
import { Discover } from './Matchmaking'

vi.mock('../services/api', () => ({
  api: {
    discoverProjects: vi.fn(),
    candidates: vi.fn(),
    swipe: vi.fn(),
  },
}))

describe('Discover match celebration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.discoverProjects).mockResolvedValue({ items: [
      { id: 42, name: 'ft_transcendence', slug: 'ft-transcendence', maximum_team_size: 5, subscription_status: 'subscribed' },
      { id: 84, name: 'webserv', slug: 'webserv', maximum_team_size: 3, subscription_status: 'eligible' },
    ] })
    vi.mocked(api.candidates).mockResolvedValue({ scan_id: 'scan-1', items: [{ user_id: 7, login: 'ada', display_name: 'Ada Lovelace', image_url: null, profile_url: 'https://profile.intra.42.fr/users/ada', campus_name: '1337', level: 8.5, biography: '', skills: [], languages: [], availability: '', working_hours: '', github_url: null, visible: true }] })
    vi.mocked(api.swipe).mockResolvedValue({ matched: true, match_id: 99 })
  })

  it('celebrates when a right swipe is reciprocal', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
    render(<MemoryRouter><QueryClientProvider client={queryClient}><Discover /></QueryClientProvider></MemoryRouter>)

    fireEvent.click(await screen.findByRole('button', { name: 'Interested' }))

    expect(await screen.findByRole('heading', { name: /it’s a match/i })).toBeInTheDocument()
    expect(screen.getByText(/Ada Lovelace/)).toBeInTheDocument()
    expect(screen.getByText(/already swiped right on you too/i)).toBeInTheDocument()
    await waitFor(() => expect(api.swipe).toHaveBeenCalledWith(7, 42, 'right'))
  })

  it('shows eligible projects but requires an Intra subscription before matching', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
    render(<MemoryRouter><QueryClientProvider client={queryClient}><Discover /></QueryClientProvider></MemoryRouter>)

    await waitFor(() => expect(api.candidates).toHaveBeenCalledWith(42))
    fireEvent.click(screen.getByRole('button', { name: 'Project' }))
    fireEvent.click(screen.getByRole('option', { name: /webserv/i }))

    expect(await screen.findByRole('heading', { name: /subscribe to webserv first/i })).toBeInTheDocument()
    expect(screen.getByText(/matching is available only after you subscribe/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /subscribe on 42 intra/i })).toHaveAttribute('href', 'https://projects.intra.42.fr/projects/webserv')
    expect(api.candidates).not.toHaveBeenCalledWith(84)
  })
})
