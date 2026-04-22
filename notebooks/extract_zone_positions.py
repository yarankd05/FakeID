# standard library
# Purpose: run trained YOLO model on all 100 Spanish DNI template images,
# average the bounding box positions as normalised ratios,
# and write real zone positions to data/templates/spain.json
#
# Dataset: MIDV-2020 (K.B. Bulatov et al., Computer Optics, 2021)
# Never commit template images or this script's outputs to GitHub.

import json
import os
from pathlib import Path

# third-party
import numpy as np
from ultralytics import YOLO

# paths — absolute, safe regardless of where script is run from
BASE_DIR: Path = Path(__file__).resolve().parent.parent
WEIGHTS_PATH: str = str(BASE_DIR / "backend" / "weights" / "yolo_zones.pt")
TEMPLATES_DIR: str = str(Path.home() / "Desktop" / "datasets" / "midv2020" / "templates" / "images" / "esp_id")
OUTPUT_PATH: str = str(BASE_DIR / "data" / "templates" / "spain.json")

# class index order from Roboflow export — must match trained model exactly
CLASS_NAMES: dict[int, str] = {
    0: "id_number",
    1: "photo_zone",
    2: "text_fields"
}


def extract_zone_positions() -> None:
    """
    Run YOLO inference on all template images and average detected
    bounding box positions as normalised ratios. Write results to spain.json.
    """
    print(f"Loading model from {WEIGHTS_PATH}")
    model = YOLO(WEIGHTS_PATH)

    # accumulate detections per class
    detections: dict[str, list[dict]] = {name: [] for name in CLASS_NAMES.values()}
    skipped: int = 0
    processed: int = 0

    image_paths = sorted(Path(TEMPLATES_DIR).glob("*.jpg"))
    print(f"Found {len(image_paths)} template images")

    for image_path in image_paths:
        results = model(str(image_path), verbose=False)
        boxes = results[0].boxes

        if boxes is None or len(boxes) == 0:
            print(f"WARNING: no detections in {image_path.name} — skipping")
            skipped += 1
            continue

        # track which classes were detected in this image
        detected_classes: set[int] = set()

        for box in boxes:
            class_id = int(box.cls.item())
            if class_id not in CLASS_NAMES:
                continue

            # skip duplicate detections of same class in same image
            # keep only highest confidence detection per class per image
            if class_id in detected_classes:
                continue
            detected_classes.add(class_id)

            # xywhn = normalised cx, cy, w, h (0.0 to 1.0)
            cx, cy, w, h = box.xywhn[0].tolist()
            class_name = CLASS_NAMES[class_id]
            detections[class_name].append({
                "x": cx,
                "y": cy,
                "w": w,
                "h": h
            })

        processed += 1

    print(f"\nProcessed: {processed} images, skipped: {skipped}")

    # compute averages per class
    template: dict[str, dict[str, float]] = {}
    for class_name, boxes in detections.items():
        if len(boxes) == 0:
            print(f"WARNING: no detections found for class '{class_name}' — using placeholder 0.0")
            template[class_name] = {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
            continue

        avg_x = round(float(np.mean([b["x"] for b in boxes])), 4)
        avg_y = round(float(np.mean([b["y"] for b in boxes])), 4)
        avg_w = round(float(np.mean([b["w"] for b in boxes])), 4)
        avg_h = round(float(np.mean([b["h"] for b in boxes])), 4)

        template[class_name] = {"x": avg_x, "y": avg_y, "w": avg_w, "h": avg_h}
        print(f"{class_name}: x={avg_x}, y={avg_y}, w={avg_w}, h={avg_h} ({len(boxes)} detections)")

    # write to spain.json
    with open(OUTPUT_PATH, "w") as f:
        json.dump(template, f, indent=2)

    print(f"\nWritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    extract_zone_positions()