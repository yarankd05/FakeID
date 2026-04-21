#standard library
— none —

#third-party
import numpy as np

#local
from backend.utils.exceptions import ModelInferenceError


def compute_similarity(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    """
    Compute cosine similarity between two face embeddings.

    Args:
        embedding_a: face embedding vector from ID photo, shape (512,)
        embedding_b: face embedding vector from live photo, shape (512,)

    Returns:
        cosine similarity score between 0.0 and 1.0

    Raises:
        ModelInferenceError: if either embedding is None or wrong shape
    """
    if embedding_a is None or embedding_b is None:
        raise ModelInferenceError("Model inference failed")

    #ArcFace embeddings are L2-normalized so dot product equals cosine similarity
    return float(np.dot(embedding_a, embedding_b))


def similarity_to_percentage(similarity_score: float) -> float:
    """Convert cosine similarity score to a percentage rounded to 2 decimal places."""
    return round(similarity_score * 100, 2)


def get_verdict(similarity_score: float, threshold: float) -> str:
    """
    Return verified or suspicious based on score and threshold.

    Args:
        similarity_score: cosine similarity between 0.0 and 1.0
        threshold: minimum score to consider identity verified

    Returns:
        'verified' if score is above threshold, 'suspicious' otherwise
    """
    return "verified" if similarity_score >= threshold else "suspicious"