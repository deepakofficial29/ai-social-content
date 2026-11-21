# Model Evaluation Plan — Multimodal AI Caption Generator

**Phase:** 2.1 — Research and Architecture Planning  
**Status:** Plan only. No benchmarks have been run yet.

This document distinguishes clearly between:
- **Published benchmark scores** — from model developers or independent evaluators
- **Our own experiments** — to be run before committing to a provider

---

## 1. Why We Need Our Own Evaluation

Published benchmarks (MMBench, MMMU, DocVQA, Fleurs, etc.) measure general capability on academic datasets. They do not measure:

- Performance on Indian social media content specifically
- Indian English accent handling
- Code-mixed speech (Hinglish, Tanglish, etc.)
- Carousel sequence reasoning
- Caption quality for social media platforms
- Hallucination rate on our specific content types

We must run our own experiments before committing to a provider for production.

---

## 2. Test Media Categories

### 2.1 Image Test Set

| Category | Count | Description |
|---|---|---|
| Product photos | 20 | Single product on plain background |
| Lifestyle images | 20 | People using products in real settings |
| Food and beverage | 15 | Restaurant dishes, home cooking |
| Travel and outdoor | 15 | Landmarks, landscapes, street scenes |
| Text-heavy images | 15 | Posters, menus, price tags, signage |
| Indian text in images | 10 | Hindi, Tamil, Telugu script in images |
| Infographics | 10 | Charts, diagrams, data visualisations |
| Low-quality / compressed | 10 | Typical WhatsApp-forwarded image quality |

**Total: 115 images**

### 2.2 Carousel Test Set

| Category | Count | Description |
|---|---|---|
| Product carousel (3–5 images) | 10 | Multiple product angles |
| Event carousel (4–8 images) | 10 | Event photos in chronological order |
| Tutorial carousel (5–10 images) | 10 | Step-by-step instructions |
| Mixed-content carousel | 5 | Images with different subjects |

**Total: 35 carousels**

### 2.3 Video Test Set

| Category | Count | Description |
|---|---|---|
| Product demo with voiceover | 10 | 30–90 seconds |
| Silent product showcase | 10 | No audio track |
| Talking-head / testimonial | 10 | Person speaking to camera |
| Event highlight reel | 5 | Multiple scenes, background music |
| Screen recording / tutorial | 5 | Software or app walkthrough |

**Total: 40 videos**

### 2.4 Audio Test Set

| Category | Count | Description |
|---|---|---|
| Clear Indian English speech | 15 | Studio-quality recording |
| Accented Indian English | 15 | Various regional accents |
| Hindi speech | 10 | Clear Hindi |
| Code-mixed Hinglish | 10 | Mixed Hindi-English |
| Regional language (Tamil/Telugu/Bengali) | 10 | One language per sample |
| Noisy background | 10 | Street noise, crowd, music |
| Multiple speakers | 5 | Conversation or interview |

**Total: 75 audio samples**

---

## 3. Evaluation Metrics

### 3.1 Image Understanding Metrics

| Metric | Definition | How to Measure |
|---|---|---|
| Object detection accuracy | Fraction of ground-truth objects correctly identified | Manual annotation + model output comparison |
| Scene description relevance | Does the description match the actual scene? | Human rating 1–5 |
| OCR accuracy (Latin) | Character error rate on English text in images | Ground-truth text vs. extracted text |
| OCR accuracy (Indic) | Character error rate on Hindi/Tamil/Telugu text | Ground-truth text vs. extracted text |
| Hallucination rate | Fraction of model claims not supported by the image | Human review of model output |
| Detail coverage | Fraction of notable image elements mentioned | Human annotation of notable elements |
| Latency | Time from API call to response (ms) | Measured in code |
| Cost per image | Actual API cost per image | Calculated from token counts |

### 3.2 Carousel / Multi-Image Metrics

| Metric | Definition | How to Measure |
|---|---|---|
| Sequence awareness | Does the model understand image order matters? | Test with reversed carousel; check if output changes |
| Cross-image reasoning | Does the model connect information across images? | Annotate cross-image relationships; check coverage |
| Narrative coherence | Does the output tell a coherent story across images? | Human rating 1–5 |
| Per-image attribution | Can the model attribute observations to specific images? | Check if output references image positions |

### 3.3 Video Understanding Metrics

| Metric | Definition | How to Measure |
|---|---|---|
| Temporal accuracy | Are events described in the correct order? | Human review against video timeline |
| Key event coverage | Fraction of annotated key events mentioned | Manual annotation + output comparison |
| Audio-visual alignment | Does the description connect audio and visual content? | Human rating 1–5 |
| Silent video handling | Does the model correctly note absence of audio? | Check output for silent video samples |
| Latency | Time from upload to response (ms) | Measured in code |
| Cost per video minute | Actual API cost per minute of video | Calculated from token counts |

### 3.4 Audio Transcription Metrics

