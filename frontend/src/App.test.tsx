import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import { api } from './api/client'

vi.mock('./api/media', () => ({
  listCollections: vi.fn().mockResolvedValue([]),
}))
vi.mock('./api/generation', () => ({
  listGenerations: vi.fn().mockResolvedValue([]),
  getGenerationConfig: vi.fn().mockResolvedValue(undefined),
}))

describe('application navigation', () => {
  it('renders the dashboard and primary navigation', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { success: true } } as never)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('Grounded captions start with evidence')).toBeInTheDocument()
    expect(screen.getByText('Media Library')).toBeInTheDocument()
  })
})
