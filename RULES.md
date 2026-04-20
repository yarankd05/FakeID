## Section 1: API Response Format

### 1.1 Standard response envelope
Every route must return this exact structure:

```json
{
  "success": true,
  "data": { },
  "error": null
}
```

Rules:
- If success is true → data has content, error is null
- If success is false → data is null, error has a message string
- Never return bare values — always wrap in the envelope
- Never return HTTP 200 with success: false — always pair the correct HTTP status code

---

### 1.2 Feature-specific response shapes

**Feature 1 — face verification (Yara)**
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

**Feature 2 — age estimation (Yara)**
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

**Feature 3 — document authenticity (Giorgia)**
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
        "label": "real",
        "low_confidence": false
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

Canonical error strings — use these exactly, no variations:
- "No face detected in ID photo"
- "No face detected in live photo"
- "Document perspective correction failed"
- "No document zones detected"
- "Model inference failed"
- "Invalid image format"
- "Missing required field: age_on_id"
- "Unexpected server error"
- "Model not loaded — weights file missing"

---

### 1.4 HTTP status codes
- 200 → success
- 400 → bad input (missing field, wrong format, face not detected)
- 422 → validation error (FastAPI default for malformed request body — do not override)
- 500 → model or server error
- 503 → model not loaded (weights file missing at startup)

Never return 200 with success: false.
Always pair the correct HTTP code with the envelope.

##################################################

## Section 2: Folder Structure

### 2.1 Full structure

```
FakeID/
├── backend/
│   ├── models/           # ML model classes only — one file per feature
│   ├── routes/           # FastAPI route handlers only — one file per feature
│   ├── utils/            # Shared helpers — preprocessing.py, exceptions.py, similarity.py
│   ├── weights/          # Pretrained model weight files (.pt, .pth) — never commit these
│   ├── config.py         # All constants and paths — owned by Giorgia
│   ├── dependencies.py   # Model instantiation — owned by Giorgia
│   ├── schemas.py        # All Pydantic request/response models — owned by Giorgia
│   └── main.py           # FastAPI app entry point — registers routes, nothing else
├── frontend/
│   ├── index.html        # Single page app — all UI lives here
│   ├── style.css         # All styles — mobile-first
│   └── camera.js         # All camera logic and API calls to backend
├── data/
│   ├── templates/        # Country layout templates (JSON) — spain.json, france.json etc.
│   └── test_scenarios/   # Demo test images — one subfolder per scenario
├── notebooks/            # Evaluation scripts, threshold tuning, metric plots — report use only
├── requirements.txt      # Python dependencies — update if you add a package
├── RULES.md              # This file
└── .gitignore            # Do not modify without agreeing first
```

### 2.2 Rules
- One file per feature per layer — never put Feature 1 and Feature 3 logic in the same file
- models/ contains only model classes and inference logic — no routing, no HTTP
- routes/ contains only FastAPI endpoints — no ML logic, just call the model and return response
- utils/ is for functions used by more than one feature — if only one feature uses it, keep it in that feature's file
- weights/ is local only — never commit weight files, they are gitignored
- data/templates/ contains one JSON file per country — named spain.json, france.json etc.
- data/test_scenarios/ contains one subfolder per demo scenario
- notebooks/ is for exploration only — no production code lives here
- If you need to add a new file or folder, tell the other person before pushing

### 2.3 What goes in test_scenarios

```
data/test_scenarios/
├── czech_fake/       # Completely fake ID — tests Feature 3
│   ├── id_photo.jpg
│   └── live_photo.jpg
└── sisters_id/       # Real ID, wrong person — tests Feature 1
    ├── id_photo.jpg
    └── live_photo.jpg
```

### 2.4 File creation order
Giorgia must create and push these files before Yara writes any route or model code:
1. backend/config.py
2. backend/schemas.py
3. backend/utils/exceptions.py
4. backend/utils/preprocessing.py
5. backend/dependencies.py

###################################

## Section 3: Error Handling

### 3.1 Custom exception classes
All custom exceptions live in backend/utils/exceptions.py:

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

class ModelNotLoadedError(Exception):
    pass
