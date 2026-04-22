# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FakeID is an identity verification API that uses computer vision and ML to verify ID documents and match them to live photos. Three features:
1. **Face Verification** — compares face in ID photo to live photo using ArcFace embeddings
2. **Age Estimation** — estimates age from live photo and checks consistency with declared ID age
3. **Document Authenticity** — detects forged ID documents via perspective correction, zone detection, geometric analysis, and binary classification (EfficientNet-B0)

Currently targets Spain only (prototype).

## Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run from project root — never from inside backend/
uvicorn backend.main:app --reload
```

Model weight files (`.pt`, `.pth`) go in `backend/weights/` and are gitignored. The server starts without them — routes return 503 if a model's weights are missing.

## Architecture

```
backend/
  config.py         # All constants and absolute paths (BASE_DIR, thresholds, WEIGHTS_DIR)
  schemas.py        # Pydantic request models (VerifyRequest, AgeRequest, DocumentRequest)
  dependencies.py   # Model instantiation with graceful fallback — import from here, not main.py
  main.py           # FastAPI app: registers routes, CORS, global exception handler only
  models/           # One file per feature: face_verify.py, age_model.py, doc_auth.py
  routes/           # One file per feature: verify.py, age.py, document.py
  utils/            # Shared: exceptions.py, preprocessing.py, similarity.py
  weights/          # Local model weights (gitignored)
frontend/
  index.html / style.css / camera.js   # Single-page app; frontend is empty in current branch
data/
  templates/        # Country layout JSON (spain.json)
  test_scenarios/   # Demo images
notebooks/          # Evaluation scripts only — no production code here
```

**Data flow:** `route → decode_base64_image() → model.run() → JSONResponse envelope`

Models are instantiated once at startup in `dependencies.py`. Routes import model instances from there. Models raise custom exceptions; routes catch them and return the correct HTTP status with the response envelope.

## API Response Format

Every endpoint returns this envelope — no exceptions:

```json
{ "success": true, "data": { ... }, "error": null }
{ "success": false, "data": null, "error": "canonical error string" }
```

HTTP codes: `200` success, `400` bad input / face not detected, `422` FastAPI validation (don't override), `500` model/server error, `503` weights missing.

Never return `200` with `success: false`. Never raise `HTTPException` — always return `JSONResponse` with the envelope.

## Error Handling Pattern

```python
# routes always follow this pattern
@router.post("/check-document")
def check_document(request: DocumentRequest):        # def not async def — PyTorch/CV2 are blocking
    if doc_authenticator is None:
        return JSONResponse(status_code=503, content={"success": False, "data": None, "error": "Model not loaded — weights file missing"})
    try:
        image = decode_base64_image(request.id_image)
        result = doc_authenticator.run(image)
        return JSONResponse(status_code=200, content={"success": True, "data": result, "error": None})
    except (InvalidImageError, ZoneDetectionError, PerspectiveCorrectionError) as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(status_code=400, content={"success": False, "data": None, "error": str(e)})
    except ModelInferenceError as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(status_code=500, content={"success": False, "data": None, "error": str(e)})
```

Custom exceptions live in `backend/utils/exceptions.py`. Models raise them; models never return `None` silently.

## Code Style (strict — see RULES.md for full detail)

- **Python 3.11+** syntax: `list[str]`, `str | None` (not `List`, not `Optional`)
- Full type hints on every function; docstrings on every public function/class
- All constants in `config.py` only — never hardcode thresholds or paths elsewhere
- Routes use `def` (not `async def`) because PyTorch/OpenCV are blocking
- Model files: main inference method is always `run()`, private helpers prefixed `_`, no FastAPI imports inside models
- URL paths: lowercase hyphens (`/verify-face`), not underscores or camelCase
- Canonical error strings must match exactly (see `RULES.md` Section 1.3)
- Import order: stdlib → third-party → local (full path from project root, e.g. `from backend.config import ...`)

## Key Thresholds (backend/config.py)

| Constant | Value | Purpose |
|---|---|---|
| `SIMILARITY_THRESHOLD` | 0.28 | Face match: below → suspicious |
| `MAX_AGE_GAP` | 5 | Years before age consistency flag |
| `CLASSIFIER_REAL_THRESHOLD` | 0.7 | EfficientNet score above → real |
| `LOW_CONFIDENCE_BOUNDARY` | 0.6 | Score 0.6–0.7 → real but `low_confidence: true` |
| `GEOMETRIC_TOLERANCE` | 0.15 | Max deviation from country template |

## Git Workflow

Branch naming: `feature/<name>` or `fix/<name>`. Never commit to `main` directly. Every merge to `main` requires a PR reviewed by the other contributor. Commit format: `type: lowercase description` (types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`).

Requirements changes go in a separate branch/PR (`chore/add-<package>`), never bundled with feature code.

Full workflow rules, PR template, and conflict resolution procedures are in `RULES.md`.
