import os

from backend.config import WEIGHTS_DIR
from backend.models.doc_auth import DocumentAuthenticator

from backend.models.face_verify import FaceVerifier
from backend.models.age_model import AgeEstimator


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


doc_authenticator = _load(DocumentAuthenticator, f"{WEIGHTS_DIR}/efficientnet.pth")

face_verifier = _load(FaceVerifier, f"{WEIGHTS_DIR}/arcface.pth")
age_estimator = _load(AgeEstimator, f"{WEIGHTS_DIR}/dex.pth")