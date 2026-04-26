# FakeID: AI-Powered Identity Verification
**The night is young, but not too young.**

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
- **Feature 3 — Document Authenticity:** 4-layer pipeline (perspective correction, YOLO zone detection, geometric analysis, MRZ checksum validation) to detect fake ID documents and verify holder age

Prototype targets Spanish DNI 3.0 format for zone detection and MIDV-2020 passport subset (Azerbaijan, Greece, Serbia) for MRZ verification. Dataset: MIDV-2020 (Bulatov et al., Computer Optics, 2022).

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

Model weights are not included in this repository due to file size. Download all weights from the shared Google Drive folder:

[Download weights from Google Drive](https://drive.google.com/drive/folders/1U69EkMxtZ9_WS6XD4ZvLsaibl5wtFJ01?usp=sharing)

Place all files in `backend/weights/`:

| File | Size | Description |
|------|------|-------------|
| `yolo_zones.pt` | 6.2 MB | YOLOv8n zone detector, custom trained on MIDV-2020 Spanish DNI |
| `best_mrz_v2.pt` | 5.9 MB | YOLOv8n MRZ zone detector, trained on MIDV-2020 passport subset |

DeepFace weights (ArcFace, DEX) are downloaded automatically on first use. The first request to `/api/verify-face` or `/api/estimate-age` will take longer while weights download.

## Running the Server

```bash
cd FakeID
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Wait for `Application startup complete.` then open http://localhost:8000 in a browser.

To access from a phone on the same network, find your machine's local IP address and open `http://<your-ip>:8000` in the phone browser.

## Project Structure

- `backend/`
  - `models/`
    - `doc_auth.py` — Feature 3: 4-layer document authenticity pipeline
    - `mrz_detector.py` — Feature 3: MRZ detection, OCR, ICAO checksum validation
    - `face_verify.py` — Feature 1: ArcFace face verification
    - `age_model.py` — Feature 2: DEX age estimation
  - `routes/`
    - `document.py` — POST /api/check-document
    - `verify.py` — POST /api/verify-face
    - `age.py` — POST /api/estimate-age
  - `config.py` — all thresholds and constants
  - `dependencies.py` — model loading at startup
  - `schemas.py` — Pydantic request models
- `frontend/`
  - `index.html` — single-page mobile-first UI
  - `style.css`
  - `camera.js`
- `data/templates/`
  - `spain.json` — scan reference coordinates (tolerance 0.08)
  - `spain_photo.json` — photo reference coordinates (tolerance 0.25)
- `notebooks/`
  - `fakeid-mrz-inference.ipynb` — MRZ detector training and inference demo
  - `feature3_eval.ipynb` — Feature 3 evaluation
  - `feature1_eval.ipynb` — Feature 1 evaluation
  - `feature2_eval.ipynb` — Feature 2 evaluation
- `requirements.txt`
- `README.md`

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

- Layer 1: Canny contour crop with 4-corner perspective correction (94/100 success rate)
- Layer 2: YOLOv8n zone detection on original image
- Layer 3: Geometric analysis against `spain.json` with tolerance 0.08
- Layer 4: MRZ zone detection + EasyOCR + ICAO checksum validation + age check

**Photo path** (phone photos)

- Layer 1: YOLO-World zero-shot card detection and crop
- Layer 2: YOLOv8n zone detection on original image
- Layer 3: Geometric analysis against `spain_photo.json` with tolerance 0.25
- Layer 4: MRZ zone detection + EasyOCR + ICAO checksum validation + age check

**Final verdict:** `real` / `fake` / `underage` / `suspicious`

## Notebooks

### MRZ Detector — Training and Inference

**File:** `notebooks/fakeid-mrz-inference.ipynb`
**Platform:** Kaggle (T4 GPU recommended)

To run inference only (no retraining needed):

1. Download `best_mrz_v2.pt` from the Google Drive weights folder above
2. Upload it to a Kaggle dataset and attach it to the notebook as input
3. Update the `WEIGHTS` path in Section 5 to match your dataset path
4. Run Section 0 (install dependencies) and Section 5 (demo) only

To retrain from scratch:

1. Download the MIDV-2020 passport subset (Azerbaijan, Greece, Serbia) — see Dataset section below for access instructions
2. Ensure `dataset.yaml` points to the correct train/val paths
3. Attach the dataset and run all cells in order from Section 0
4. Trained weights will be saved to `/kaggle/working/nightverify_mrz/mrz_detector/weights/best.pt`

> **Note:** MIDV-2020 cannot be redistributed per its licence. Training cells are documentation of the original run and cannot be rerun without downloading the dataset independently.

## Model Performance

| Model | Metric | Value |
|-------|--------|-------|
| YOLOv8n zone detector | mAP50 overall | 0.859 |
| YOLOv8n zone detector | mAP50 id_number | 0.801 |
| YOLOv8n zone detector | mAP50 photo_zone | 0.873 |
| YOLOv8n zone detector | mAP50 text_fields | 0.903 |
| YOLOv8n MRZ detector | mAP50 | 0.983 |
| YOLOv8n MRZ detector | mAP50-95 | 0.487 |
| YOLOv8n MRZ detector | Precision | 0.848 |
| YOLOv8n MRZ detector | Recall | 1.000 |
| YOLOv8n MRZ detector | Inference speed | 9.4ms/image (T4 GPU) |

## Known Limitations

- Prototype supports Spanish DNI 3.0 for zone detection and MIDV-2020 passports (Azerbaijan, Greece, Serbia) for MRZ verification
- 18% false positive rate on portrait-orientation phone photos where the card occupies less than 30% of the frame, mitigated by the frontend retake gate
- EasyOCR accuracy is lower on synthetic MIDV-2020 template scans than on real passport photos — documented limitation
- DeepFace weights download automatically on first use; first inference request will be slow

## Dataset

MIDV-2020 — K.B. Bulatov, E.V. Emelianova, D.V. Tropin, N.S. Skoryukina, Y.S. Chernyshova, A.V. Konev, A.S. Usilin. MIDV-2020: A Comprehensive Benchmark Dataset for Identity Document Analysis. Computer Optics, 2022. DOI: 10.18287/2412-6179-CO-1006

How to obtain the dataset:

1. Visit the dataset page: http://l3i-share.univ-lr.fr/MIDV2020/midv2020.html
2. Fill in the registration form to request access
3. You will receive download credentials by email
4. Use FileZilla or any SFTP client to connect to `sftp://l3i-share.univ-lr.fr`
5. Download the Spanish DNI subset (`esp_id`) and passport subsets (`aze_passport`, `grc_passport`, `srb_passport`)

Folders used in this project:

| Folder | Contents | Used for |
|--------|----------|----------|
| `scan_upright/images/esp_id/` | 100 flatbed scan images | YOLO zone detector training |
| `photo/images/esp_id/` | 100 phone photo images | YOLO zone detector training |
| `templates/images/esp_id/` | 100 clean template images | Geometric analysis reference only |
| `photo/images/aze_passport/` | Azerbaijan passport images | MRZ detector training |
| `photo/images/grc_passport/` | Greece passport images | MRZ detector training |
| `photo/images/srb_passport/` | Serbia passport images | MRZ detector training |

Raw dataset images are not included in this repository and must not be redistributed. Academic use only.
