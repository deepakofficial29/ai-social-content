# Model Research — Multimodal AI Caption Generator

**Research date:** 2025  
**Phase:** 2.1 — Research and Architecture Planning  
**Status:** No models integrated. Research only.

---

## 1. Image Understanding Models

### 1.1 Evaluation Criteria

For this platform the relevant criteria are:

- Accuracy on real-world social media content (products, people, events, food, travel)
- Multi-image input support (carousel posts require reasoning across ordered images)
- OCR quality (text in images is common in Indian social media content)
- Contextual reasoning (understanding what is happening, not just labelling objects)
- Fine-detail recognition (brand logos, product labels, facial expressions)
- API availability and reliability
- Pricing per image
- Latency (acceptable for a web upload flow: under 10 seconds per image)
- Data privacy and residency options
- Rate limits at MVP scale

### 1.2 Models Evaluated

#### Google Gemini 1.5 Pro / Gemini 2.0 Flash

**Source:** https://ai.google.dev/gemini-api/docs  
**Model versions available as of research date:** gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp

- Accepts up to 3,600 images per request in a single context window (1M tokens)
- Native multi-image reasoning — can compare, sequence, and reason across images
- Strong OCR including handwritten text and stylised fonts
- Supports video natively (up to 1 hour via File API)
- Supports audio natively
- Available via Google AI Studio (free tier) and Vertex AI (enterprise)
- Pricing (Gemini 1.5 Flash, as of research date): ~$0.075 per 1M input tokens; images counted as tokens (~258 tokens per image at standard resolution)
- Pricing (Gemini 1.5 Pro): ~$3.50 per 1M input tokens
- Rate limits on free tier: 15 RPM (requests per minute), 1M TPM
- Latency: Flash model typically 1–4 seconds per image request
- Data privacy: Gemini API data is not used for training by default when using API key access; Vertex AI offers stronger enterprise data controls
- **Relevant strength:** Native carousel/multi-image support is directly aligned with our use case

#### OpenAI GPT-4o / GPT-4o-mini

**Source:** https://platform.openai.com/docs/guides/vision  
**Model versions:** gpt-4o, gpt-4o-mini, gpt-4-turbo (vision)

- Accepts multiple images per request (up to ~10 practical limit per message)
- Does not have a native "sequence of images" concept — images are treated as independent items in a message
- Strong general visual reasoning and OCR
- Pricing (gpt-4o, as of research date): $2.50 per 1M input tokens; images billed at 85–1,105 tokens depending on resolution (low/high detail mode)
- Pricing (gpt-4o-mini): $0.15 per 1M input tokens
- Rate limits: Tier-dependent; Tier 1 starts at 500 RPM
- Latency: 2–8 seconds per image request depending on image size and detail mode
- No native video understanding — video must be pre-processed into frames
- Data privacy: Inputs not used for training by default; Zero Data Retention available for enterprise
- **Relevant limitation:** Multi-image carousel reasoning requires careful prompt engineering; no native ordering concept

#### Anthropic Claude 3.5 Sonnet / Claude 3 Opus

**Source:** https://docs.anthropic.com/en/docs/build-with-claude/vision  
**Model versions:** claude-3-5-sonnet-20241022, claude-3-opus-20240229

- Accepts up to 20 images per API request
- Strong at detailed visual analysis and nuanced descriptions
- Good OCR performance
- Pricing (Claude 3.5 Sonnet): $3.00 per 1M input tokens; images billed at ~1,600 tokens for standard images
- Pricing (Claude 3 Haiku): $0.25 per 1M input tokens
- Rate limits: Tier-dependent; starts at 50 RPM
- No native video understanding
- Data privacy: Inputs not used for training; enterprise agreements available
- **Relevant strength:** Nuanced, detailed descriptions; good at understanding context and mood

#### Qwen-VL (Alibaba)

**Source:** https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct  
**Model versions:** Qwen2-VL-7B-Instruct, Qwen2-VL-72B-Instruct

- Open-source, self-hostable
- Strong multilingual OCR including Chinese, Arabic, and other scripts
- Qwen2-VL-72B achieves competitive scores on DocVQA and OCRBench benchmarks
- Supports video input natively in the 72B variant
- Self-hosting requires significant GPU resources (72B model: ~4× A100 80GB)
- Available via Alibaba Cloud DashScope API
- DashScope pricing: approximately $0.001–$0.003 per image (varies by model size)
- **Relevant strength:** Best-in-class OCR for non-Latin scripts; strong for Indian language text in images
- **Relevant limitation:** Self-hosting at production scale is expensive; cloud API has less documentation in English

#### InternVL2 (Shanghai AI Lab)

