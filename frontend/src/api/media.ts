import { api } from './client'
import type { ApiResponse, CollectionSummary, MediaItem, UploadResult } from '../types'

export async function uploadMedia(
  files: File[],
  onProgress?: (percent: number) => void,
  signal?: AbortSignal,
) {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const { data } = await api.post<ApiResponse<UploadResult>>('/media/upload', form, {
    signal,
    onUploadProgress: (event) => {
      if (event.total) onProgress?.(Math.round((event.loaded / event.total) * 100))
    },
  })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function listCollections() {
  const { data } = await api.get<ApiResponse<CollectionSummary[]>>('/media/collections')
  if (!data.success) throw new Error(data.message)
  return data.data || []
}

export async function getMedia(mediaId: string) {
  const { data } = await api.get<ApiResponse<MediaItem>>(`/media/${mediaId}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}
