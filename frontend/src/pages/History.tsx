import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listGenerations } from '../api/generation'
import { EmptyState, ErrorState, LoadingState } from '../components/common/States'

export default function History() {
  const query = useQuery({ queryKey: ['generations'], queryFn: listGenerations })
  if (query.isLoading) return <LoadingState label="Loading generation history…" />
  if (query.isError) return <ErrorState error={query.error as Error} onRetry={() => query.refetch()} />

  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-semibold text-slate-950">Generation History</h1><p className="mt-1 text-sm text-slate-500">Persisted generation requests and their evidence package versions.</p></div>
      {!query.data?.length ? (
        <EmptyState title="No generation history" description="Generated captions will appear here without replacing earlier requests." />
      ) : (
        <div className="space-y-4">
          {query.data.map((request) => (
            <article key={request.request_id} className="panel p-5">
              <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{request.config.platform} · {request.config.tone} · Evidence v{request.evidence_package_version}</div>
                  <h2 className="mt-1 font-semibold text-slate-900">{request.variants.length} caption variants</h2>
                  <p className="mt-1 text-xs text-slate-500">{new Date(request.created_at).toLocaleString()} · {request.provider}/{request.model_id}</p>
                </div>
                <Link className="btn-secondary" to={`/evidence/${request.collection_id}`}>Inspect evidence</Link>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-3">
                {request.variants.map((variant) => {
                  const grounding = request.grounding[variant.variant_id]
                  const quality = request.quality[variant.variant_id]
                  return (
                    <div key={variant.variant_id} className="rounded-lg border border-slate-200 p-4">
                      <div className="text-xs font-semibold uppercase text-brand">{variant.approach}</div>
                      <p className="mt-2 line-clamp-4 text-sm text-slate-800">{variant.caption_text}</p>
                      <div className="mt-3 text-xs"><span className={grounding?.is_verified ? 'text-emerald-700' : 'text-amber-700'}>{grounding?.status || 'not validated'}</span></div>
                      {quality && <div className="mt-2 text-xs text-slate-500">{quality.strengths.length} strengths · {quality.weaknesses.length} reviews</div>}
                      <div className="mt-2 text-xs text-slate-400">Evidence: {variant.evidence_ids.join(', ') || 'none'}</div>
                    </div>
                  )
                })}
              </div>
              {request.warnings.length > 0 && <div className="mt-3 text-xs text-amber-700">Warnings: {request.warnings.join('; ')}</div>}
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