**Source:** https://huggingface.co/OpenGVLab/InternVL2-8B  
**Model versions:** InternVL2-8B, InternVL2-26B, InternVL2-76B

- Open-source, self-hostable
- Competitive with GPT-4V on several benchmarks (MMBench, MMMU)
- Strong at high-resolution image understanding
- No managed cloud API — must self-host or use third-party inference providers
- **Relevant limitation:** No managed API; operational overhead is significant for an MVP

#### LLaVA (Large Language and Vision Assistant)

**Source:** https://llava-vl.github.io/  
**Model versions:** LLaVA-1.6 (LLaVA-NeXT), LLaVA-1.5

- Open-source, self-hostable
- Good general visual understanding
- Weaker than Gemini/GPT-4o on fine-grained OCR and complex reasoning
- Available via Ollama for local deployment
- **Relevant limitation:** Lags behind frontier models on detailed scene understanding; no managed API

### 1.3 Image Model Comparison Table

| Criterion | Gemini 1.5 Flash | Gemini 1.5 Pro | GPT-4o | Claude 3.5 Sonnet | Qwen2-VL-72B | InternVL2-76B |
|---|---|---|---|---|---|---|
| Multi-image (carousel) | ✅ Native (3,600 imgs) | ✅ Native | ⚠️ Manual (10 imgs) | ⚠️ Manual (20 imgs) | ✅ Native | ✅ Native |
| OCR quality | Good | Very good | Very good | Good | Excellent | Very good |
| Scene reasoning | Good | Excellent | Excellent | Excellent | Good | Good |
| Fine detail | Good | Very good | Very good | Very good | Good | Good |
| Video native | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ✅ 72B only | ❌ No |
| Audio native | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| Managed API | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ DashScope | ❌ No |
| Cost per image (approx) | ~$0.00002 | ~$0.0009 | ~$0.00075 | ~$0.0048 | ~$0.002 | Self-host |
| Latency (typical) | 1–4s | 2–8s | 2–8s | 3–10s | 2–6s | Varies |
| Privacy controls | Good | Good | Good | Good | Moderate | Full (self-host) |

*Costs are approximate estimates based on published token pricing and typical image token counts as of research date. Actual costs depend on prompt length, image resolution, and response length. Verify current pricing before implementation.*

*Benchmark scores (MMBench, MMMU, DocVQA) are published by model developers and independent evaluators. We have not run our own benchmarks yet — see MODEL_EVALUATION_PLAN.md.*

### 1.4 Image Model Recommendation

**MVP primary:** Gemini 1.5 Flash  
**MVP fallback / quality upgrade:** Gemini 1.5 Pro or GPT-4o

**Reasoning:**
1. Native multi-image support directly maps to our carousel use case without prompt engineering workarounds
2. Native video and audio support means a single provider can handle all three media types, reducing integration complexity
3. Flash model offers the best cost-to-quality ratio for an MVP
4. The 1M token context window allows processing an entire carousel in one API call, preserving sequence context
5. Google AI Studio free tier allows development and testing without upfront cost

---

## 2. Video Understanding

### 2.1 Approaches Evaluated

#### Approach A: Native Video API (Gemini)

Gemini 1.5 Pro and Flash accept video files directly via the File API.

- Upload video file → receive file URI → include URI in prompt
- Supports up to 1 hour of video
- Gemini samples frames internally at approximately 1 frame per second
- Audio track is also processed natively
- The model reasons across the full temporal sequence
- **Source:** https://ai.google.dev/gemini-api/docs/vision#video

**Advantages:**
- Single API call handles video + audio together
- No frame extraction code to maintain
- Temporal reasoning is handled by the model
- Preserves audio-visual synchronisation

**Disadvantages:**
- Less control over which frames are analysed
- Cannot target specific scenes or moments
- File upload adds latency (large files take time to upload)
- Cost scales with video duration (token count)
- Gemini's internal sampling rate (1 fps) may miss fast-moving content

#### Approach B: FFmpeg Frame Extraction + Vision API

Use our existing FFmpeg installation to extract frames, then send frames to a vision API.

**Frame extraction strategies:**

1. **Uniform sampling** — extract one frame every N seconds
   - Simple, predictable, controllable cost
   - May miss important moments between samples
   - FFmpeg command: `ffmpeg -i input.mp4 -vf fps=1/5 frame_%04d.jpg`

2. **Scene-change detection** — extract frames only when the scene changes significantly
   - FFmpeg `select` filter with `scene` threshold: `ffmpeg -i input.mp4 -vf "select=gt(scene\,0.3)" -vsync vfr frame_%04d.jpg`
   - More semantically meaningful frames
   - Threshold tuning required; may miss gradual changes

