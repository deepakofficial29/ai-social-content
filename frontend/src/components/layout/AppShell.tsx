import { useQuery } from '@tanstack/react-query'
import {
  BarChart3, Clock3, FolderOpen, LayoutDashboard, Plus,
  SearchCheck, Sparkles,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../../api/client'

const navigation = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/create', label: 'Create', icon: Plus },
  { to: '/media', label: 'Media Library', icon: FolderOpen },
  { to: '/history', label: 'History', icon: Clock3 },
]

export default function AppShell() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health')
      return data.success
    },
  })

  return (
    <div className="min-h-screen bg-canvas">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r border-slate-200 bg-white md:flex md:flex-col">
        <div className="flex h-16 items-center gap-2 border-b border-slate-100 px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand text-white">
            <Sparkles size={18} />
          </div>
          <div>
            <div className="font-semibold text-slate-900">Caption Studio</div>
            <div className="text-xs text-slate-500">Evidence workspace</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                  isActive ? 'bg-blue-50 text-brand' : 'text-slate-600 hover:bg-slate-50'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
          <div className="px-3 pt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Workflow
          </div>
          <div className="flex items-center gap-3 px-3 py-2 text-sm text-slate-500">
            <SearchCheck size={18} />
            Evidence review
          </div>
          <div className="flex items-center gap-3 px-3 py-2 text-sm text-slate-500">
            <BarChart3 size={18} />
            Caption studio
          </div>
        </nav>
      </aside>

      <div className="md:pl-60">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur md:px-8">
          <div className="md:hidden font-semibold">Caption Studio</div>
          <div className="hidden text-sm text-slate-500 md:block">Creative workspace</div>
          <div className="flex items-center gap-2 text-sm">
            <span className={`h-2 w-2 rounded-full ${health.data ? 'bg-emerald-500' : health.isError ? 'bg-red-500' : 'bg-amber-400'}`} />
            {health.isLoading ? 'Checking backend' : health.data ? 'Backend connected' : 'Backend unavailable'}
          </div>
        </header>
        <main className="mx-auto max-w-[1440px] p-4 md:p-8">
          <Outlet />
        </main>
      </div>

      <nav className="fixed bottom-0 left-0 right-0 z-30 grid grid-cols-4 border-t border-slate-200 bg-white px-2 py-2 md:hidden">
        {navigation.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 rounded-lg py-1 text-xs ${isActive ? 'text-brand' : 'text-slate-500'}`
            }
          >
            <Icon size={18} />
            {label.split(' ')[0]}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
