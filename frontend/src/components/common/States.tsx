import type { ReactNode } from 'react'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="panel flex min-h-48 items-center justify-center text-sm text-slate-500">
      {label}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <div className="font-semibold">Request failed</div>
      <div className="mt-1">{error.message}</div>
      {onRetry && (
        <button className="btn-secondary mt-3" type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, description, action }: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="panel flex min-h-64 flex-col items-center justify-center px-6 text-center">
      <div className="text-lg font-semibold text-slate-900">{title}</div>
      <p className="mt-2 max-w-md text-sm text-slate-500">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
