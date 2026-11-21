import { useRef, useState } from 'react'
import { ArrowDown, ArrowUp, UploadCloud, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { uploadMedia } from '../api/media'
import { runUnderstanding } from '../api/evidence'

const allowed = new Set([
  'image/jpeg', 'image/png', 'image/webp',
  'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm',
  'audio/wav', 'audio/mpeg', 'audio/mp4', 'audio/aac', 'audio/x-m4a',
])
const maxSize = 100 * 1024 * 1024

export default function Create() {
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadController, setUploadController] = useState<AbortController>()

  const addFiles = (incoming: FileList | File[]) => {
    const next = Array.from(incoming)
    const valid: File[] = []
    for (const file of next) {
      if (!allowed.has(file.type)) {
        setError(`${file.name} is not a supported media type.`)
        continue
      }
      if (file.size > maxSize) {
        setError(`${file.name} exceeds the 100 MB upload limit.`)
        continue
      }
      valid.push(file)
    }
    setFiles((current) => [...current, ...valid])
  }

  const move = (index: number, direction: -1 | 1) => {
    setFiles((current) => {
      const target = index + direction
      if (target < 0 || target >= current.length) return current
      const reordered = [...current]
      ;[reordered[index], reordered[target]] = [reordered[target], reordered[index]]
      return reordered
    })
  }

  const upload = async () => {
    if (!files.length) {
      setError('Select at least one media file.')
      return
    }
    setBusy(true)
    setProgress(0)
    const controller = new AbortController()
    setUploadController(controller)
    setError('')
    try {
      const result = await uploadMedia(files, setProgress, controller.signal)
      await runUnderstanding(result.collection_id)
      navigate(`/evidence/${result.collection_id}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Upload failed.')
    } finally {
      setBusy(false)
      setUploadController(undefined)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Create from media</h1>
        <p className="mt-1 text-sm text-slate-500">Upload one or more supported media files. Reorder carousel images before upload.</p>
      </div>

      <section
        className="panel flex min-h-52 cursor-pointer flex-col items-center justify-center border-dashed p-8 text-center"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          addFiles(event.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          className="hidden"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.avi,.mkv,.webm,.wav,.mp3,.m4a,.aac"
          onChange={(event) => event.target.files && addFiles(event.target.files)}
        />
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-brand">
          <UploadCloud size={23} />
        </div>
        <div className="mt-3 font-semibold text-slate-800">Drop files here or browse</div>
        <div className="mt-1 text-xs text-slate-500">Images, video or audio · 100 MB per file</div>
      </section>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {files.length > 0 && (
        <section className="panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Selected files · {files.length}</h2>
            <button type="button" className="text-sm text-slate-500 hover:text-slate-800" onClick={() => setFiles([])}>Clear all</button>
          </div>
          <div className="space-y-2">
            {files.map((file, index) => (
              <div key={`${file.name}-${file.lastModified}`} className="flex items-center gap-3 rounded-lg border border-slate-200 p-3">
                {file.type.startsWith('image/') ? (
                  <img src={URL.createObjectURL(file)} alt="" className="h-14 w-14 rounded-md object-cover" />
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-md bg-slate-100 text-xs text-slate-500">MEDIA</div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-slate-800">{file.name}</div>
                  <div className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB · {file.type || 'unknown type'}</div>
                </div>
                {files.length > 1 && (
                  <>
                    <button type="button" className="btn-secondary px-2" aria-label="Move up" onClick={() => move(index, -1)}><ArrowUp size={15} /></button>
                    <button type="button" className="btn-secondary px-2" aria-label="Move down" onClick={() => move(index, 1)}><ArrowDown size={15} /></button>
                  </>
                )}
                <button type="button" className="btn-secondary px-2" aria-label="Remove" onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}><X size={15} /></button>
              </div>
            ))}
          </div>
          <div className="mt-5 flex justify-end">
            {busy && (
              <button type="button" className="btn-secondary mr-2" onClick={() => uploadController?.abort()}>
                Cancel
              </button>
            )}
            <button type="button" className="btn-primary" disabled={busy} onClick={upload}>
              {busy ? `Uploading ${progress}%` : 'Upload and build evidence'}
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