| Metric | Definition | How to Measure |
|---|---|---|
| Word Error Rate (WER) | Standard ASR metric: (S+D+I)/N | Ground-truth transcripts vs. model output |
| Character Error Rate (CER) | More appropriate for Indic scripts | Ground-truth vs. model output |
| Language detection accuracy | Correct language identified? | Ground-truth language labels |
| Code-mixing detection | Is code-mixed speech correctly handled? | Human review of Hinglish samples |
| Timestamp accuracy | Are word timestamps within 500ms of actual? | Manual verification on sample |
| Latency | Time from audio submission to transcript (ms) | Measured in code |
| Cost per minute | Actual API cost per audio minute | Calculated from API billing |

### 3.5 Overall Caption Quality Metrics (Phase 3 — for reference)

These metrics apply to the final caption output, not the understanding models. Included here for completeness.

| Metric | Definition |
|---|---|
| Factual accuracy | Fraction of caption claims supported by MediaEvidence |
| Platform appropriateness | Does the caption match the target platform's style? |
| Engagement potential | Human rating of likely engagement |
| Hashtag relevance | Are suggested hashtags relevant to the content? |
| Character count compliance | Does the caption fit within platform limits? |

---

## 4. Evaluation Procedure

### 4.1 Phase 1: Provider Shortlisting (before integration)

1. Select 10 representative images from each category (not the full test set)
2. Run each candidate provider on the same inputs
3. Record outputs, latency, and cost
4. Human-rate outputs on scene description relevance and hallucination rate
5. Eliminate providers that fail basic accuracy or cost thresholds

**Decision threshold:** A provider must achieve < 15% hallucination rate and < $0.01 per image to proceed to full evaluation.

### 4.2 Phase 2: Full Benchmark (after integration)

1. Run the full test set through the selected provider
2. Calculate all metrics defined in Section 3
3. Document results in a benchmark report
4. Compare against published benchmarks to validate our setup

### 4.3 Phase 3: Regression Testing (ongoing)

1. Maintain a fixed set of 20 "golden" test cases per media type
2. Run golden tests after every provider version update
3. Alert if any metric degrades by more than 10% relative

---

## 5. Published Benchmark Reference Points

These are published scores from model developers or independent evaluators. **We have not verified these ourselves.**

### 5.1 Vision Benchmarks

| Model | MMBench | MMMU | DocVQA | Source |
|---|---|---|---|---|
| Gemini 1.5 Pro | ~82 | ~62 | ~87 | Google technical report, 2024 |
| GPT-4o | ~83 | ~69 | ~92 | OpenAI technical report, 2024 |
| Claude 3.5 Sonnet | ~79 | ~68 | ~89 | Anthropic technical report, 2024 |
| Qwen2-VL-72B | ~83 | ~64 | ~96 | Alibaba technical report, 2024 |
| InternVL2-76B | ~83 | ~65 | ~94 | Shanghai AI Lab, 2024 |

*These scores are from published reports and may not reflect current model versions. Scores on academic benchmarks do not directly predict performance on social media content.*

### 5.2 Audio Transcription Benchmarks

| Model | Fleurs WER (avg) | Hindi WER | Source |
|---|---|---|---|
| Whisper large-v3 | ~8.4% | ~12% | OpenAI technical report, 2023 |
| Whisper large-v2 | ~9.1% | ~14% | OpenAI technical report, 2022 |
| Google STT Chirp | Not published | Not published | — |

*WER on Fleurs is an average across languages. Hindi-specific WER is from community evaluations and may vary. Code-mixed speech WER is not published by any provider.*

---

## 6. Evaluation Infrastructure Requirements

To run these evaluations we will need:

1. A test media library (115 images, 35 carousels, 40 videos, 75 audio samples) — to be assembled before Phase 2 integration
2. Ground-truth annotations for each test item (object labels, transcripts, key events)
3. A simple evaluation script that calls each provider and records outputs
4. A human review interface (can be a simple spreadsheet initially)
5. API keys for each provider being evaluated (development keys only; not production)

**Estimated effort:** 2–3 days to assemble test media and annotations; 1 day to run evaluations; 1 day to analyse results.

---

## 7. Unresolved Questions

1. **Code-mixed speech accuracy** — No provider publishes WER on Hinglish or Tanglish. We must measure this ourselves before committing to a transcription provider.

2. **Carousel sequence reasoning** — We do not know whether Gemini's multi-image input preserves sequence context reliably. This must be tested with reversed-order carousels.

3. **Indian text OCR** — Published OCR benchmarks focus on English and Chinese. Performance on Hindi/Tamil/Telugu script in social media images (often stylised fonts) is unknown.

4. **Cost at scale** — Pricing estimates are based on published rates. Actual costs depend on prompt length, image resolution, and response verbosity. We must measure actual token counts on our test set.

5. **Latency under load** — Published latency figures are for single requests. Latency under concurrent load (multiple users uploading simultaneously) is unknown.