```

---

### 3.2 Where to catch errors and how to return them
Models raise custom exceptions — never return None silently.
Routes catch custom exceptions and return JSONResponse with the correct HTTP status code.
Never raise HTTPException directly — always return JSONResponse with our envelope.

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.dependencies import doc_authenticator
from backend.utils.preprocessing import decode_base64_image
from backend.utils.exceptions import ZoneDetectionError, PerspectiveCorrectionError
from backend.utils.exceptions import InvalidImageError, ModelInferenceError

@router.post("/check-document")
def check_document(request: DocumentRequest):
    """Check if an ID document is real or fake."""
    if doc_authenticator is None:
        return JSONResponse(
            status_code=503,
            content={"success": False, "data": None, "error": "Model not loaded — weights file missing"}
        )
    try:
        image = decode_base64_image(request.id_image)
        result = doc_authenticator.run(image)
        return JSONResponse(
            status_code=200,
            content={"success": True, "data": result, "error": None}
        )
    except (InvalidImageError, ZoneDetectionError, PerspectiveCorrectionError) as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "error": str(e)}
        )
    except ModelInferenceError as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": str(e)}
        )
```

---

### 3.3 Global fallback handler in main.py
Catches anything the routes missed — uncaught exceptions only:

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

---

### 3.4 Logging format
Every caught error must be logged before returning. Use this exact format:

```python
print(f"ERROR [{feature_name}]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
```

Rules:
- Never silence an error without logging it first
- Never use bare except: or except Exception: pass
- getattr(image, 'shape', 'not decoded') handles the case where image was never decoded

---

### 3.5 Frontend error handling
The frontend reads result.error from the top-level envelope — never result.detail.
Map backend error strings to bouncer-friendly messages in camera.js.
For the full fetch pattern see Section 4.11.

```javascript
const ERROR_MESSAGES = {
    "No face detected in ID photo": "Could not find a face on the ID — please retake",
    "No face detected in live photo": "Could not detect your face — please look at the camera",
    "Document perspective correction failed": "ID image is too angled — please retake",
    "No document zones detected": "Could not read the ID document — please retake",
    "Model inference failed": "System error — please try again",
    "Invalid image format": "Image format not supported — please retake",
    "Missing required field: age_on_id": "Please enter the age shown on the ID",
    "Model not loaded — weights file missing": "System not ready — contact support",
    "Unexpected server error": "Something went wrong — please try again"
}

function getDisplayError(backendMessage) {
    return ERROR_MESSAGES[backendMessage] || "Something went wrong — please try again"
}
```

---

### 3.6 Edge cases per feature

Feature 1 — face verification:
- ID photo has no detectable face → FaceNotDetectedError("No face detected in ID photo")
- Live photo has no detectable face → FaceNotDetectedError("No face detected in live photo")
- Image is corrupt or unreadable → InvalidImageError("Invalid image format")

Feature 2 — age estimation:
- age_on_id is None → return 400 with error "Missing required field: age_on_id"
- Face crop too small for age model → ModelInferenceError("Model inference failed")

Feature 3 — document authenticity:
- Perspective correction fails → PerspectiveCorrectionError("Document perspective correction failed")
- YOLO detects zero zones → ZoneDetectionError("No document zones detected")
- Country not matched to any template → return deviation_score: 1.0, country_matched: "unknown", within_tolerance: false
- EfficientNet score between LOW_CONFIDENCE_BOUNDARY and CLASSIFIER_REAL_THRESHOLD → return result with low_confidence: true

#######################################################

## Section 4: Code Style & Naming

These rules are strict. Both contributors must follow them exactly.
When in doubt, default to PEP 8.
Python version: 3.11+
Uvicorn must always be run from the project root — never from inside backend/

---

### 4.1 Naming conventions

**Python — variables and functions:**
- Always snake_case
- Names must be descriptive — never x, tmp, data, result, val
- Good: id_face_embedding, similarity_score, corrected_image
- Bad: emb, res, img2, temp

**Python — classes:**
- Always PascalCase
- Named after what they do, not what they contain
- Good: FaceVerifier, DocumentAuthenticator, AgeEstimator
- Bad: FaceModel, DocClass, Model3

**Python — constants:**
- Always UPPER_SNAKE_CASE
- Must live in backend/config.py only — never inside functions or model files
- Good: SIMILARITY_THRESHOLD = 0.6
- Bad: threshold = 0.6 defined anywhere other than config.py

**Python — files:**
- Always snake_case
- Good: face_verify.py, doc_auth.py, preprocessing.py
- Bad: model.py, feature3.py, utils2.py

