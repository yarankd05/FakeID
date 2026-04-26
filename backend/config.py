import os
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Face verification
SIMILARITY_THRESHOLD: float = 0.4      # below this score → suspicious
FACE_DETECTION_CONFIDENCE: float = 0.9     # min RetinaFace confidence to accept detection

# Age estimation
MAX_AGE_GAP: int = 5                        # gap in years before consistency flag raised

# Document authenticity
GEOMETRIC_TOLERANCE_SCAN: float = 0.08     # max deviation for flatbed scans (tight — consistent crops)
GEOMETRIC_TOLERANCE_PHOTO: float = 0.25    # max deviation for phone photos (loose — high positional variance)
CLASSIFIER_REAL_THRESHOLD: float = 0.7     # EfficientNet score above this → real
LOW_CONFIDENCE_BOUNDARY: float = 0.6       # scores 0.6-0.7 → real but low_confidence: true
                                            # CLASSIFIER_REAL_THRESHOLD = real/fake decision
                                            # LOW_CONFIDENCE_BOUNDARY = uncertainty flag only
                                            # these are intentionally different values
                                            #
                                            # full three-zone classification logic:
                                            # score < 0.6  → fake, low_confidence: false
                                            # score 0.6-0.7 → real, low_confidence: true
                                            # score > 0.7  → real, low_confidence: false

SUPPORTED_COUNTRIES: list[str] = ["spain"]  # prototype targets Spain only — extend later

# Paths — always absolute, always safe
WEIGHTS_DIR: str = str(BASE_DIR / "backend" / "weights")
TEMPLATES_DIR: str = str(BASE_DIR / "data" / "templates")

# MRZ verification
MRZ_MODEL_PATH: Path = BASE_DIR / "backend" / "weights" / "best_mrz_v2.pt"
MRZ_MIN_LINE_LENGTH: int = 20
MRZ_PADDING: int = 120
MRZ_MIN_AGE: int = 18