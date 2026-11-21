import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getEvidence, rebuildEvidence } from '../api/evidence'
import { EmptyState, ErrorState, LoadingState } from '../components/common/States'

export default function EvidenceReview() {
  const { collectionId = '' } = useParams()
  const query = useQuery({ queryKey: ['evidence', collectionId], queryFn: () => getEvidence(collectionId), enabled: !!collectionId })
  const rebuild = useMutation({ mutationFn: () => rebuildEvidence(collectionId), onSuccess: () => query.refetch() })

  if (query.isLoading) return <LoadingState label="Loading evidence package…" />
  if (query.isError) return <ErrorState error={query.error as Error} onRetry={() => query.refetch()} />
  if (!query.data) return <EmptyState title="Evidence unavailable" description="Build an evidence package before reviewing this collection." />

  const packageData = query.data
  const direct = packageData.evidence_items.filter((item) => item.observation_type === 'direct_observation')
  const interpreted = packageData.evidence_items.filter((item) => item.observation_type !== 'direct_observation')

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950">Evidence Review</h1>
          <p className="mt-1 text-sm text-slate-500">{packageData.collection_type} collection · {packageData.evidence_items.length} evidence items</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" type="button" disabled={rebuild.isPending} onClick={() => rebuild.mutate()}><RefreshCw size={15} />Rebuild</button>
          <Link className="btn-primary" to={`/studio/${collectionId}`}>Open Caption Studio</Link>
        </div>
      </div>

      {packageData.conflicts.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <div className="flex items-center gap-2 font-semibold"><AlertTriangle size={17} />Potential contradictions detected</div>
          <div className="mt-2 space-y-1">{packageData.conflicts.map((conflict) => <p key={conflict.conflict_id}>{conflict.description}</p>)}</div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
        <section className="panel p-5">
          <h2 className="font-semibold text-slate-900">Unified evidence</h2>
          <div className="mt-4 grid gap-3">
            {packageData.evidence_items.map((item) => (
              <article key={item.evidence_id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {item.observation_type === 'direct_observation'
                      ? <CheckCircle2 size={16} className="text-emerald-600" />
                      : <AlertTriangle size={16} className="text-amber-600" />}
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.category}</span>
                  </div>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{item.source.modality}</span>
                </div>
                <p className="mt-2 text-sm font-medium text-slate-900">{item.value}</p>
                {item.uncertainty_note && <p className="mt-2 text-xs text-amber-700">Uncertain: {item.uncertainty_note}</p>}
                <div className="mt-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
                  Evidence ID: {item.evidence_id}<br />
                  Asset: {item.source.media_id}
                  {typeof item.source.frame_index === 'number' && ` · Frame ${item.source.frame_index}`}
                  {typeof item.source.video_start_seconds === 'number' && ` · ${item.source.video_start_seconds}s`}
                  {typeof item.source.audio_start_seconds === 'number' && ` · ${item.source.audio_start_seconds}s`}
                  {item.source.provider && ` · ${item.source.provider}/${item.source.model_id}`}
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="space-y-5">
          <section className="panel p-5">
            <h2 className="font-semibold text-slate-900">Grounded summary</h2>
            {packageData.content_summary ? (
              <pre className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">{JSON.stringify(packageData.content_summary, null, 2)}</pre>
            ) : <p className="mt-2 text-sm text-slate-500">No summary is available.</p>}
          </section>
          <section className="panel p-5">
            <h2 className="font-semibold text-slate-900">Quality</h2>
            {packageData.quality ? <pre className="mt-3 whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(packageData.quality, null, 2)}</pre> : <p className="mt-2 text-sm text-slate-500">No quality assessment.</p>}
          </section>
          <section className="panel p-5">
            <h2 className="font-semibold text-slate-900">Evidence groups</h2>
            <p className="mt-3 text-sm text-slate-600"><strong>{direct.length}</strong> direct observations</p>
            <p className="mt-1 text-sm text-slate-600"><strong>{interpreted.length}</strong> interpretations or inferences</p>
            <p className="mt-1 text-sm text-slate-600"><strong>{packageData.cross_modal_relationships.length}</strong> relationships</p>
          </section>
        </aside>
      </div>
    </div>
  )
}
