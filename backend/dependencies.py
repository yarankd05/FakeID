# standard library
import os
from pathlib import Path

# local
from backend.config import WEIGHTS_DIR
from backend.models.doc_auth import DocumentAuthenticator
from backend.models.face_verify import FaceVerifier
from backend.models.age_model import AgeEstimator

# DeepFace manages its own weights at ~/.deepface/weights/
# do not move these — DeepFace expects them in this exact location
DEEPFACE_WEIGHTS: str = str(Path.home() / ".deepface" / "weights")


def _load(cls: type, path: str) -> object | None:
    """
    Load a model instance, return None if weights or module file is missing.

    Args:
        cls: Model class to instantiate
        path: Absolute path to weights file

    Returns:
        Instantiated model or None if loading fails
    """
    try:
        return cls(weights_path=path)
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        return None
    except ImportError as e:
        print(f"WARNING: model module not found — {e}")
        return None


def _load_doc_authenticator() -> object | None:
    """
    Load DocumentAuthenticator with both required weight files.
    Returns None if either weights file is missing.

    Returns:
        Instantiated DocumentAuthenticator or None if loading fails
    """
    yolo_path = f"{WEIGHTS_DIR}/yolo_zones.pt"
    efficientnet_path = f"{WEIGHTS_DIR}/efficientnet.pth"
    try:
        return DocumentAuthenticator(
            yolo_path=yolo_path,
            efficientnet_path=efficientnet_path
        )
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        return None
    except ImportError as e:
        print(f"WARNING: model module not found — {e}")
        return None


doc_authenticator = _load_doc_authenticator()
face_verifier = _load(FaceVerifier, f"{DEEPFACE_WEIGHTS}/arcface_weights.h5")
age_estimator = _load(AgeEstimator, f"{DEEPFACE_WEIGHTS}/dex_chalearn_iccv2015.h5")