**FastAPI routes:**
- URL paths always lowercase with hyphens: /verify-face, /estimate-age, /check-document
- Never camelCase or underscores in URLs: not /verifyFace, not /verify_face

**JavaScript — variables and functions:**
- Always camelCase
- Good: captureIdPhoto, similarityScore, displayError
- Bad: capture_id, sim_score, err

**JavaScript — constants:**
- Always UPPER_SNAKE_CASE
- Good: const MAX_FILE_SIZE = 5000000
- Bad: let maxSize = 5000000

---

### 4.2 Type hints
Every function and method must have full type hints on inputs and outputs.
No exceptions — untyped functions will not be accepted.
Use Python 3.11+ syntax: list[str] not List[str], str | None not Optional[str].

```python
# correct
def compute_similarity(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:

def load_model(weights_path: str) -> torch.nn.Module:

def correct_perspective(image: np.ndarray) -> np.ndarray:

# wrong
def compute_similarity(a, b):
```

**Pydantic schemas — backend/schemas.py — owned by Giorgia:**

```python
from pydantic import BaseModel

class VerifyRequest(BaseModel):
    id_image: str
    live_image: str

class AgeRequest(BaseModel):
    live_image: str
    age_on_id: int | None = None  # None triggers our 400, not FastAPI's 422

class DocumentRequest(BaseModel):
    id_image: str
```

---

### 4.3 Docstrings
Every class and every public function must have a docstring in this format:

```python
def compute_similarity(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    """
    Compute cosine similarity between two face embeddings.

    Args:
        embedding_a: Face embedding vector from ID photo, shape (512,)
        embedding_b: Face embedding vector from live photo, shape (512,)

    Returns:
        Cosine similarity score between 0.0 and 1.0

    Raises:
        ModelInferenceError: If either embedding is None or wrong shape
    """
```

One-liner only for functions under 5 lines:

```python
def normalize(embedding: np.ndarray) -> np.ndarray:
    """Normalize embedding vector to unit length."""
```

---

### 4.4 Import ordering
Always follow this order with a blank line between each group:

```python
# 1. Standard library
import os
import json
from pathlib import Path

# 2. Third-party
import numpy as np
import torch
import cv2
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# 3. Local — always full path from project root
from backend.config import SIMILARITY_THRESHOLD
from backend.schemas import VerifyRequest
from backend.utils.exceptions import ZoneDetectionError
from backend.dependencies import doc_authenticator
```

Rules:
- Never import *
- Never import inside a function unless absolutely necessary — if you must, comment why
- Always use full path: backend.models.doc_auth, never just doc_auth

---

### 4.5 Model class structure
Every model file must follow this exact structure:

```python
class DocumentAuthenticator:
    """
    Authenticates ID documents using perspective correction,
    zone detection, geometric analysis, and binary classification.
    """

    def __init__(self, weights_path: str) -> None:
        """Load all models at startup. Raises FileNotFoundError if weights missing."""
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Weights file not found: {weights_path}. "
                f"Download and place in backend/weights/ before starting the server."
            )
        self.model = self._load_model(weights_path)

    def _load_model(self, weights_path: str) -> torch.nn.Module:
        """Load EfficientNet-B0 weights from disk."""
        ...

    def run(self, image: np.ndarray) -> dict:
        """
        Run full document authenticity pipeline.

        Args:
            image: Raw ID document image, shape (H, W, 3), BGR format

        Returns:
            Dict matching Feature 3 response shape in Section 1.2

        Raises:
            PerspectiveCorrectionError: If perspective fix fails
            ZoneDetectionError: If YOLO detects zero zones
            ModelInferenceError: If EfficientNet inference fails
        """
        ...

    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """Correct document perspective using homography."""
        ...
```

Rules:
- __init__ always checks weights exist and raises FileNotFoundError with clear message if not
- Models loaded once in __init__ — never reloaded per request
- Main inference method always called run() — no alternatives
- Private helpers always prefixed with _
- No FastAPI, JSONResponse, or schema imports inside model files — ever
- Model files never read from disk during run() — only during __init__

---

### 4.6 Model instantiation — backend/dependencies.py
Model instances live here — never in main.py, never inside routes.
This prevents circular imports.
Owned by Giorgia. Created before any route file is written.
Each model wrapped in try/except so one missing weights file
does not prevent the others from loading.

