# standard library
import os
import json
from pathlib import Path


# third-party
import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics import YOLOWorld

# local
from backend.config import (
    TEMPLATES_DIR,
    GEOMETRIC_TOLERANCE_SCAN,
    GEOMETRIC_TOLERANCE_PHOTO,
    MRZ_MIN_AGE,
)
from backend.models.mrz_detector import verify_passport
from backend.utils.exceptions import (
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

    def __init__(self, yolo_path: str, mrz_model: object, mrz_reader: object) -> None:
        """Load all models at startup.

        Args:
            yolo_path:  Absolute path to YOLO zone detector weights file.
            mrz_model:  Loaded YOLOv8 MRZ detection model.
            mrz_reader: Loaded EasyOCR reader instance.

        Raises:
            FileNotFoundError: if YOLO weights file is missing.
        """
        if not os.path.exists(yolo_path):
            raise FileNotFoundError(
                f"Weights file not found: {yolo_path}. "
                f"Download and place in backend/weights/ before starting the server."
            )

        self.zone_detector = self._load_zone_detector(yolo_path)
        self.card_detector = YOLOWorld("yolov8s-world.pt")
        self.card_detector.set_classes(["id card", "credit card", "identity document", "card"])
        self.mrz_model  = mrz_model
        self.mrz_reader = mrz_reader

        with open(os.path.join(TEMPLATES_DIR, "spain.json"), "r") as f:
            self.template_scan: dict = json.load(f)
        with open(os.path.join(TEMPLATES_DIR, "spain_photo.json"), "r") as f:
            self.template_photo: dict = json.load(f)

    def _load_zone_detector(self, yolo_path: str) -> YOLO:
        """
        Load YOLO zone detector weights from disk.

        Args:
            yolo_path: absolute path to YOLO weights file

        Returns:
            YOLO model instance
        """
        return YOLO(yolo_path)

    def run(self, image: np.ndarray, image_path: Path, min_age: int = 18) -> dict:
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
        h, w = image.shape[:2]
        aspect = w / h
        long_side = max(h, w)
        is_scan = (0.65 <= aspect <= 0.75 and long_side >= 2400) or \
                  (1.38 <= aspect <= 1.50 and long_side >= 2400)

        corrected_image = self._correct_perspective(image)

        try:
            detected_zones = self._detect_zones(image)
        except ZoneDetectionError:
            detected_zones = {}

        partial_detection = not _ALL_ZONES.issubset(detected_zones.keys())
        template = self.template_scan if is_scan else self.template_photo
        tolerance = GEOMETRIC_TOLERANCE_SCAN if is_scan else GEOMETRIC_TOLERANCE_PHOTO
        geometry = self._analyze_geometry(detected_zones, template, tolerance)
        classification = self._classify(image_path, partial_detection, min_age)

        return self._build_response(detected_zones, geometry, classification, partial_detection)

    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """
        Detect document boundary using YOLO-World zero-shot detection and crop to card.
        Falls back to Canny contour detection, then centre crop if neither works.

        Args:
            image: raw input image, shape (H, W, 3), BGR format

        Returns:
            cropped card image ready for zone detection
        """
        try:
            # primary: YOLO-World zero-shot card detection (phone photos only)
            #skip for scans — A4 aspect ratio is outside phone photo range (1.1–2.2)
            h, w = image.shape[:2]
            aspect = w / h
            # ID card aspect ratio is ~1.586 (85.6mm x 54mm)
            # phone photos framed around the card are roughly 1.2–2.0
            # A4 scans are ~0.707 (portrait) or ~1.414 (landscape) — outside card range
            # only run YOLO-World if image looks like a phone photo framed around a card
            if 1.1 <= aspect <= 2.2:
                results = self.card_detector(image, verbose=False, conf=0.1)
                boxes = results[0].boxes

                if boxes is not None and len(boxes) > 0:
                    best_idx = int(boxes.conf.argmax())
                    x1, y1, x2, y2 = boxes.xyxy[best_idx].cpu().numpy().astype(int)
                    pad = 30
                    x1 = max(0, x1 - pad)
                    y1 = max(0, y1 - pad)
                    x2 = min(w, x2 + pad)
                    y2 = min(h, y2 + pad)
                    return image[y1:y2, x1:x2]

        except Exception:
            pass

        try:
            # secondary: Canny contour detection
            h_orig, w_orig = image.shape[:2]
            scale = 1000 / w_orig
            resized = cv2.resize(image, (1000, int(h_orig * scale)))

            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 30, 100)

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            edges = cv2.dilate(edges, kernel, iterations=5)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                total_area = resized.shape[0] * resized.shape[1]

                if 0.05 <= area / total_area <= 0.85:
                    perimeter = cv2.arcLength(largest_contour, True)
                    for epsilon_factor in [0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]:
                        approximated = cv2.approxPolyDP(
                            largest_contour, epsilon_factor * perimeter, True
                        )
                        if len(approximated) == 4:
                            approximated = (approximated / scale).astype(np.float32)
                            return self._apply_perspective_transform(image, approximated)

        except Exception:
            pass

        # final fallback: centre crop
        try:
            h, w = image.shape[:2]
            margin_h = int(h * 0.15)
            margin_w = int(w * 0.15)
            return image[margin_h:h - margin_h, margin_w:w - margin_w]
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
        corners = corners.reshape(4, 2)
        ordered = np.zeros((4, 2), dtype=np.float32)

        # top-left has smallest sum, bottom-right has largest sum
        sums = corners.sum(axis=1)
        ordered[0] = corners[np.argmin(sums)]
        ordered[2] = corners[np.argmax(sums)]

        # remaining two points
        remaining = corners[
            np.where((corners != ordered[0]).any(axis=1) & (corners != ordered[2]).any(axis=1))
        ]

        # top-right has smaller y, bottom-left has larger y
        if remaining[0][1] < remaining[1][1]:
            ordered[1] = remaining[0]
            ordered[3] = remaining[1]
        else:
            ordered[1] = remaining[1]
            ordered[3] = remaining[0]

        return ordered

    def _detect_zones(self, image: np.ndarray) -> dict[str, dict]:
        """
        Detect key document zones using YOLOv8.
        Keeps highest-confidence detection per class if duplicates exist.

        Args:
            image: raw original input image, BGR format

        Returns:
            dict mapping zone name to normalised centre/size coordinates:
            {"photo_zone": {"cx": float, "cy": float, "w": float, "h": float}, ...}

        Raises:
            ZoneDetectionError: if zero zones are detected
        """
        results = self.zone_detector(image, verbose=False, conf=0.15)


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

    def _analyze_geometry(self, detected_zones: dict[str, dict], template: dict, tolerance: float) -> dict:
        """
        Compare detected zone positions against the Spain template.
        Deviation is computed only over zones that were actually detected.

        Args:
            detected_zones: dict mapping zone name to normalised coords from YOLO
            template: reference template dict (scan or photo)
            tolerance: maximum allowed deviation score

        Returns:
            dict with country_matched, deviation_score, and within_tolerance
        """
        deviations: list[float] = []
        for zone_name, zone_data in detected_zones.items():
            if zone_name not in template:
                continue
            template_zone = template[zone_name]
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
        within_tolerance = deviation_score <= tolerance

        # require at least 2 detected zones and tolerance met to claim a match
        country_matched = "spain" if len(detected_zones) >= 2 and within_tolerance else "unknown"

        return {
            "country_matched": country_matched,
            "deviation_score": round(deviation_score, 4),
            "within_tolerance": within_tolerance,
        }

    def _classify(self, image_path: Path, partial_detection: bool, min_age: int = 18) -> dict:
        """Run MRZ verification pipeline on document image.

        Args:
            image_path:        Path to the document image file.
            partial_detection: True if fewer than 3 zones were detected.

        Returns:
            Dict with score (float), label ('real'/'fake'/'underage'/'error'),
            and low_confidence (bool).
        """
        result = verify_passport(
            image_path=image_path,
            model=self.mrz_model,
            reader=self.mrz_reader,
            min_age=min_age,
        )

        verdict = result.get("verdict", "ERROR")
        label = verdict.lower() if verdict in ("REAL", "FAKE", "UNDERAGE") else "error"
        low_confidence = partial_detection or verdict == "ERROR"
        score = 1.0 if verdict == "REAL" else 0.0

        return {
            "score": score,
            "label": label,
            "low_confidence": low_confidence,
            "mrz_detail": result,
        }

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
