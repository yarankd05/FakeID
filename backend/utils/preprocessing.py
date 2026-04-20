import base64

import cv2
import numpy as np


def decode_base64_image(encoded: str) -> np.ndarray:
    """
    Decode a base64 JPEG string into a BGR numpy array.

    Args:
        encoded: Base64 encoded JPEG string

    Returns:
        BGR image as numpy array, shape (H, W, 3)

    Raises:
        InvalidImageError: If the string cannot be decoded into a valid image
    """
    from backend.utils.exceptions import InvalidImageError

    try:
        image_bytes = base64.b64decode(encoded)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidImageError("Invalid image format")
        return image
    except Exception:
        raise InvalidImageError("Invalid image format")


def encode_image_to_base64(image: np.ndarray) -> str:
    """
    Encode a BGR numpy array to a base64 JPEG string.

    Args:
        image: BGR image as numpy array, shape (H, W, 3)

    Returns:
        Base64 encoded JPEG string
    """
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")


def resize_image(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """
    Resize image to target dimensions.

    Args:
        image: BGR image as numpy array
        width: Target width in pixels
        height: Target height in pixels

    Returns:
        Resized BGR image as numpy array
    """
    return cv2.resize(image, (width, height))