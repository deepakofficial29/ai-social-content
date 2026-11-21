import { api } from './client'
import type {
  ApiResponse,
  GenerationConfig,
  GenerationRequest,
  GenerationPlan,
} from '../types'

export async function saveGenerationConfig(mediaId: string, config: GenerationConfig) {
  const { data } = await api.post<ApiResponse<GenerationConfig>>(
    `/generation/config/${mediaId}`,
    config,
  )
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function getGenerationConfig(mediaId: string) {
  const { data } = await api.get<ApiResponse<GenerationConfig>>(`/generation/config/${mediaId}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createStrategy(mediaId: string, config: GenerationConfig) {
  const { data } = await api.post<ApiResponse<GenerationPlan>>(
    `/generation/strategy/${mediaId}`,
    config,
  )
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function generateCaptions(mediaId: string, config: GenerationConfig) {
  const { data } = await api.post<ApiResponse<GenerationRequest>>(
    `/generation/captions/${mediaId}`,
    config,
  )
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function regenerateCaptions(generationId: string) {
  const { data } = await api.post<ApiResponse<GenerationRequest>>(
    `/generation/${generationId}/regenerate`,
  )
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function listGenerations() {
  const { data } = await api.get<ApiResponse<GenerationRequest[]>>('/generation')
  if (!data.success) throw new Error(data.message)
  return data.data || []
}

export async function getGeneration(generationId: string) {
  const { data } = await api.get<ApiResponse<GenerationRequest>>(`/generation/${generationId}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}
