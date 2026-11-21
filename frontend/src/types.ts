export interface ApiResponse<T> {
  success: boolean
  message: string
  data?: T
  error?: { code: string; details: Record<string, unknown> }
}

export interface MediaItem {
  media_id: string
  filename: string
  media_type: 'image' | 'video' | 'audio'
  file_size: number
  metadata?: Record<string, unknown>
  processing_status: string
  sequence_index: number
}

export interface CollectionSummary {
  collection_id: string
  collection_type: string
  created_at: string
  media: MediaItem[]
}

export interface UploadResult {
  collection_id: string
  media: MediaItem[]
}

export interface EvidenceSource {
  media_id: string
  collection_id: string
  media_type: string
  modality: string
  image_index?: number
  video_start_seconds?: number
  video_end_seconds?: number
  frame_index?: number
  audio_start_seconds?: number
  audio_end_seconds?: number
  provider: string
  model_id: string
}

export interface EvidenceItem {
  evidence_id: string
  category: string
  observation_type: 'direct_observation' | 'interpretation' | 'inference'
  value: string
  source: EvidenceSource
  confidence?: string
  uncertainty_note?: string
  supporting_evidence_ids: string[]
  raw_provider_value?: string
}

export interface EvidencePackage {
  package_id: string
  schema_version: string
  collection_id: string
  collection_type: string
  asset_ids: string[]
  evidence_items: EvidenceItem[]
  cross_modal_relationships: Array<{
    relationship_id: string
    relationship_type: string
    evidence_ids: string[]
    description: string
  }>
  conflicts: Array<{
    conflict_id: string
    conflicting_evidence_ids: string[]
    description: string
    source_references: string[]
    explanation: string
    resolution_status: string
  }>
  quality?: Record<string, unknown>
  content_summary?: Record<string, unknown>
  processing_status: string
  warnings: string[]
  providers_used: string[]
  package_version?: number
}

export interface GenerationConfig {
  media_id?: string
  platform: string
  objective: string
  audience: string
  custom_audience_description?: string
  tone: string
  custom_tone_description?: string
  language: string
  custom_language_description?: string
  caption_length: 'short' | 'medium' | 'long'
  emoji_preference: 'none' | 'minimal' | 'moderate' | 'expressive'
  hashtag_preference: 'disabled' | 'minimal' | 'relevant' | 'custom'
  cta_enabled: boolean
  brand_voice_description?: string
  brand_name?: string
  keywords_to_include: string[]
  words_or_claims_to_avoid: string[]
  additional_instructions?: string
  variant_count: number
}

export interface CaptionVariant {
  variant_id: string
  approach: string
  caption_text: string
  platform: string
  tone: string
  content_angle: string
  hashtags: string[]
  cta?: string
  evidence_ids: string[]
  provider: string
  model_id: string
}

export interface GroundingResult {
  grounding_id: string
  status: 'verified' | 'unverified' | 'contradicted' | string
  is_verified: boolean
  claims: Array<{ claim: string; classification: string; evidence_ids: string[]; explanation: string }>
  unsupported_claims: string[]
  contradicted_claims: string[]
  correction_attempted: boolean
  corrected_caption?: string
}

export interface QualityResult {
  grounding_separate_status: string
  strengths: string[]
  weaknesses: string[]
  criteria: Record<string, string>
}

export interface GenerationPlan {
  plan_id: string
  main_content_angle: string
  key_message: string
  audience_relevance: string
  recommended_structure: string[]
  tone_instructions: string
  platform_considerations: string[]
  supported_facts: string[]
  evidence_ids: string[]
  prohibited_claims: string[]
  created_at: string
}

export interface GenerationRequest {
  request_id: string
  collection_id: string
  evidence_package_id: string
  evidence_package_version: number
  config: GenerationConfig
  plan: Record<string, unknown>
  variants: CaptionVariant[]
  grounding: Record<string, GroundingResult>
  quality: Record<string, QualityResult>
  provider: string
  model_id: string
  status: string
  warnings: string[]
  created_at: string
}