```python
# backend/dependencies.py
import os
from backend.models.doc_auth import DocumentAuthenticator
from backend.models.face_verify import FaceVerifier
from backend.models.age_model import AgeEstimator
from backend.config import WEIGHTS_DIR

def _load(cls, path: str):
    """Load a model instance, return None if weights file is missing."""
    try:
        return cls(weights_path=path)
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        return None

doc_authenticator = _load(DocumentAuthenticator, f"{WEIGHTS_DIR}/efficientnet.pth")
face_verifier = _load(FaceVerifier, f"{WEIGHTS_DIR}/arcface.pth")
age_estimator = _load(AgeEstimator, f"{WEIGHTS_DIR}/dex.pth")
```

Routes import from dependencies.py — never from main.py:

```python
from backend.dependencies import doc_authenticator
```

Every route checks for None before calling run():

```python
if doc_authenticator is None:
    return JSONResponse(
        status_code=503,
        content={"success": False, "data": None, "error": "Model not loaded — weights file missing"}
    )
```

---

### 4.7 Async rules
PyTorch and OpenCV are blocking. Running them inside async def freezes the entire server.

Rules:
- Route functions that call ML models must use def, not async def
- FastAPI runs def routes in a thread pool automatically — this is correct and safe
- Never use time.sleep() anywhere

```python
# correct
@router.post("/check-document")
def check_document(request: DocumentRequest):
    ...

# wrong — freezes the server
@router.post("/check-document")
async def check_document(request: DocumentRequest):
    result = doc_authenticator.run(image)
```

---

### 4.8 Shared utilities — backend/utils/preprocessing.py
Owned by Giorgia. Created and pushed before Yara writes any route code.
Yara imports from here — she never re-implements these functions.

```python
def decode_base64_image(encoded: str) -> np.ndarray:
    """Decode a base64 JPEG string into a BGR numpy array."""

def encode_image_to_base64(image: np.ndarray) -> str:
    """Encode a BGR numpy array to a base64 JPEG string."""

def resize_image(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize image to target dimensions."""
```

---

### 4.9 Constants — backend/config.py
Owned by Giorgia. Created before any model file is written.
Uses absolute path construction — safe regardless of where uvicorn is run from.

```python
# backend/config.py
import os
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Face verification
SIMILARITY_THRESHOLD: float = 0.6          # below this score → suspicious
FACE_DETECTION_CONFIDENCE: float = 0.9     # min RetinaFace confidence to accept detection

# Age estimation
MAX_AGE_GAP: int = 5                        # gap in years before consistency flag raised

# Document authenticity
GEOMETRIC_TOLERANCE: float = 0.15          # max deviation from country template
CLASSIFIER_REAL_THRESHOLD: float = 0.7     # EfficientNet score above this → real
LOW_CONFIDENCE_BOUNDARY: float = 0.6       # scores 0.6-0.7 → real but low_confidence: true
                                            # CLASSIFIER_REAL_THRESHOLD = real/fake decision
                                            # LOW_CONFIDENCE_BOUNDARY = uncertainty flag only
                                            # these are intentionally different values
SUPPORTED_COUNTRIES: list[str] = ["spain", "portugal", "france", "germany", "switzerland", "uk"]

# Paths — always absolute, always safe
WEIGHTS_DIR: str = str(BASE_DIR / "backend" / "weights")
TEMPLATES_DIR: str = str(BASE_DIR / "data" / "templates")
```

Never hardcode a threshold or path anywhere else.

---

### 4.10 Comments
Write comments to explain why, not what.

```python
# correct — explains a non-obvious decision
# ArcFace embeddings are L2-normalized so dot product equals cosine similarity
similarity = float(np.dot(embedding_a, embedding_b))

# wrong — states the obvious
# compute dot product
similarity = float(np.dot(embedding_a, embedding_b))
```

Rules:
- Every threshold value must have a comment explaining why it was chosen
- Never leave TODO comments in pushed code — fix it or document it in RULES.md
- Never commit commented-out code — git preserves history
- Never write a comment that just restates what the next line does

---

### 4.11 JavaScript style (camera.js)
- Always const for fixed values, let for mutable — never var
- Always async/await — never .then().catch() chains
- All API calls wrapped in try/catch
- Always check response.ok before reading body
- Always read result.error — never result.detail
- Camera errors must always be caught and displayed — never silently ignored