3. **Keyframe extraction** — extract I-frames (encoder keyframes)
   - `ffmpeg -i input.mp4 -vf "select=eq(pict_type\,I)" -vsync vfr frame_%04d.jpg`
   - Fast, no re-encoding needed
   - Keyframe density varies by encoder settings; may be too sparse or too dense

4. **Hybrid: scene-change + uniform fallback** — use scene detection with a maximum interval cap
   - Best balance of coverage and relevance
   - Slightly more complex implementation

**Timestamp preservation:**
- FFmpeg can embed timestamps in output filenames: `frame_%04d_pts%pts.jpg`
- Or extract via `ffprobe -show_frames` to get exact PTS (presentation timestamp) per frame

**Audio extraction:**
- `ffmpeg -i input.mp4 -vn -acodec pcm_s16le audio.wav`
- Extracted audio is then passed to a transcription service separately

**Advantages of Approach B:**
- Full control over frame selection
- Can target specific time ranges
- Works with any vision API (not locked to Gemini)
- Can deduplicate near-identical frames before sending to API (cost saving)
- Explicit timestamp tracking for evidence references

**Disadvantages:**
- More code to maintain
- Audio and video are processed separately — no native audio-visual synchronisation
- Multiple API calls instead of one
- Frame deduplication adds complexity

#### Approach C: Third-party Video Understanding APIs

