# standard library
import os
import json

# third-party
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models
from ultralytics import YOLO

# local
from backend.config import (
    GEOMETRIC_TOLERANCE,
    CLASSIFIER_REAL_THRESHOLD,
    LOW_CONFIDENCE_BOUNDARY,
    SUPPORTED_COUNTRIES,
    WEIGHTS_DIR,
    TEMPLATES_DIR,
)
from backend.utils.exceptions import (
    PerspectiveCorrectionError,
    ZoneDetectionError,
    ModelInferenceError,
)

_CLASS_MAP: dict[int, str] = {0: "id_number", 1: "photo_zone", 2: "text_fields"}
_ALL_ZONES: frozenset[str] = frozenset({"id_number", "photo_zone", "text_fields"})


class DocumentAuthenticator:
    """
    Authenticates ID documents using perspective correction,
    zone detection, geometric analysis, and binary classification.
    Trained on Spanish DNI 3.0 format using MIDV-2020 dataset.
    """

    def __init__(self, yolo_path: str, efficientnet_path: str) -> None:
        """
        Load all models at startup.

        Args:
            yolo_path: absolute path to YOLO zone detector weights file
            efficientnet_path: absolute path to EfficientNet classifier weights file

        Raises:
            FileNotFoundError: if either weights file is missing
        """
        for path in (yolo_path, efficientnet_path):
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"Weights file not found: {path}. "
                    f"Download and place in backend/weights/ before starting the server."
                )

        self.zone_detector = self._load_zone_detector(yolo_path)
        self.classifier = self._load_classifier(efficientnet_path)

        template_path = os.path.join(TEMPLATES_DIR, "spain.json")
        with open(template_path, "r") as f:
            self.template: dict = json.load(f)

    def _load_zone_detector(self, yolo_path: str) -> YOLO:
        """
        Load YOLO zone detector weights from disk.

        Args:
            yolo_path: absolute path to YOLO weights file

        Returns:
            YOLO model instance
        """
        return YOLO(yolo_path)

    def _load_classifier(self, efficientnet_path: str) -> nn.Module:
        """
        Load EfficientNet-B0 classifier weights from disk.
        Replaces final classifier head with a 2-class linear layer.

        Args:
            efficientnet_path: absolute path to EfficientNet weights file

        Returns:
            EfficientNet-B0 model in eval mode
        """
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, 2)
        model.load_state_dict(torch.load(efficientnet_path, map_location="cpu"))
        model.eval()
        return model

    def run(self, image: np.ndarray) -> dict:
        """
        Run full document authenticity pipeline.

        Args:
            image: raw ID document image, shape (H, W, 3), BGR format

        Returns:
            dict matching Feature 3 response shape from RULES.md Section 1.2

        Raises:
            ZoneDetectionError: if YOLO detects zero zones
            ModelInferenceError: if EfficientNet inference fails
        """
        corrected_image = self._correct_perspective(image)

        detected_zones = self._detect_zones(corrected_image)
        partial_detection = not _ALL_ZONES.issubset(detected_zones.keys())

        geometry = self._analyze_geometry(detected_zones)
        classification = self._classify(corrected_image, partial_detection)

        return self._build_response(detected_zones, geometry, classification, partial_detection)

    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """
        Detect document edges and correct perspective distortion.
        Best-effort: returns original image if no document contour is found.

        Args:
            image: raw input image, shape (H, W, 3), BGR format

        Returns:
            perspective-corrected image, or original image if correction not possible
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 75, 200)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return image

            largest_contour = max(contours, key=cv2.contourArea)
            perimeter = cv2.arcLength(largest_contour, True)
            approximated = cv2.approxPolyDP(largest_contour, 0.02 * perimeter, True)

            if len(approximated) == 4:
                return self._apply_perspective_transform(image, approximated)

            return image

        except Exception:
            return image

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
        corners = corners.reshape(4, 2).astype(np.float32)
        rect = self._order_corners(corners)

        width_top = np.linalg.norm(rect[1] - rect[0])
        width_bottom = np.linalg.norm(rect[2] - rect[3])
        height_left = np.linalg.norm(rect[3] - rect[0])
        height_right = np.linalg.norm(rect[2] - rect[1])

        output_width = int(max(width_top, width_bottom))
        output_height = int(max(height_left, height_right))

        destination = np.array(
            [
                [0, 0],
                [output_width - 1, 0],
                [output_width - 1, output_height - 1],
                [0, output_height - 1],
            ],
            dtype=np.float32,
        )

        transform_matrix = cv2.getPerspectiveTransform(rect, destination)
        return cv2.warpPerspective(image, transform_matrix, (output_width, output_height))

    def _order_corners(self, corners: np.ndarray) -> np.ndarray:
        """
        Order corners as top-left, top-right, bottom-right, bottom-left.

        Args:
            corners: 4 corner points, shape (4, 2)

        Returns:
            ordered corners, shape (4, 2)
        """
        ordered = np.zeros((4, 2), dtype=np.float32)

        # top-left has smallest sum, bottom-right has largest sum
        sums = corners.sum(axis=1)
        ordered[0] = corners[np.argmin(sums)]
        ordered[2] = corners[np.argmax(sums)]

        # top-right has smallest diff, bottom-left has largest diff
        diffs = np.diff(corners, axis=1)
        ordered[1] = corners[np.argmin(diffs)]
        ordered[3] = corners[np.argmax(diffs)]

        return ordered

    def _detect_zones(self, image: np.ndarray) -> dict[str, dict]:
        """
        Detect key document zones using YOLOv8.
        Keeps highest-confidence detection per class if duplicates exist.

        Args:
            image: perspective-corrected document image, BGR format

        Returns:
            dict mapping zone name to normalised centre/size coordinates:
            {"photo_zone": {"cx": float, "cy": float, "w": float, "h": float}, ...}

        Raises:
            ZoneDetectionError: if zero zones are detected
        """
        results = self.zone_detector(image, verbose=False)

        best_per_class: dict[str, dict] = {}
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                class_idx = int(boxes.cls[i].item())
                zone_name = _CLASS_MAP.get(class_idx)
                if zone_name is None:
                    continue
                conf = float(boxes.conf[i].item())
                if zone_name not in best_per_class or conf > best_per_class[zone_name]["_conf"]:
                    xywhn = boxes.xywhn[i].cpu().numpy()
                    best_per_class[zone_name] = {
                        "cx": float(xywhn[0]),
                        "cy": float(xywhn[1]),
                        "w": float(xywhn[2]),
                        "h": float(xywhn[3]),
                        "_conf": conf,
                    }

        if not best_per_class:
            raise ZoneDetectionError("No document zones detected")

        return {
            zone_name: {k: v for k, v in zone_data.items() if k != "_conf"}
            for zone_name, zone_data in best_per_class.items()
        }

    def _analyze_geometry(self, detected_zones: dict[str, dict]) -> dict:
        """
        Compare detected zone positions against the Spain template.
        Deviation is computed only over zones that were actually detected.

        Args:
            detected_zones: dict mapping zone name to normalised coords from YOLO

        Returns:
            dict with country_matched, deviation_score, and within_tolerance
        """
        deviations: list[float] = []
        for zone_name, zone_data in detected_zones.items():
            if zone_name not in self.template:
                continue
            template_zone = self.template[zone_name]
            deviation = float(
                np.sqrt(
                    (zone_data["cx"] - template_zone["x"]) ** 2
                    + (zone_data["cy"] - template_zone["y"]) ** 2
                )
            )
            deviations.append(deviation)

        if not deviations:
            return {"country_matched": "unknown", "deviation_score": 1.0, "within_tolerance": False}

        deviation_score = float(np.mean(deviations))
        within_tolerance = deviation_score <= GEOMETRIC_TOLERANCE

        # require at least 2 detected zones and tolerance met to claim a match
        country_matched = "spain" if len(detected_zones) >= 2 and within_tolerance else "unknown"

        return {
            "country_matched": country_matched,
            "deviation_score": round(deviation_score, 4),
            "within_tolerance": within_tolerance,
        }

    def _classify(self, image: np.ndarray, partial_detection: bool) -> dict:
        """
        Run EfficientNet-B0 binary classifier on document image.

        Args:
            image: perspective-corrected document image, BGR format
            partial_detection: True if fewer than 3 zones were detected

        Returns:
            dict with score (float), label ("real"/"fake"), and low_confidence (bool)

        Raises:
            ModelInferenceError: if any step of inference fails
        """
        try:
            # convert BGR to RGB — OpenCV uses BGR, ImageNet normalisation expects RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb_image, (224, 224))

            tensor = torch.from_numpy(resized).float().permute(2, 0, 1) / 255.0
            mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
            tensor = (tensor - mean) / std
            tensor = tensor.unsqueeze(0)

            with torch.no_grad():
                logits = self.classifier(tensor)
                probabilities = torch.softmax(logits, dim=1)
                score = float(probabilities[0, 1].item())

            if score < LOW_CONFIDENCE_BOUNDARY:
                label = "fake"
                low_confidence = False
            elif score < CLASSIFIER_REAL_THRESHOLD:
                label = "real"
                low_confidence = True
            else:
                label = "real"
                low_confidence = False

            # partial zone detection means less reliable classification
            if partial_detection:
                low_confidence = True

            return {"score": round(score, 4), "label": label, "low_confidence": low_confidence}

        except Exception as e:
            raise ModelInferenceError("Model inference failed") from e

    def _build_response(
        self,
        detected_zones: dict[str, dict],
        geometry: dict,
        classification: dict,
        partial_detection: bool,
    ) -> dict:
        """
        Build the full Feature 3 response dict.

        Args:
            detected_zones: zone detection output from _detect_zones
            geometry: geometric analysis output from _analyze_geometry
            classification: classifier output from _classify
            partial_detection: True if fewer than 3 zones were detected

        Returns:
            dict matching Feature 3 response shape from RULES.md Section 1.2
        """
        return {
            "feature": "document_authenticity",
            "layers": {
                "perspective": {
                    "corrected": True
                },
                "zone_detection": {
                    "photo_zone": "photo_zone" in detected_zones,
                    "id_number": "id_number" in detected_zones,
                    "text_fields": "text_fields" in detected_zones,
                    "all_zones_detected": not partial_detection,
                },
                "geometric_analysis": geometry,
                "classifier": classification,
            },
        }
