import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Copy, RefreshCw } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { generateCaptions, getGenerationConfig, regenerateCaptions, saveGenerationConfig } from '../api/generation'
import { getEvidence } from '../api/evidence'
import type { GenerationConfig, GenerationRequest } from '../types'
import { ErrorState, LoadingState } from '../components/common/States'

const defaults: GenerationConfig = {
  platform: 'instagram',
  objective: 'engagement',
  audience: 'general',
  tone: 'friendly',
  language: 'english',
  caption_length: 'medium',
  emoji_preference: 'minimal',
  hashtag_preference: 'relevant',
  cta_enabled: true,
  keywords_to_include: [],
  words_or_claims_to_avoid: [],
  variant_count: 3,
}

export default function CaptionStudio() {
  const { collectionId = '' } = useParams()
  const evidence = useQuery({ queryKey: ['evidence', collectionId], queryFn: () => getEvidence(collectionId), enabled: !!collectionId })
  const savedConfig = useQuery({
    queryKey: ['generation-config', collectionId],
    queryFn: () => getGenerationConfig(collectionId),
    enabled: !!collectionId,
  })
  const [config, setConfig] = useState<GenerationConfig>(defaults)
  const [request, setRequest] = useState<GenerationRequest>()
  const [copied, setCopied] = useState('')

  useEffect(() => {
    if (savedConfig.isSuccess && savedConfig.data) setConfig(savedConfig.data)
  }, [savedConfig.isSuccess, savedConfig.data])

  const saveAndGenerate = useMutation({
    mutationFn: async () => {
      await saveGenerationConfig(collectionId, { ...config, media_id: collectionId })
      return generateCaptions(collectionId, { ...config, media_id: collectionId })
    },
    onSuccess: setRequest,
  })
  const regenerate = useMutation({
    mutationFn: (generationId: string) => regenerateCaptions(generationId),
    onSuccess: setRequest,
  })

  if (evidence.isLoading || savedConfig.isLoading) return <LoadingState label="Loading Caption Studio…" />
  if (evidence.isError) return <ErrorState error={evidence.error as Error} onRetry={() => evidence.refetch()} />

  const set = (key: keyof GenerationConfig, value: unknown) =>
    setConfig((current) => ({ ...current, [key]: value }))

  return (
    <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
      <aside className="panel h-fit p-5">
        <h1 className="text-xl font-semibold text-slate-950">Caption settings</h1>
        <div className="mt-5 space-y-4">
          <div><label className="label">Platform</label><select className="field" value={config.platform} onChange={(e) => set('platform', e.target.value)}>
            {['instagram','linkedin','x','facebook','youtube','threads','custom'].map((v) => <option key={v}>{v}</option>)}
          </select></div>
          <div><label className="label">Objective</label><select className="field" value={config.objective} onChange={(e) => set('objective', e.target.value)}>
            {['engagement','brand_awareness','education','promotion','storytelling','community_building','product_showcase','entertainment','professional_communication','custom'].map((v) => <option key={v}>{v}</option>)}
          </select></div>
          <div><label className="label">Audience</label><select className="field" value={config.audience} onChange={(e) => set('audience', e.target.value)}>
            {['general','students','professionals','creators','customers','business_owners','custom'].map((v) => <option key={v}>{v}</option>)}
          </select></div>
          <div><label className="label">Tone</label><select className="field" value={config.tone} onChange={(e) => set('tone', e.target.value)}>
            {['professional','friendly','conversational','humorous','inspirational','educational','persuasive','minimalist','storytelling','custom'].map((v) => <option key={v}>{v}</option>)}
          </select></div>
          <div><label className="label">Language</label><select className="field" value={config.language} onChange={(e) => set('language', e.target.value)}>
            {['english','kannada','hindi','tamil','telugu','malayalam','hinglish','custom'].map((v) => <option key={v}>{v}</option>)}
          </select></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Length</label><select className="field" value={config.caption_length} onChange={(e) => set('caption_length', e.target.value)}>{['short','medium','long'].map((v) => <option key={v}>{v}</option>)}</select></div>
            <div><label className="label">Emojis</label><select className="field" value={config.emoji_preference} onChange={(e) => set('emoji_preference', e.target.value)}>{['none','minimal','moderate','expressive'].map((v) => <option key={v}>{v}</option>)}</select></div>
          </div>
          <div><label className="label">Hashtags</label><select className="field" value={config.hashtag_preference} onChange={(e) => set('hashtag_preference', e.target.value)}>{['disabled','minimal','relevant','custom'].map((v) => <option key={v}>{v}</option>)}</select></div>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={config.cta_enabled} onChange={(e) => set('cta_enabled', e.target.checked)} />Include CTA</label>
          <div><label className="label">Brand name</label><input className="field" value={config.brand_name || ''} onChange={(e) => set('brand_name', e.target.value || undefined)} /></div>
          <div><label className="label">Brand voice</label><textarea className="field min-h-20" value={config.brand_voice_description || ''} onChange={(e) => set('brand_voice_description', e.target.value)} /></div>
          <div><label className="label">Additional instructions</label><textarea className="field min-h-20" value={config.additional_instructions || ''} onChange={(e) => set('additional_instructions', e.target.value)} /></div>
          <div><label className="label">Variants</label><input className="field" type="number" min={1} max={5} value={config.variant_count} onChange={(e) => set('variant_count', Number(e.target.value))} /></div>
          {saveAndGenerate.isError && <ErrorState error={saveAndGenerate.error as Error} />}
          <button className="btn-primary w-full" type="button" disabled={saveAndGenerate.isPending} onClick={() => saveAndGenerate.mutate()}>
            {saveAndGenerate.isPending ? 'Generating…' : 'Generate grounded captions'}
          </button>
        </div>
      </aside>

      <section className="space-y-4">
        <div className="panel p-5">
          <div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Caption variants</h2><p className="mt-1 text-sm text-slate-500">{evidence.data?.evidence_items.length || 0} evidence items available</p></div>{request && <button className="btn-secondary" type="button" onClick={() => regenerate.mutate(request.request_id)}><RefreshCw size={15} />Regenerate</button>}</div>
        </div>
        {!request ? (
          <div className="panel flex min-h-80 items-center justify-center text-sm text-slate-500">Configure the settings and generate variants.</div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {request.variants.map((variant) => {
              const grounding = request.grounding[variant.variant_id]
              const quality = request.quality[variant.variant_id]
              return (
                <article key={variant.variant_id} className="panel p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div><div className="text-xs font-semibold uppercase tracking-wide text-brand">{variant.approach}</div><h3 className="mt-1 font-semibold text-slate-900">{variant.content_angle}</h3></div>
                    <button className="btn-secondary px-2.5" type="button" aria-label="Copy caption" onClick={async () => { await navigator.clipboard.writeText(variant.caption_text); setCopied(variant.variant_id) }}><Copy size={15} /></button>
                  </div>
                  <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-800">{variant.caption_text}</p>
                  {variant.hashtags.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{variant.hashtags.map((tag) => <span key={tag} className="rounded bg-blue-50 px-2 py-1 text-xs text-brand">{tag}</span>)}</div>}
                  {variant.cta && <div className="mt-3 text-sm font-medium text-slate-700">CTA: {variant.cta}</div>}
                  <div className={`mt-4 rounded-lg px-3 py-2 text-sm ${grounding?.is_verified ? 'border border-emerald-200 bg-emerald-50 text-emerald-800' : 'border border-amber-200 bg-amber-50 text-amber-900'}`}>
                    <strong>{grounding?.is_verified ? 'Verified by evidence' : 'Not verified'}</strong>
                    {!grounding?.is_verified && grounding?.unsupported_claims.length > 0 && <div className="mt-1 text-xs">Unsupported: {grounding.unsupported_claims.join('; ')}</div>}
                    {grounding?.corrected_caption && <div className="mt-2 text-xs">Corrected: {grounding.corrected_caption}</div>}
                  </div>
                  {quality && <details className="mt-3 text-sm"><summary className="cursor-pointer font-medium text-slate-700">Quality feedback</summary><div className="mt-2 space-y-1 text-xs text-slate-600">{quality.strengths.map((item) => <p key={item}>Strength: {item}</p>)}{quality.weaknesses.map((item) => <p key={item}>Review: {item}</p>)}</div></details>}
                  <div className="mt-3 text-xs text-slate-500">Evidence: {variant.evidence_ids.join(', ') || 'none'}</div>
                  {copied === variant.variant_id && <div className="mt-2 text-xs font-medium text-emerald-700">Copied</div>}
                </article>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