Services such as Twelve Labs (https://www.twelvelabs.io/) offer dedicated video understanding APIs with semantic search and temporal understanding.

- Twelve Labs Marengo/Pegasus models: index video for semantic search and summarisation
- Pricing: based on video hours indexed; approximately $0.05–$0.15 per video minute (verify current pricing)
- Strong temporal understanding
- **Relevant limitation:** Additional vendor dependency; pricing model differs from per-token APIs; less control over output format

### 2.2 Video Understanding Recommendation

**MVP approach:** Gemini File API (Approach A) for videos under 5 minutes  
**Supplementary:** FFmpeg frame extraction (Approach B, hybrid scene-change + uniform) for longer videos or when frame-level evidence references are required

**Reasoning:**
1. For social media content, most videos are under 3 minutes — well within Gemini's native capability
2. Native video processing preserves audio-visual synchronisation, which is important for understanding speech-over-video content
3. FFmpeg is already installed and configured — frame extraction can be added as a fallback without new dependencies
4. The hybrid approach for longer videos gives us explicit timestamps for evidence references

---

## 3. Audio Understanding

### 3.1 Distinction: Transcription vs. General Audio Understanding

These are two different capabilities:

**Speech-to-text transcription:** Converting spoken words to text. Outputs: transcript, timestamps, language, speaker segments.

**General audio understanding:** Understanding non-speech audio — music genre, environmental sounds, emotional tone, background noise classification. This is a separate, harder problem with fewer mature solutions.

For our MVP, transcription is the primary requirement. General audio understanding is a future enhancement.

### 3.2 Transcription Models Evaluated

#### OpenAI Whisper (open-source)

**Source:** https://github.com/openai/whisper  
**Model sizes:** tiny, base, small, medium, large-v2, large-v3

- Open-source, runs locally
- Trained on 680,000 hours of multilingual audio
- Supports 99 languages including Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu
- Language detection built-in
- Word-level timestamps available with `--word_timestamps` flag
- Indian English accent handling: good on large-v2/v3; moderate on smaller models
- Code-mixed speech (Hinglish, Tanglish): moderate — Whisper handles it better than most alternatives but still makes errors on heavy code-mixing
- Background noise handling: good on large models; degrades on smaller models
- Local execution: large-v3 requires ~10GB VRAM; medium requires ~5GB VRAM; small requires ~2GB VRAM
- CPU inference is possible but slow (large-v3: ~10–30× real-time on CPU)
- **No API cost** — compute cost only

#### Faster-Whisper

**Source:** https://github.com/SYSTRAN/faster-whisper  
**Based on:** CTranslate2 optimised Whisper

- Same model weights as OpenAI Whisper, re-implemented with CTranslate2
- 4× faster than original Whisper on CPU; 2× faster on GPU
- Lower memory usage (INT8 quantisation available)
- Same language support and accuracy as Whisper
- Drop-in replacement for Whisper in most use cases
- **Recommended over original Whisper for production local deployment**

#### OpenAI Whisper API (cloud)

**Source:** https://platform.openai.com/docs/guides/speech-to-text  
**Model:** whisper-1

- Managed cloud API using Whisper large-v2
- Pricing: $0.006 per minute of audio (as of research date)
- No GPU required on our side
- Supports all Whisper languages
- Returns transcript with optional timestamps
- Rate limits: 50 RPM, 25MB file size limit
- **Relevant for MVP:** Eliminates GPU requirement; predictable cost

#### Gemini Audio (native)

**Source:** https://ai.google.dev/gemini-api/docs/audio  

- Gemini 1.5 Pro/Flash accept audio files directly
- Returns transcription as part of a multimodal response
- Can simultaneously describe audio content (music, sounds, tone)
- Supports 8.4 hours of audio per request
- Pricing: same token-based pricing as text/image
- Language support: broad, including Indian languages
- **Relevant strength:** If we are already using Gemini for vision, audio can be handled in the same API call for video content — no separate transcription step

#### Google Cloud Speech-to-Text v2

**Source:** https://cloud.google.com/speech-to-text  

- Managed cloud API
- Supports 125+ languages including all major Indian languages
- Chirp model (Universal Speech Model): strong on accented speech and code-mixing
- Pricing: approximately $0.016 per minute for standard; $0.048 per minute for Chirp (verify current pricing)
- Word-level timestamps
- Speaker diarisation available
- **Relevant strength:** Best-in-class for Indian language support and code-mixed speech

#### Azure Speech Services

**Source:** https://azure.microsoft.com/en-us/products/ai-services/speech-to-text  

- Supports Hindi, Tamil, Telugu, Bengali, and other Indian languages
- Pricing: approximately $0.016 per audio hour for standard (verify current pricing)
- Good accent handling
- **Less relevant for MVP** — adds another vendor dependency

### 3.3 Audio Transcription Comparison Table

| Criterion | Whisper large-v3 (local) | Faster-Whisper (local) | OpenAI Whisper API | Gemini Audio | Google STT Chirp |
|---|---|---|---|---|---|
| Indian English accuracy | Good | Good | Good | Good | Very good |
| Indian languages | Good | Good | Good | Good | Excellent |
| Code-mixed (Hinglish) | Moderate | Moderate | Moderate | Moderate | Good |
| Language detection | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Word timestamps | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Approximate | ✅ Yes |
| Background noise | Good | Good | Good | Good | Very good |
| Cost | Compute only | Compute only | $0.006/min | Token-based | ~$0.048/min (Chirp) |
| GPU required | Yes (large) | Yes (large) | No | No | No |
| Latency | Medium–High | Medium | Low–Medium | Low–Medium | Low |
| Privacy | Full (local) | Full (local) | OpenAI policy | Google policy | Google policy |
| Multimodal (audio+video) | ❌ No | ❌ No | ❌ No | ✅ Yes | ❌ No |

*Accuracy figures are based on published benchmarks and community evaluations. We have not run our own tests on Indian English or code-mixed speech. See MODEL_EVALUATION_PLAN.md.*

### 3.4 General Audio Understanding

Beyond transcription, understanding non-speech audio (music, ambient sounds, emotional tone) is relevant for video content where the audio track contributes to the caption context.

**Current state of the field:**
- Gemini 1.5 Pro/Flash can describe audio content beyond speech (music genre, environmental sounds, emotional tone) as part of its multimodal understanding
- Dedicated audio classification models (PANNs, AudioCLIP, CLAP) exist but require self-hosting
- No mature managed API specifically for general audio understanding at the time of research

**Recommendation for MVP:** Use Gemini's native audio understanding as a secondary signal. Do not build a dedicated audio classification pipeline in Phase 2.

### 3.5 Audio Recommendation

**MVP primary:** OpenAI Whisper API (cloud) for transcription  
**MVP alternative:** Faster-Whisper (local) if GPU is available and privacy is a concern  
**General audio understanding:** Gemini native audio (included in video processing call)

**Reasoning:**
1. OpenAI Whisper API eliminates GPU infrastructure requirements for MVP
2. $0.006/minute is affordable at MVP scale (100 minutes/day = $0.60/day)
3. Faster-Whisper is the recommended upgrade path when self-hosting becomes viable
4. Gemini handles general audio understanding as part of the video processing call — no additional integration needed

---

## 4. Summary of Recommended MVP Model Stack

| Component | Recommended | Alternative |
|---|---|---|
| Image understanding | Gemini 1.5 Flash | GPT-4o (higher cost, no native carousel) |
| Multi-image / carousel | Gemini 1.5 Flash (native) | GPT-4o with manual sequencing |
| Video understanding | Gemini 1.5 Flash (File API) | FFmpeg frames + Gemini Flash |
| Audio transcription | OpenAI Whisper API | Faster-Whisper (local, GPU required) |
| General audio understanding | Gemini 1.5 Flash (native) | Not available as managed API |

**Single-provider MVP option:** Use Gemini 1.5 Flash for everything (images, video, audio). This reduces integration complexity and API key management to a single provider.

**Dual-provider option:** Gemini 1.5 Flash for vision/video + OpenAI Whisper API for transcription. This gives best-in-class transcription with explicit timestamps while keeping vision costs low.
