import { useQuery } from '@tanstack/react-query'
import { ArrowRight, FolderOpen, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listCollections } from '../api/media'
import { listGenerations } from '../api/generation'
import { EmptyState, ErrorState, LoadingState } from '../components/common/States'

export default function Dashboard() {
  const collections = useQuery({ queryKey: ['collections'], queryFn: listCollections })
  const generations = useQuery({ queryKey: ['generations'], queryFn: listGenerations })

  if (collections.isLoading || generations.isLoading) return <LoadingState label="Loading workspace…" />
  if (collections.isError) return <ErrorState error={collections.error as Error} onRetry={() => collections.refetch()} />
  if (generations.isError) return <ErrorState error={generations.error as Error} onRetry={() => generations.refetch()} />

  return (
    <div className="space-y-6">
      <section className="panel px-6 py-7 md:px-8">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div>
            <div className="text-sm font-medium text-brand">Creative workspace</div>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Grounded captions start with evidence</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-500">Upload media, review what the system observed, then create and inspect caption variants.</p>
          </div>
          <Link className="btn-primary" to="/create"><Plus size={17} />Start creating</Link>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Recent media</h2>
            <Link className="text-sm font-medium text-brand" to="/media">View library</Link>
          </div>
          {collections.data?.length ? (
            <div className="mt-4 space-y-2">
              {collections.data.slice(0, 5).map((collection) => (
                <Link key={collection.collection_id} to={`/evidence/${collection.collection_id}`}
                  className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-3 hover:bg-slate-50">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-600"><FolderOpen size={17} /></div>
                    <div><div className="text-sm font-medium text-slate-800">{collection.collection_type} collection</div><div className="text-xs text-slate-500">{collection.media.length} asset(s)</div></div>
                  </div>
                  <ArrowRight size={16} className="text-slate-400" />
                </Link>
              ))}
            </div>
          ) : <div className="mt-4"><EmptyState title="No media yet" description="Upload media to start an evidence review." /></div>}
        </section>

        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Recent generations</h2>
            <Link className="text-sm font-medium text-brand" to="/history">View history</Link>
          </div>
          {generations.data?.length ? (
            <div className="mt-4 space-y-2">
              {generations.data.slice(0, 5).map((request) => (
                <Link key={request.request_id} to={`/history`}
                  className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-3 hover:bg-slate-50">
                  <div><div className="text-sm font-medium text-slate-800">{request.variants.length} variants</div><div className="text-xs text-slate-500">{request.config.platform} · {new Date(request.created_at).toLocaleString()}</div></div>
                  <ArrowRight size={16} className="text-slate-400" />
                </Link>
              ))}
            </div>
          ) : <div className="mt-4"><EmptyState title="No generations yet" description="Complete evidence review and generate your first captions." /></div>}
        </section>
      </div>
    </div>
  )
}
