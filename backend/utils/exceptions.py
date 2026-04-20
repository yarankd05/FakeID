class FaceNotDetectedError(Exception):
    """Raised when no face is detected in an input image."""
    pass


class DocumentNotDetectedError(Exception):
    """Raised when no document is detected in the input image."""
    pass


class PerspectiveCorrectionError(Exception):
    """Raised when OpenCV fails to correct document perspective."""
    pass


class ZoneDetectionError(Exception):
    """Raised when YOLO detects zero zones on the document."""
    pass


class ModelInferenceError(Exception):
    """Raised when a model fails during inference."""
    pass


class InvalidImageError(Exception):
    """Raised when the input image is corrupt, empty, or unreadable."""
    pass


class ModelNotLoadedError(Exception):
    """Raised when a model instance is None at inference time."""
    pass