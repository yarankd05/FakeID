# standard library
import os

# third-party
import numpy as np
from deepface import DeepFace

# local
from backend.config import MAX_AGE_GAP
from backend.utils.exceptions import FaceNotDetectedError, ModelInferenceError, InvalidImageError


class AgeEstimator:
    """
    Estimates age from a live face photo using the DEX model
    and checks consistency against the age declared on the ID.
    """

    def __init__(self, weights_path: str) -> None:
        """
        Load DEX model at startup.
        Raises FileNotFoundError if weights are missing.
        """
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Weights file not found: {weights_path}. "
                f"Download and place in backend/weights/ before starting the server."
            )

    def _estimate_age(self, image: np.ndarray) -> float:
        """
        Run DEX age estimation on a face image.

        Args:
            image: face image as numpy array, shape (H, W, 3), BGR format

        Returns:
            estimated age as float

        Raises:
            FaceNotDetectedError: if no face is found in the image
            ModelInferenceError: if age estimation fails
        """
        try:
            result = DeepFace.analyze(
                img_path=image,
                actions=["age"],
                detector_backend="retinaface",
                enforce_detection=True
            )
            return float(result[0]["age"])

        except ValueError as e:
            # retinaface found no face — enforce_detection=True raises ValueError
            raise FaceNotDetectedError(str(e))

        except Exception as e:
            raise ModelInferenceError(str(e))

    def run(self, live_image: np.ndarray, age_on_id: int) -> dict:
        """
        Run full age estimation pipeline.

        Args:
            live_image: live photo of person, shape (H, W, 3), BGR format
            age_on_id: age the bouncer typed in from the ID

        Returns:
            dict matching Feature 2 response shape from RULES.md Section 1.2

        Raises:
            FaceNotDetectedError: if no face found in live image
            ModelInferenceError: if age estimation fails
        """
        estimated_age = self._estimate_age(live_image)
        gap = abs(estimated_age - age_on_id)
        # gap above MAX_AGE_GAP means estimated age is too different from id age
        age_flag = gap > MAX_AGE_GAP

        return {
            "feature": "age_estimation",
            "layers": {
                "age_model": {
                    "estimated_age": round(estimated_age, 1)
                },
                "consistency": {
                    "id_age": age_on_id,
                    "estimated_age": round(estimated_age, 1),
                    "gap": round(gap, 1),
                    "flag": age_flag
                }
            }
        }