#standard library
import os
import json
from pathlib import Path

#third-party
import cv2
import numpy as np

#local
from backend.config import (
    GEOMETRIC_TOLERANCE,
    CLASSIFIER_REAL_THRESHOLD,
    LOW_CONFIDENCE_BOUNDARY,
    SUPPORTED_COUNTRIES,
    WEIGHTS_DIR,
    TEMPLATES_DIR
)
from backend.utils.exceptions import (
    PerspectiveCorrectionError,
    ZoneDetectionError,
    ModelInferenceError,
    InvalidImageError
)


class DocumentAuthenticator:
    """
    Authenticates ID documents using perspective correction,
    zone detection, geometric analysis, and binary classification.
    Trained on Spanish DNI 3.0 format using MIDV-2020 dataset.
    """

    def __init__(self, weights_path: str) -> None:
        """
        Load all models at startup.
        Raises FileNotFoundError if weights are missing.

        Args:
            weights_path: absolute path to EfficientNet weights file
        """
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Weights file not found: {weights_path}. "
                f"Download and place in backend/weights/ before starting the server."
            )
        self.classifier = self._load_classifier(weights_path)
        self.templates = self._load_templates()

    def _load_classifier(self, weights_path: str):
        """
        Load EfficientNet-B0 classifier weights from disk.

        Args:
            weights_path: absolute path to weights file

        Returns:
            loaded PyTorch model in eval mode
        """
        #placeholder — will be implemented in Phase 5
        return None

    def _load_templates(self) -> dict:
        """
        Load all country zone templates from data/templates/.

        Returns:
            dict mapping country name to zone position dict
        """
        templates = {}
        for country in SUPPORTED_COUNTRIES:
            template_path = os.path.join(TEMPLATES_DIR, f"{country}.json")
            if os.path.exists(template_path):
                with open(template_path, "r") as f:
                    templates[country] = json.load(f)
        return templates

    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """
        Detect document edges and correct perspective distortion.

        Args:
            image: raw input image, shape (H, W, 3), BGR format

        Returns:
            perspective-corrected image cropped to document bounds

        Raises:
            PerspectiveCorrectionError: if document edges cannot be detected
        """
        try:
            #convert to grayscale for edge detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            #apply gaussian blur to reduce noise before edge detection
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            #detect edges using canny
            edges = cv2.Canny(blurred, 75, 200)

            #find contours — looking for the document rectangle
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                raise PerspectiveCorrectionError(
                    "Document perspective correction failed"
                )

            #find the largest contour — assumed to be the document
            largest_contour = max(contours, key=cv2.contourArea)

            #approximate the contour to a polygon
            perimeter = cv2.arcLength(largest_contour, True)
            approximated = cv2.approxPolyDP(
                largest_contour, 0.02 * perimeter, True
            )

            #if we found a quadrilateral apply perspective transform
            if len(approximated) == 4:
                return self._apply_perspective_transform(image, approximated)

            #if not a clean quad, return original — perspective correction not needed
            return image

        except PerspectiveCorrectionError:
            raise
        except Exception as e:
            raise PerspectiveCorrectionError(
                "Document perspective correction failed"
            )

    def _apply_perspective_transform(
        self, image: np.ndarray, corners: np.ndarray
    ) -> np.ndarray:
        """
        Apply perspective transform to straighten document.

        Args:
            image: original image
            corners: 4 corner points of the document, shape (4, 1, 2)

        Returns:
            warped and cropped document image
        """
        #reshape corners to (4, 2)
        corners = corners.reshape(4, 2).astype(np.float32)

        #sort corners: top-left, top-right, bottom-right, bottom-left
        rect = self._order_corners(corners)

        #compute output dimensions from corner distances
        width_top = np.linalg.norm(rect[1] - rect[0])
        width_bottom = np.linalg.norm(rect[2] - rect[3])
        height_left = np.linalg.norm(rect[3] - rect[0])
        height_right = np.linalg.norm(rect[2] - rect[1])

        output_width = int(max(width_top, width_bottom))
        output_height = int(max(height_left, height_right))

        #define destination corners for the transform
        destination = np.array([
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1]
        ], dtype=np.float32)

        #compute and apply the perspective transform matrix
        transform_matrix = cv2.getPerspectiveTransform(rect, destination)
        warped = cv2.warpPerspective(image, transform_matrix,
                                     (output_width, output_height))
        return warped

    def _order_corners(self, corners: np.ndarray) -> np.ndarray:
        """
        Order corners as top-left, top-right, bottom-right, bottom-left.

        Args:
            corners: 4 corner points, shape (4, 2)

        Returns:
            ordered corners, shape (4, 2)
        """
        ordered = np.zeros((4, 2), dtype=np.float32)

        #top-left has smallest sum, bottom-right has largest sum
        sums = corners.sum(axis=1)
        ordered[0] = corners[np.argmin(sums)]
        ordered[2] = corners[np.argmax(sums)]

        #top-right has smallest diff, bottom-left has largest diff
        diffs = np.diff(corners, axis=1)
        ordered[1] = corners[np.argmin(diffs)]
        ordered[3] = corners[np.argmax(diffs)]

        return ordered

    def _detect_zones(self, image: np.ndarray) -> dict:
        """
        Detect key document zones using YOLOv8.
        Placeholder — will be implemented in Phase 3.

        Args:
            image: perspective-corrected document image

        Returns:
            dict with detected zone bounding boxes
        """
        #placeholder until YOLO is trained
        return {
            "photo_zone": None,
            "mrz": None,
            "text_fields": None
        }

    def _analyze_geometry(
        self, zones: dict, image: np.ndarray
    ) -> dict:
        """
        Compare detected zone positions to country template.
        Placeholder — will be implemented after templates are filled.

        Args:
            zones: detected zone bounding boxes from YOLO
            image: document image for dimension reference

        Returns:
            dict with country match and deviation score
        """
        #placeholder until spain.json is filled with real values
        return {
            "country_matched": "unknown",
            "deviation_score": 1.0,
            "within_tolerance": False
        }

    def _classify_document(self, image: np.ndarray) -> dict:
        """
        Run EfficientNet-B0 binary classifier on document image.
        Placeholder — will be implemented in Phase 5.

        Args:
            image: perspective-corrected document image

        Returns:
            dict with classifier score and label
        """
        #placeholder until EfficientNet is trained
        return {
            "score": 0.0,
            "label": "unknown",
            "low_confidence": False
        }

    def run(self, image: np.ndarray) -> dict:
        """
        Run full document authenticity pipeline.

        Args:
            image: raw ID document image, shape (H, W, 3), BGR format

        Returns:
            dict matching Feature 3 response shape from RULES.md Section 1.2

        Raises:
            PerspectiveCorrectionError: if perspective fix fails
            ZoneDetectionError: if YOLO detects zero zones
            ModelInferenceError: if EfficientNet inference fails
        """
        #layer 1 — perspective correction
        corrected_image = self._correct_perspective(image)

        #layer 2 — zone detection (placeholder)
        zones = self._detect_zones(corrected_image)

        #layer 3 — geometric analysis (placeholder)
        geometry = self._analyze_geometry(zones, corrected_image)

        #layer 4 — document classifier (placeholder)
        classification = self._classify_document(corrected_image)

        return {
            "feature": "document_authenticity",
            "layers": {
                "perspective": {
                    "corrected": True
                },
                "zone_detection": {
                    "photo_zone": zones["photo_zone"] is not None,
                    "mrz": zones["mrz"] is not None,
                    "text_fields": zones["text_fields"] is not None
                },
                "geometric_analysis": geometry,
                "classifier": classification
            }
        }