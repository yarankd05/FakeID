import numpy as np
from retinaface import RetinaFace
from deepface import DeepFace


def detect_and_crop_face(image_path: str):
    """
    takes an image path, detects the face using retinaface,
    and returns the cropped face as a numpy array.
    returns none if no face is found.
    """
    try:
        faces = RetinaFace.extract_faces(image_path, align=True)

        if len(faces) == 0:
            return None

        # return the first face found — assumed to be the largest
        return faces[0]

    except Exception as e:
        return None


def get_embedding(image_path: str):
    """
    takes an image path and returns the arcface embedding vector.
    returns none if embedding fails.
    """
    try:
        embedding_result = DeepFace.represent(
            img_path=image_path,
            model_name="ArcFace",
            detector_backend="retinaface",
            enforce_detection=True
        )

        return np.array(embedding_result[0]["embedding"])

    except Exception as e:
        return None


def verify_faces(id_image_path: str, live_image_path: str):
    """
    takes two image paths (id photo and live photo),
    computes arcface embeddings for both,
    calculates cosine similarity,
    and returns a result dict with score and verdict.
    """
    embedding_id = get_embedding(id_image_path)
    embedding_live = get_embedding(live_image_path)

    if embedding_id is None:
        raise ValueError("could not detect face in id image")

    if embedding_live is None:
        raise ValueError("could not detect face in live image")

    # cosine similarity — measures angle between two embedding vectors
    dot_product = np.dot(embedding_id, embedding_live)
    norm_id = np.linalg.norm(embedding_id)
    norm_live = np.linalg.norm(embedding_live)
    similarity = dot_product / (norm_id * norm_live)

    # convert to percentage score
    score = round(float(similarity) * 100, 2)

    # 65% threshold — below this the faces are too different to confirm identity
    verdict = "verified" if score >= 65 else "suspicious"

    return {
        "verdict": verdict,
        "score": score,
        "id_face_found": True,
        "live_face_found": True
    }