```javascript
// API call pattern — always follow this exactly
async function verifyIdentity(idImage, liveImage) {
    try {
        const response = await fetch('/verify-face', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_image: idImage, live_image: liveImage })
        });
        const result = await response.json();
        if (!result.success) {
            displayError(getDisplayError(result.error));
            return;
        }
        displayResult(result.data);
    } catch (err) {
        displayError(getDisplayError("Unexpected server error"));
        console.error('Fetch failed:', err);
    }
}

// Camera pattern — always handle failures
async function startCamera(facingMode) {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: facingMode }
        });
        videoElement.srcObject = stream;
    } catch (err) {
        displayError("Camera access denied — please allow camera permission and refresh");
        console.error('Camera error:', err);
    }
}
```

---

### 5.7 Recovering from an accidental commit to main
If you accidentally commit directly to main, do not panic and do not push.
Follow these steps immediately:

```bash
# undo the last commit but keep your changes as uncommitted files
git reset --soft HEAD~1

# now create a proper branch and move your work there
git checkout -b feature/your-branch-name
git add .
git commit -m "feat: your proper commit message"
git push origin feature/your-branch-name
```

If you already pushed to main by accident:
1. Stop immediately — do not push anything else
2. Message Yara so she does not pull
3. Run this to revert the push:
```bash
git revert HEAD
git push origin main
```
Never use git reset --hard on main after pushing — it rewrites history and breaks Yara's local repo.

---

### 5.8 Adding a new package to requirements.txt
Follow this exact sequence — never install a package without updating requirements.txt:

```bash
# 1. tell Yara you are adding a package before doing anything
# 2. install it
pip install package-name

# 3. update requirements.txt immediately
pip freeze > requirements.txt

# 4. commit and push right away — do not bundle with other changes
git add requirements.txt
git commit -m "chore: add package-name to requirements"
git push origin main

# 5. tell Yara to pull and run:
pip install -r requirements.txt
```

Rules:
- Never install a package without adding it to requirements.txt in the same session
- Never bundle a requirements.txt update with feature code — always a separate commit
- If a package causes a conflict with existing ones, resolve it before pushing

---

### 5.9 Code freeze before demo
48 hours before the presentation, the codebase enters code freeze.

Code freeze rules:
- No new features — only critical bug fixes allowed
- Every bug fix still goes through a PR and review
- No changes to requirements.txt
- No changes to RULES.md
- No changes to backend/config.py thresholds — demo results must be reproducible
- Both contributors must have a working local version running end-to-end before freeze begins

To mark the freeze point in git:
```bash
git checkout main
git pull origin main
git tag -a v1.0-demo -m "demo-ready version"
git push origin v1.0-demo
```

---

### 5.10 Tagging a release
When a meaningful milestone is reached, tag it so you can always return to it.

```bash
# create an annotated tag
git tag -a v0.1-foundation -m "foundation files complete"
git tag -a v0.2-feature3 -m "document authenticity complete"
git tag -a v0.3-features1-2 -m "face verify and age estimation complete"
git tag -a v1.0-demo -m "demo-ready version"

# push tags to GitHub
git push origin --tags
```

To return to a tagged version if something breaks:
```bash
git checkout v1.0-demo
```

---

### 5.11 Pull request description template
Every PR must include this description — copy and fill it in when opening the PR on GitHub:

```
## What changed
Brief description of what this PR adds or fixes.

## How to test it
Steps to verify it works locally — e.g. "run uvicorn, send this request, expect this response"

## Known issues or limitations
Anything incomplete, hardcoded, or temporarily skipped.

## Checklist
- [ ] Follows all naming conventions from Section 4
- [ ] All functions have type hints and docstrings
- [ ] No hardcoded thresholds or paths
- [ ] No committed weights or venv files
- [ ] requirements.txt updated if new packages added
- [ ] Tested locally end-to-end before opening PR
```

---

### 5.12 What requires a PR review vs what can be self-merged
Not everything needs a full review. Use this to decide:

Requires review from the other person:
- Any new model file or route file
- Any change to backend/schemas.py, backend/dependencies.py, backend/config.py
- Any change to backend/main.py
- Any change to requirements.txt
- Any frontend change that affects how API responses are read or displayed
- Any change that touches a file owned by the other person

Can be self-merged without review:
- Fixing a typo in a comment or docstring
- Adding or updating a notebook
- Adding test scenario images to data/test_scenarios/
- Updating RULES.md with agreed changes
- README updates

When in doubt — ask before merging.