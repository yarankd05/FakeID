import numpy as np

def cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    """
    Computes cosine similarity between two embedding vectors.
    Returns a value between -1 and 1, where 1 = identical.
    """
    dot_product = np.dot(vector_a, vector_b)
    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))


def similarity_to_percentage(similarity: float) -> float:
    """
    Converts cosine similarity score to a percentage.
    """
    return round(similarity * 100, 2)


def get_verdict(score: float, threshold: float = 65.0) -> str:
    """
    Returns verified or suspicious based on score and threshold.
    """
    return "verified" if score >= threshold else "suspicious"