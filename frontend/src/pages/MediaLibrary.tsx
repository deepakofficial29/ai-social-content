import { useQuery } from '@tanstack/react-query'
import { ArrowRight, FolderOpen, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listCollections } from '../api/media'
import { EmptyState, ErrorState, LoadingState } from '../components/common/States'

export default function MediaLibrary() {
  const query = useQuery({ queryKey: ['collections'], queryFn: listCollections })
  if (query.isLoading) return <LoadingState label="Loading media library…" />
  if (query.isError) return <ErrorState error={query.error as Error} onRetry={() => query.refetch()} />

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-semibold text-slate-950">Media Library</h1><p className="mt-1 text-sm text-slate-500">Uploaded collections and their processing state.</p></div>
        <Link className="btn-primary" to="/create"><Plus size={17} />Upload media</Link>
      </div>
      {!query.data?.length ? (
        <EmptyState title="No uploaded media" description="Create a collection to begin evidence review." action={<Link className="btn-primary" to="/create">Upload media</Link>} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {query.data.map((collection) => (
            <article key={collection.collection_id} className="panel p-5">
              <div className="flex items-start justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-100 text-slate-600"><FolderOpen size={20} /></div>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">{collection.collection_type}</span>
              </div>
              <h2 className="mt-4 font-semibold text-slate-900">{collection.media.length} asset{collection.media.length === 1 ? '' : 's'}</h2>
              <p className="mt-1 text-sm text-slate-500">{new Date(collection.created_at).toLocaleString()}</p>
              <div className="mt-4 flex flex-col gap-2">
                <Link className="btn-secondary" to={`/evidence/${collection.collection_id}`}>Review evidence<ArrowRight size={15} /></Link>
                <Link className="btn-primary" to={`/studio/${collection.collection_id}`}>Open Caption Studio</Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
