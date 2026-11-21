"""Understanding API endpoints — Phase 2.

POST /api/v1/understanding/{collection_id}
    Start understanding analysis for a collection.
    In Phase 2 this is synchronous — the response is returned when
    processing completes.  Document this limitation clearly.

GET /api/v1/evidence/{collection_id}
    Retrieve the MediaEvidence for a collection.
    In Phase 2 evidence is returned directly from the pipeline result.
    Persistence to the database is planned for Phase 3.

Note on synchronous processing:
    Phase 2 processes media synchronously within the HTTP request.
    For videos this may take 30–120 seconds depending on duration and
    provider latency.  A background job queue will be introduced in Phase 3.
    Clients should use an appropriate HTTP timeout (minimum 180 seconds).
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.exceptions import EvidenceNotFoundError, MediaNotFoundError
from app.database import repository as repo
from app.pipelines.understanding_pipeline import run_understanding_pipeline
from app.schemas.common import APIResponse
from app.schemas.understanding import EvidenceResponse
from app.evidence.pipeline import build_unified_evidence, run_evidence_pipeline
from app.schemas.unified_evidence import (
    ContentSummary,
    CrossModalRelationship,
    EvidenceConflict,
    EvidenceItem,
    EvidenceQualityDimensions,
    UnifiedMediaEvidence,
)

router = APIRouter(prefix="/understanding", tags=["understanding"])
evidence_router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("/{collection_id}", response_model=APIResponse[EvidenceResponse])
def start_understanding(collection_id: str, db: Session = Depends(get_db)):
    """Start (and complete, synchronously) understanding analysis for a collection.

    WARNING: This endpoint is synchronous in Phase 2.
    Processing may take up to 120 seconds for video content.
    Use a client timeout of at least 180 seconds.
    """
    collection = repo.get_collection(db, collection_id)
    if not collection:
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")

    evidence = run_understanding_pipeline(collection_id, db)
    package = build_unified_evidence(evidence)
    latest_job = sorted(collection.jobs, key=lambda job: job.created_at, reverse=True)[0] if collection.jobs else None
    repo.save_evidence_package(db, package, processing_job_id=latest_job.id if latest_job else None)
    db.commit()

    response_data = EvidenceResponse.from_evidence(evidence)

    if evidence.processing_status == "failed":
        return JSONResponse(
            status_code=422,
            content=APIResponse.fail(
                "Understanding pipeline failed",
                "UNDERSTANDING_FAILED",
                {"errors": evidence.processing_errors},
            ).model_dump(mode="json"),
        )

    return APIResponse.ok(
        "Understanding complete" if evidence.processing_status == "complete"
        else "Understanding partially complete",
        data=response_data,
    )


@evidence_router.get("/{collection_id}", response_model=APIResponse[UnifiedMediaEvidence])
def get_evidence(collection_id: str, db: Session = Depends(get_db)):
    """Retrieve the persisted unified evidence package without rerunning providers."""
    collection = repo.get_collection(db, collection_id)
    if not collection:
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")

    package = run_evidence_pipeline(collection_id, db, rebuild=False)
    if not package:
        raise EvidenceNotFoundError(f"No evidence package exists for collection '{collection_id}'.")
    return APIResponse.ok("Evidence package retrieved", data=package)


@evidence_router.get("/{collection_id}/items", response_model=APIResponse[list[EvidenceItem]])
def get_evidence_items(collection_id: str, db: Session = Depends(get_db)):
    package = repo.load_evidence_package(db, collection_id)
    if not repo.get_collection(db, collection_id):
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")
    if not package:
        raise EvidenceNotFoundError(f"No evidence package exists for collection '{collection_id}'.")
    return APIResponse.ok("Evidence items retrieved", data=package.evidence_items)


@evidence_router.get("/{collection_id}/provenance", response_model=APIResponse[list[EvidenceItem]])
def get_evidence_provenance(collection_id: str, db: Session = Depends(get_db)):
    package = repo.load_evidence_package(db, collection_id)
    if not repo.get_collection(db, collection_id):
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")
    if not package:
        raise EvidenceNotFoundError(f"No evidence package exists for collection '{collection_id}'.")
    return APIResponse.ok("Evidence provenance retrieved", data=package.evidence_items)


@evidence_router.get("/{collection_id}/conflicts", response_model=APIResponse[list[EvidenceConflict]])
def get_evidence_conflicts(collection_id: str, db: Session = Depends(get_db)):
    package = repo.load_evidence_package(db, collection_id)
    if not repo.get_collection(db, collection_id):
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")
    if not package:
        raise EvidenceNotFoundError(f"No evidence package exists for collection '{collection_id}'.")
    return APIResponse.ok("Evidence conflicts retrieved", data=package.conflicts)


@evidence_router.get("/{collection_id}/relationships", response_model=APIResponse[list[CrossModalRelationship]])
def get_evidence_relationships(collection_id: str, db: Session = Depends(get_db)):
    package = repo.load_evidence_package(db, collection_id)
    if not repo.get_collection(db, collection_id):
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")
    if not package:
        raise EvidenceNotFoundError(f"No evidence package exists for collection '{collection_id}'.")
    return APIResponse.ok("Evidence relationships retrieved", data=package.cross_modal_relationships)


@evidence_router.get("/{collection_id}/quality", response_model=APIResponse[EvidenceQualityDimensions])
def get_evidence_quality(collection_id: str, db: Session = Depends(get_db)):
    package = repo.load_evidence_package(db, collection_id)
    if not repo.get_collection(db, collection_id):
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")
    if not package or not package.quality:
        raise EvidenceNotFoundError(f"No evidence quality assessment exists for collection '{collection_id}'.")
    return APIResponse.ok("Evidence quality retrieved", data=package.quality)


@evidence_router.get("/{collection_id}/summary", response_model=APIResponse[ContentSummary])
def get_evidence_summary(collection_id: str, db: Session = Depends(get_db)):
    package = repo.load_evidence_package(db, collection_id)
    if not repo.get_collection(db, collection_id):
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")
    if not package or not package.content_summary:
        raise EvidenceNotFoundError(f"No grounded content summary exists for collection '{collection_id}'.")
    return APIResponse.ok("Grounded content summary retrieved", data=package.content_summary)


@evidence_router.post("/{collection_id}/rebuild", response_model=APIResponse[UnifiedMediaEvidence])
def rebuild_evidence(collection_id: str, db: Session = Depends(get_db)):
    """Explicitly rerun Phase 2 understanding and replace the evidence package."""
    if not repo.get_collection(db, collection_id):
        raise MediaNotFoundError(f"Collection '{collection_id}' not found.")
    package = run_evidence_pipeline(collection_id, db, rebuild=True)
    if not package:
        raise EvidenceNotFoundError(f"Unable to rebuild evidence for collection '{collection_id}'.")
    return APIResponse.ok("Evidence package rebuilt", data=package)


@evidence_router.get("/review/{collection_id}", response_class=HTMLResponse)
def evidence_review_interface(collection_id: str):
    """Temporary isolated review interface for evidence inspection."""
    return HTMLResponse(content=f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Evidence Review</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #17202a; }}
    section {{ margin: 1rem 0; padding: 1rem; border: 1px solid #ccd1d1; border-radius: 8px; }}
    .item {{ margin: .75rem 0; padding: .75rem; background: #f7f9f9; }}
    .uncertain {{ color: #9c6500; }}
    pre {{ white-space: pre-wrap; }}
  </style>
</head>
<body>
  <h1>Evidence Review</h1>
  <p>Collection: <code>{collection_id}</code></p>
  <button id="rebuild">Rebuild evidence</button>
    <section>
      <h2>Caption generation</h2>
      <label>Platform
        <select id="platform">
          <option>instagram</option><option>linkedin</option><option>x</option>
          <option>facebook</option><option>youtube</option><option>threads</option><option>custom</option>
        </select>
      </label>
      <label>Objective
        <select id="objective">
          <option>engagement</option><option>brand_awareness</option><option>education</option>
          <option>promotion</option><option>storytelling</option><option>community_building</option>
          <option>product_showcase</option><option>entertainment</option><option>professional_communication</option>
        </select>
      </label>
      <label>Audience
        <select id="audience">
          <option>general</option><option>students</option><option>professionals</option>
          <option>creators</option><option>customers</option><option>business_owners</option>
        </select>
      </label>
      <label>Tone
        <select id="tone">
          <option>friendly</option><option>professional</option><option>conversational</option>
          <option>humorous</option><option>inspirational</option><option>educational</option>
          <option>persuasive</option><option>minimalist</option><option>storytelling</option>
        </select>
      </label>
      <label>Language
        <select id="language">
          <option>english</option><option>kannada</option><option>hindi</option><option>tamil</option>
          <option>telugu</option><option>malayalam</option><option>hinglish</option>
        </select>
      </label>
      <label>Length
        <select id="length"><option>short</option><option selected>medium</option><option>long</option></select>
      </label>
      <label>Emojis
        <select id="emojis"><option>none</option><option selected>minimal</option><option>moderate</option><option>expressive</option></select>
      </label>
      <label>Hashtags
        <select id="hashtags"><option>disabled</option><option selected>relevant</option><option>minimal</option><option>custom</option></select>
      </label>
      <label><input id="cta" type="checkbox" checked> Include CTA</label>
      <label>Brand voice<textarea id="brandVoice"></textarea></label>
      <label>Custom instructions<textarea id="instructions"></textarea></label>
      <button id="generate">Generate variants</button>
      <div id="generations"></div>
    </section>
  <section><h2>Media and status</h2><pre id="overview"></pre></section>
  <section><h2>Grounded summary</h2><pre id="summary"></pre></section>
  <section><h2>Evidence items</h2><div id="items"></div></section>
  <section><h2>Relationships</h2><pre id="relationships"></pre></section>
  <section><h2>Contradictions</h2><pre id="conflicts"></pre></section>
  <section><h2>Quality</h2><pre id="quality"></pre></section>
  <script>
    const collectionId = {collection_id!r};
    const prefix = "/api/v1/evidence/" + encodeURIComponent(collectionId);
    async function load() {{
      const pkgResponse = await fetch(prefix);
      const pkgEnvelope = await pkgResponse.json();
      if (!pkgEnvelope.success) {{
        document.body.insertAdjacentHTML("beforeend", "<p>Evidence package unavailable.</p>");
        return;
      }}
      const pkg = pkgEnvelope.data;
      document.querySelector("#overview").textContent = JSON.stringify({{
        collection_type: pkg.collection_type, asset_ids: pkg.asset_ids,
        processing_status: pkg.processing_status, providers_used: pkg.providers_used,
        warnings: pkg.warnings
      }}, null, 2);
      document.querySelector("#summary").textContent = JSON.stringify(pkg.content_summary, null, 2);
      document.querySelector("#relationships").textContent = JSON.stringify(pkg.cross_modal_relationships, null, 2);
      document.querySelector("#conflicts").textContent = JSON.stringify(pkg.conflicts, null, 2);
      document.querySelector("#quality").textContent = JSON.stringify(pkg.quality, null, 2);
      document.querySelector("#items").innerHTML = pkg.evidence_items.map(item => `
        <div class="item ${{item.uncertainty_note ? "uncertain" : ""}}">
          <strong>${{item.category}} — ${{item.observation_type}}</strong>
          <div>${{item.value}}</div>
          <small>Evidence ID: ${{item.evidence_id}} | Modality: ${{item.source.modality}} |
          Asset: ${{item.source.media_id}} | Frame: ${{item.source.frame_index ?? "n/a"}} |
          Time: ${{item.source.video_start_seconds ?? item.source.audio_start_seconds ?? "n/a"}} |
          Uncertainty: ${{item.uncertainty_note ?? "none"}}</small>
        </div>`).join("");
    }}
    document.querySelector("#rebuild").addEventListener("click", async () => {{
      await fetch(prefix + "/rebuild", {{ method: "POST" }});
      await load();
    }});
    document.querySelector("#generate").addEventListener("click", async () => {{
      const config = {{
        platform: document.querySelector("#platform").value,
        objective: document.querySelector("#objective").value,
        audience: document.querySelector("#audience").value,
        tone: document.querySelector("#tone").value,
        language: document.querySelector("#language").value,
        caption_length: document.querySelector("#length").value,
        emoji_preference: document.querySelector("#emojis").value,
        hashtag_preference: document.querySelector("#hashtags").value,
        cta_enabled: document.querySelector("#cta").checked,
        brand_voice_description: document.querySelector("#brandVoice").value || null,
        additional_instructions: document.querySelector("#instructions").value || null,
        variant_count: 3
      }};
      const response = await fetch("/api/v1/generation/captions/" + encodeURIComponent(collectionId), {{
        method: "POST", headers: {{"Content-Type":"application/json"}},
        body: JSON.stringify(config)
      }});
      const envelope = await response.json();
      if (!envelope.success) {{
        document.querySelector("#generations").innerHTML =
          "<p><strong>Generation unavailable:</strong> " + envelope.message + "</p>";
        return;
      }}
      const request = envelope.data;
      document.querySelector("#generations").innerHTML = request.variants.map(variant => {{
        const grounding = request.grounding[variant.variant_id];
        const quality = request.quality[variant.variant_id];
        return `<article class="item">
          <h3>${{variant.approach}}</h3>
          <p>${{variant.caption_text}}</p>
          <p><strong>Grounding:</strong> ${{grounding.status}} —
          ${{grounding.is_verified ? "verified" : "NOT verified"}}</p>
          <small>Evidence: ${{(variant.evidence_ids || []).join(", ") || "none"}}</small>
          <details><summary>Quality feedback</summary><pre>${{JSON.stringify(quality, null, 2)}}</pre></details>
        </article>`;
      }}).join("");
    }});
    load();
  </script>
</body>
</html>""")
