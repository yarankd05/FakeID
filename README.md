# FakeID — AI-Powered Identity Verification

> *The night is young, but not too young.*

A deep learning prototype for nightclub ID verification built for the AI-Machine Learning & Analytics course at IE University (Academic Year 25-26).

## Team

| Name | Role |
|------|------|
| Giorgia Merli | Feature 3: Document Authenticity, Report Architecture & Technical Writing |
| Yara El Nakadi | Features 1 & 2: Face Verification & Age Estimation, Frontend, Presentation |
| Shams Badra | Business Analysis, Market Research & Dataset Annotation |
| Dulce Gómez Sanmartín | Executive Report, Presentation & Dataset Annotation |
| Chrysi Karageorgiou | Viability Analysis, Financial Modelling & Dataset Annotation |
| Maria Pereira | Market Research, Competitive Analysis & Dataset Annotation |
| Arrieta Zubialde | Presentation, Demo Preparation & Dataset Annotation |

## System Overview

FakeID verifies identity at nightclub entrances using a three-feature pipeline:

- **Feature 1 — Face Verification:** Compares the face on the ID document against a live photo using RetinaFace detection and ArcFace embeddings
- **Feature 2 — Age Estimation:** Estimates age from a live photo using the DEX model and checks consistency with the age declared on the ID
- **Feature 3 — Document Authenticity:** 4-layer pipeline (perspective correction → YOLO zone detection → geometric analysis → EfficientNet-B0 classifier) to detect fake Spanish DNI documents

Prototype targets Spanish DNI 3.0 format. Dataset: MIDV-2020 (Bulatov et al., Computer Optics, 2022).

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/yarankd05/FakeID.git
cd FakeID
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Weight Files

Model weights are not included in this repository due to file size. Download them here:

**[Download weights from Google Drive](https://drive.google.com/drive/folders/1U69EkMxtZ9_WS6XD4ZvLsaibl5wtFJ01?usp=sharing)**

Place both files in `backend/weights/`:

| File | Size | Description |
|------|------|-------------|
| `yolo_zones.pt` | 6.2 MB | YOLO zone detector, custom trained on MIDV-2020 |
| `efficientnet.pth` | 16 MB | EfficientNet-B0 binary classifier |

DeepFace weights (ArcFace, DEX) are downloaded automatically on first use. The first request to `/api/verify-face` or `/api/estimate-age` will take longer while weights download.

## Running the Server

```bash
cd FakeID
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Wait for `Application startup complete.` then open `http://localhost:8000` in a browser.

To access from a phone on the same network, find your machine's local IP address and open `http://<your-ip>:8000` in the phone browser.

## Project Structure

| Path | Description |
|------|-------------|
| `backend/models/doc_auth.py` | Feature 3 — 4-layer document authenticity pipeline |
| `backend/models/face_verify.py` | Feature 1 — ArcFace face verification |
| `backend/models/age_model.py` | Feature 2 — DEX age estimation |
| `backend/routes/document.py` | POST /api/check-document |
| `backend/routes/verify.py` | POST /api/verify-face |
| `backend/routes/age.py` | POST /api/estimate-age |
| `backend/config.py` | All thresholds and constants |
| `backend/dependencies.py` | Model loading at startup |
| `backend/schemas.py` | Pydantic request models |
| `frontend/index.html` | Single-page mobile-first UI |
| `frontend/camera.js` | Camera capture and API calls |
| `data/templates/spain.json` | Scan reference coordinates (tolerance 0.08) |
| `data/templates/spain_photo.json` | Photo reference coordinates (tolerance 0.25) |
| `notebooks/feature3_eval.ipynb` | Feature 3 evaluation — YOLO + EfficientNet metrics |
| `notebooks/feature1_eval.ipynb` | Feature 1 evaluation — face verification metrics |
| `notebooks/feature2_eval.ipynb` | Feature 2 evaluation — age estimation metrics |

## API Endpoints

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/verify-face` | POST | `id_image`, `live_image` (base64 JPEG) | Face match verdict + similarity score |
| `/api/estimate-age` | POST | `live_image` (base64 JPEG), `age_on_id` (int) | Age consistency flag + gap |
| `/api/check-document` | POST | `id_image` (base64 JPEG) | 4-layer authenticity verdict |

All responses follow the envelope: `{"success": true, "data": {...}, "error": null}`

## Feature 3 — Document Authenticity Pipeline

The pipeline detects whether the input is a flatbed scan or a phone photo, then applies the appropriate processing path.

**Scan path** (A4 aspect ratio + resolution above 2400px)

1. Layer 1: Canny contour crop with 4-corner perspective correction (94/100 success rate)
2. Layer 2: YOLOv8n zone detection on original image
3. Layer 3: Geometric analysis against `spain.json` with tolerance 0.08
4. Layer 4: EfficientNet-B0 classifier on original image

**Photo path** (phone photos)

1. Layer 1: YOLO-World zero-shot card detection and crop
2. Layer 2: YOLOv8n zone detection on original image
3. Layer 3: Geometric analysis against `spain_photo.json` with tolerance 0.25
4. Layer 4: EfficientNet-B0 classifier on original image

Final verdict: `real` / `fake` / `suspicious`

## Model Performance

| Model | Metric | Value |
|-------|--------|-------|
| YOLOv8n zone detector | mAP50 overall | 0.859 |
| YOLOv8n zone detector | mAP50 id_number | 0.801 |
| YOLOv8n zone detector | mAP50 photo_zone | 0.873 |
| YOLOv8n zone detector | mAP50 text_fields | 0.903 |
| EfficientNet-B0 | Test accuracy | 0.9769 |
| EfficientNet-B0 | Test precision | 0.8824 |
| EfficientNet-B0 | Test recall | 0.7895 |

## Known Limitations

- Prototype supports Spanish DNI 3.0 only
- 18% false positive rate on portrait-orientation phone photos where the card occupies less than 30% of the frame — mitigated by the frontend retake gate
- EfficientNet was trained on full original images; a retrained version on standardised crops is documented as future work
- DeepFace weights download automatically on first use — first inference request will be slow

## Dataset

K.B. Bulatov, E.V. Emelianova, D.V. Tropin, N.S. Skoryukina, Y.S. Chernyshova, A.V. Konev, A.S. Usilin.
*MIDV-2020: A Comprehensive Benchmark Dataset for Identity Document Analysis.*
Computer Optics, 2022. DOI: 10.18287/2412-6179-CO-1006

Raw dataset images are not included in this repository and must not be redistributed. Academic use only.
