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
