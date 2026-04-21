#standard library
import os

#third-party
import numpy as np
from deepface import DeepFace

#local
from backend.config import SIMILARITY_THRESHOLD, FACE_DETECTION_CONFIDENCE, WEIGHTS_DIR
from backend.utils.exceptions import FaceNotDetectedError, ModelInferenceError, InvalidImageError


class FaceVerifier:
    """
    Verifies identity by comparing the face in an ID photo
    against a live photo using RetinaFace detection and ArcFace embeddings.
    """

    def __init__(self, weights_path: str) -> None:
        """
        Load ArcFace model at startup.
        Raises FileNotFoundError if weights are missing.
        """
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Weights file not found: {weights_path}. "
                f"Download and place in backend/weights/ before starting the server."
            )

    def _get_embedding(self, image: np.ndarray) -> np.ndarray:
        """
        Extract ArcFace embedding from a face image.

        Args:
            image: face image as numpy array, shape (H, W, 3), BGR format

        Returns:
            ArcFace embedding vector, shape (512,)

        Raises:
            FaceNotDetectedError: if no face is found in the image
            ModelInferenceError: if embedding extraction fails
        """
        try:
            embedding_result = DeepFace.represent(
                img_path=image,
                model_name="ArcFace",
                detector_backend="retinaface",
                enforce_detection=True
            )
            return np.array(embedding_result[0]["embedding"])

        except ValueError as e:
            #retinaface found no face — enforce_detection=True raises ValueError
            raise FaceNotDetectedError(str(e))

        except Exception as e:
            raise ModelInferenceError(str(e))

    def run(self, id_image: np.ndarray, live_image: np.ndarray) -> dict:
        """
        Run full face verification pipeline.

        Args:
            id_image: ID document photo, shape (H, W, 3), BGR format
            live_image: live photo of person, shape (H, W, 3), BGR format

        Returns:
            dict matching Feature 1 response shape from RULES.md Section 1.2

        Raises:
            FaceNotDetectedError: if no face found in either image
            ModelInferenceError: if embedding extraction fails
        """
        id_embedding = self._get_embedding(id_image)
        live_embedding = self._get_embedding(live_image)

        #ArcFace embeddings are L2-normalized so dot product equals cosine similarity
        similarity_score = float(np.dot(id_embedding, live_embedding))

        #score below threshold means faces are too different to confirm identity
        verdict = "verified" if similarity_score >= SIMILARITY_THRESHOLD else "suspicious"

        return {
            "feature": "face_verification",
            "layers": {
                "face_detection": {
                    "id_face_detected": True,
                    "live_face_detected": True
                },
                "similarity": {
                    "score": round(similarity_score, 4),
                    "label": verdict
                }
            }
        }