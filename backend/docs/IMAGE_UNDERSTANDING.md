# Image Understanding

**Phase:** 2.3  
**Provider:** Gemini 2.0 Flash (configurable)  
**Status:** Implemented and tested (mocked). Requires GEMINI_API_KEY for live use.

---

## Supported Formats

- PNG
- JPEG / JPG
- WebP

---

## Single Image Analysis

`POST /api/v1/understanding/{collection_id}` where the collection contains one image.

The image is loaded from local storage, sent to the vision provider with a structured JSON prompt, and the response is parsed into an `ImageObservation`.

**What is extracted:**
- Scene description
- Detected objects with confidence levels
- Visible text (OCR) with language detection
- Dominant colours
- Estimated setting (indoor / outdoor / studio)
- Activities and actions
- Mood or tone (labelled as model interpretation)
- Notable details
- Spatial relationships

---

## Carousel Analysis

`POST /api/v1/understanding/{collection_id}` where the collection contains multiple images.

All carousel images are sent to Gemini in a **single API call** to preserve sequence context. The model is instructed to return a JSON array with one entry per image, keyed by `sequence_index`.

**Sequence preservation:**
- Images are sorted by `sequence_index` before sending.
- The model is told the total number of images and their indices.
- Results are sorted by `sequence_index` before storing in `MediaEvidence`.
- Missing observations are filled with empty entries and a warning.

**Why single API call:**
Sending all images together allows the model to reason across the sequence — understanding that image 2 shows a close-up of the product shown in image 1, for example. This is not possible when images are analysed independently.

---

## Evidence Structure

```json
{
  "collection_id": "...",
  "collection_type": "carousel",
  "image_observations": [
    {
      "media_id": "...",
      "sequence_index": 0,
      "scene_description": "A red sneaker on a white background",
      "detected_objects": [
        {"label": "sneaker", "confidence": "high"}
      ],
      "extracted_text": [
        {"text": "NIKE", "confidence": "high", "language": "en"}
      ],
      "dominant_colours": ["white", "red", "black"],
      "estimated_setting": "studio",
      "activities": [],
      "mood_or_tone": "clean, commercial",
      "notable_details": ["visible swoosh logo", "lace detail"],
      "spatial_relationships": [],
      "confidence": "high",
      "provider": "gemini",
      "model_version": "gemini-2.0-flash"
    }
  ],
  "all_extracted_text": [{"text": "NIKE", "confidence": "high"}],
  "processing_status": "complete",
  "has_visual_evidence": true
}
```

---

## Confidence Levels

| Level | Meaning |
|-------|---------|
| `high` | Model is confident in this observation |
| `medium` | Model has some uncertainty |
| `low` | Model is guessing; treat with caution |

Confidence levels come from the model's self-assessment. They are not manufactured when the provider does not supply them.

---

## Observed vs. Interpreted

The schema explicitly separates:
- **Directly observed**: `detected_objects`, `extracted_text`, `dominant_colours`, `estimated_setting`
- **Model interpretation**: `scene_description`, `activities`, `mood_or_tone`, `notable_details`, `spatial_relationships`

The caption generator (Phase 3) must not state interpretations as facts.

---

## Limitations

- Gemini 2.0 Flash may miss fine-grained details in very small images.
- OCR accuracy on stylised or handwritten Indic script is unverified — see `MODEL_EVALUATION_PLAN.md`.
- Carousel reasoning quality depends on the model's ability to understand sequence context from the prompt. This has not been evaluated on our test set yet.
- Confidence levels are self-reported by the model and may not be calibrated.
