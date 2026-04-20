# FakeID — Project Rules

## Section 1: API Response Format

### 1.1 Standard response envelope
Every route must return this exact structure:

```json
{
  "success": true | false,
  "data": { ... } | null,
  "error": null | "error message string"
}
```

Rules:
- If success is true → data has content, error is null
- If success is false → data is null, error has a message string
- Never return bare values — always wrap in the envelope

---

### 1.2 Feature-specific response shapes

**Feature 1 — face verification** (Yara)
```json
{
  "success": true,
  "data": {
    "feature": "face_verification",
    "layers": {
      "face_detection": {
        "id_face_detected": true,
        "live_face_detected": true
      },
      "similarity": {
        "score": 0.87,
        "label": "verified"
      }
    }
  },
  "error": null
}
```

**Feature 2 — age estimation** (Yara)
```json
{
  "success": true,
  "data": {
    "feature": "age_estimation",
    "layers": {
      "age_model": {
        "estimated_age": 24
      },
      "consistency": {
        "id_age": 22,
        "gap": 2,
        "flag": false
      }
    }
  },
  "error": null
}
```

**Feature 3 — document authenticity** (Giorgia)
```json
{
  "success": true,
  "data": {
    "feature": "document_authenticity",
    "layers": {
      "perspective": {
        "corrected": true
      },
      "zone_detection": {
        "photo_zone": true,
        "mrz": true,
        "text_fields": true
      },
      "geometric_analysis": {
        "country_matched": "spain",
        "deviation_score": 0.12,
        "within_tolerance": true
      },
      "classifier": {
        "score": 0.91,
        "label": "real"
      }
    }
  },
  "error": null
}
```

---

### 1.3 Error response shape
All errors across all features must follow this format:

```json
{
  "success": false,
  "data": null,
  "error": "descriptive message of what went wrong"
}
```

Example error messages (use these exact strings for consistency):
- "No face detected in ID photo"
- "No face detected in live photo"
- "Document perspective correction failed"
- "No document zones detected"
- "Model inference failed"
- "Invalid image format"
- "Missing required field: age_on_id"

---

### 1.4 HTTP status codes
- 200 → success
- 400 → bad input (missing field, wrong format)
- 422 → validation error (FastAPI default — do not override)
- 500 → model or server error

Never return 200 with success: false.
Always return the correct HTTP code AND the envelope.


#########################################################
## Section 2: Folder Structure

### 2.1 Full structure

FakeID/
├── backend/
│   ├── models/           # ML model classes only — one file per feature
│   ├── routes/           # FastAPI route handlers only — one file per feature
│   ├── utils/            # Shared helper functions — preprocessing, similarity
│   ├── weights/          # Pretrained model weight files (.pt, .pth) — never commit these
│   └── main.py           # FastAPI app entry point — connects all routes, nothing else
├── frontend/
│   ├── index.html        # Single page app — all UI lives here
│   ├── style.css         # All styles — mobile-first
│   └── camera.js         # All camera logic and API calls to backend
├── data/
│   ├── templates/        # Hardcoded country layout templates (JSON) — spain.json, france.json etc.
│   └── test_scenarios/   # Demo test images — one subfolder per scenario
├── notebooks/            # Evaluation scripts, threshold tuning, metric plots — for report use
├── requirements.txt      # Python dependencies — update this if you add a package
├── RULES.md              # This file
└── .gitignore            # Already configured — do not modify without agreeing first

### 2.2 Rules

- One file per feature per layer — never put Feature 1 and Feature 3 logic in the same file
- models/ contains only model classes and inference logic — no routing, no HTTP
- routes/ contains only FastAPI endpoints — no ML logic, just call the model and return the response
- utils/ is for functions used by more than one feature — if only one feature uses it, keep it in that feature's file
- weights/ is local only — never commit weight files, they are gitignored
- data/templates/ contains one JSON file per country — named spain.json, france.json etc.
- data/test_scenarios/ contains one subfolder per demo scenario
- notebooks/ is for exploration only — no production code lives here
- If you need to add a new folder, tell the other person before pushing

### 2.3 What goes in test_scenarios

data/test_scenarios/
├── czech_fake/     # Completely fake ID from non-existent document — tests Feature 3
│   ├── id_photo.jpg
│   └── live_photo.jpg
└── sisters_id/     # Real ID but wrong person — tests Feature 1
    ├── id_photo.jpg
    └── live_photo.jpg


###########################################################

## Section 3: Error Handling

### 3.1 Custom exception classes
Create these in backend/utils/exceptions.py — import them in any model file that needs them:

```python
class FaceNotDetectedError(Exception):
    pass

class DocumentNotDetectedError(Exception):
    pass

class PerspectiveCorrectionError(Exception):
    pass

class ZoneDetectionError(Exception):
    pass

class ModelInferenceError(Exception):
    pass

class InvalidImageError(Exception):
    pass
```

### 3.2 Where to catch errors
- Models raise custom exceptions (never return None silently)
- Routes catch custom exceptions and convert them to HTTPException
- main.py has a global fallback handler for anything unexpected

Example pattern every route must follow:

```python
from fastapi import HTTPException

@router.post("/verify")
async def verify(...)
    try:
        result = face_model.run(...)
        return {"success": True, "data": result, "error": None}
    except FaceNotDetectedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ModelInferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3.3 Global fallback handler in main.py
Paste this in backend/main.py — catches anything the routes missed:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"UNHANDLED ERROR on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": "Unexpected server error"}
    )
```

### 3.4 Logging — what gets printed to terminal
Every caught error must print a detailed log before returning the response.
Use this format in every route:

```python
print(f"ERROR [{feature_name}]: {str(e)} | input shape: {image.shape}")
```

Never silence an error without logging it first. Never use bare except: pass.

### 3.5 Frontend error handling
The frontend maps backend error messages to bouncer-friendly display messages.
Add this mapping in camera.js:

```javascript
const ERROR_MESSAGES = {
    "No face detected in ID photo": "Could not find a face on the ID — please retake",
    "No face detected in live photo": "Could not detect your face — please look at the camera",
    "Document perspective correction failed": "ID image is too blurry or angled — please retake",
    "No document zones detected": "Could not read the ID document — please retake",
    "Model inference failed": "System error — please try again",
    "Invalid image format": "Image format not supported — please retake",
    "Missing required field: age_on_id": "Please enter the age shown on the ID",
    "Unexpected server error": "Something went wrong — please try again"
}

function getDisplayError(backendMessage) {
    return ERROR_MESSAGES[backendMessage] || "Something went wrong — please try again"
}
```

### 3.6 Edge cases to handle per feature

Feature 1 — face verification:
- ID photo has no detectable face → FaceNotDetectedError
- Live photo has no detectable face → FaceNotDetectedError
- Image is completely black or corrupt → InvalidImageError

Feature 2 — age estimation:
- Age field left empty by bouncer → return 400 with "Missing required field: age_on_id"
- Face crop from Feature 1 is too small → ModelInferenceError

Feature 3 — document authenticity:
- Perspective correction produces distorted output → PerspectiveCorrectionError
- YOLO detects zero zones → ZoneDetectionError
- Country not matched to any template → return geometric deviation_score of 1.0 and label "unknown"
- EfficientNet confidence below 0.6 → still return result but add "low_confidence": true in classifier layer

###########################################