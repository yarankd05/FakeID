#third-party
import numpy as np

#local
from backend.config import SIMILARITY_THRESHOLD


def cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    """
    Compute cosine similarity between two embedding vectors.

    Args:
        vector_a: first embedding vector
        vector_b: second embedding vector

    Returns:
        cosine similarity score between -1 and 1, where 1 = identical
    """
    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    #ArcFace embeddings are L2-normalized so this equals cosine similarity
    return float(np.dot(vector_a, vector_b) / (norm_a * norm_b))


def get_verdict(score: float) -> str:
    """
    Return verified or suspicious based on cosine similarity score.

    Args:
        score: cosine similarity score between 0 and 1

    Returns:
        'verified' if score >= SIMILARITY_THRESHOLD, else 'suspicious'
    """
    #SIMILARITY_THRESHOLD = 0.6 from config — tuned on LFW evaluation
    return "verified" if score >= SIMILARITY_THRESHOLD else "suspicious"