import { api } from './client'
import type { ApiResponse, EvidencePackage } from '../types'

export async function getEvidence(collectionId: string) {
  const { data } = await api.get<ApiResponse<EvidencePackage>>(`/evidence/${collectionId}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function rebuildEvidence(collectionId: string) {
  const { data } = await api.post<ApiResponse<EvidencePackage>>(`/evidence/${collectionId}/rebuild`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function runUnderstanding(collectionId: string) {
  const { data } = await api.post(`/understanding/${collectionId}`)
  if (!data.success) throw new Error(data.message)
  return data
}
