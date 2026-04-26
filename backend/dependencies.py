# standard library
import os
from pathlib import Path

# third-party
import easyocr
from ultralytics import YOLO

# local
from backend.config import MRZ_MODEL_PATH, WEIGHTS_DIR
from backend.models.doc_auth import DocumentAuthenticator
from backend.models.face_verify import FaceVerifier
from backend.models.age_model import AgeEstimator

# DeepFace manages its own weights at ~/.deepface/weights/
# do not move these — DeepFace expects them in this exact location
DEEPFACE_WEIGHTS: str = str(Path.home() / ".deepface" / "weights")


def _load(cls: type, path: str) -> object | None:
    """Load a model instance, return None if weights or module file is missing.

    Args:
        cls:  Model class to instantiate.
        path: Absolute path to weights file.

    Returns:
        Instantiated model or None if loading fails.
    """
    try:
        return cls(weights_path=path)
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        return None
    except ImportError as e:
        print(f"WARNING: model module not found — {e}")
        return None


def _load_mrz_models() -> tuple | None:
    """Load YOLOv8 MRZ detector and EasyOCR reader.

    Returns:
        Tuple of (YOLO model, easyocr.Reader) or None if loading fails.
    """
    try:
        mrz_model  = YOLO(str(MRZ_MODEL_PATH))
        mrz_reader = easyocr.Reader(["en"], gpu=False)
        return mrz_model, mrz_reader
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        return None
    except ImportError as e:
        print(f"WARNING: model module not found — {e}")
        return None


def _load_doc_authenticator() -> object | None:
    """Load DocumentAuthenticator with YOLO zone detector and MRZ models.

    Returns:
        Instantiated DocumentAuthenticator or None if loading fails.
    """
    yolo_path = f"{WEIGHTS_DIR}/yolo_zones.pt"
    try:
        mrz = mrz_models
        if mrz is None:
            print("WARNING: MRZ models not loaded")
            return None
        return DocumentAuthenticator(
            yolo_path=yolo_path,
            mrz_model=mrz[0],
            mrz_reader=mrz[1],
        )
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        return None
    except ImportError as e:
        print(f"WARNING: model module not found — {e}")
        return None


# load order matters — mrz_models must be set before _load_doc_authenticator runs
mrz_models        = _load_mrz_models()
doc_authenticator = _load_doc_authenticator()
face_verifier     = _load(FaceVerifier, f"{DEEPFACE_WEIGHTS}/arcface_weights.h5")
age_estimator     = _load(AgeEstimator, f"{DEEPFACE_WEIGHTS}/age_model_weights.h5")