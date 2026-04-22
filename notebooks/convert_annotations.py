"""
Convert MIDV-2020 VGG annotations to YOLO format for photo_zone class.
MIDV-2020 citation:
K.B. Bulatov et al., "MIDV-2020: A Comprehensive Benchmark Dataset
for Identity Document Analysis", Computer Optics, 2021.

Usage:
    python notebooks/convert_annotations.py

Output:
    data/yolo_annotations/esp_id/ — YOLO format txt files for photo_zone
    One txt file per image, named to match the image filename.
"""

import json
import os
from pathlib import Path

#paths — adjust if your dataset is in a different location
DATASET_BASE = Path.home() / "Desktop" / "datasets" / "midv2020"
OUTPUT_BASE = Path("data") / "yolo_annotations"

#annotation files location
ANNOTATION_FILES = {
    "scan_upright": DATASET_BASE / "scan_upright" / "annotations" / "esp_id.json",
    "photo": DATASET_BASE / "photo" / "annotations" / "esp_id.json",
}

#image folders
IMAGE_FOLDERS = {
    "scan_upright": DATASET_BASE / "scan_upright" / "images" / "esp_id",
    "photo": DATASET_BASE / "photo" / "images" / "esp_id",
}

#YOLO class index for photo_zone
PHOTO_ZONE_CLASS = 0


def convert_rect_to_yolo(
    x: int, y: int, w: int, h: int,
    img_width: int, img_height: int
) -> tuple[float, float, float, float]:
    """
    Convert VGG rect annotation to YOLO format.
    YOLO format: x_center, y_center, width, height (all normalized 0-1)

    Args:
        x, y: top-left corner of bounding box in pixels
        w, h: width and height of bounding box in pixels
        img_width, img_height: image dimensions in pixels

    Returns:
        tuple of (x_center, y_center, width, height) normalized to 0-1
    """
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    width = w / img_width
    height = h / img_height
    return x_center, y_center, width, height


def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """
    Get image dimensions without loading full image into memory.

    Args:
        image_path: path to image file

    Returns:
        tuple of (width, height)
    """
    import cv2
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    return img.shape[1], img.shape[0]


def convert_annotations(subset: str) -> None:
    """
    Convert annotations for one dataset subset to YOLO format.

    Args:
        subset: one of 'scan_upright' or 'photo'
    """
    annotation_file = ANNOTATION_FILES[subset]
    image_folder = IMAGE_FOLDERS[subset]
    output_folder = OUTPUT_BASE / subset / "esp_id"
    output_folder.mkdir(parents=True, exist_ok=True)

    print(f"\nConverting {subset} annotations...")

    with open(annotation_file, "r") as f:
        data = json.load(f)

    images = data["_via_img_metadata"]
    converted = 0
    skipped = 0

    for img_key, img_data in images.items():
        filename = img_data["filename"]
        image_path = image_folder / filename

        if not image_path.exists():
            print(f"  WARNING: image not found — {filename}")
            skipped += 1
            continue

        #get image dimensions for normalization
        img_width, img_height = get_image_dimensions(image_path)

        #find face region — this becomes photo_zone
        yolo_lines = []
        for region in img_data["regions"]:
            field_name = region["region_attributes"].get("field_name", "")
            if field_name == "face" and region["shape_attributes"]["name"] == "rect":
                s = region["shape_attributes"]
                x_c, y_c, w_n, h_n = convert_rect_to_yolo(
                    s["x"], s["y"], s["width"], s["height"],
                    img_width, img_height
                )
                #YOLO format: class x_center y_center width height
                yolo_lines.append(
                    f"{PHOTO_ZONE_CLASS} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}"
                )

        if yolo_lines:
            #write YOLO annotation file — same name as image but .txt
            output_file = output_folder / filename.replace(".jpg", ".txt")
            with open(output_file, "w") as f:
                f.write("\n".join(yolo_lines))
            converted += 1
        else:
            skipped += 1

    print(f"  Converted: {converted} images")
    print(f"  Skipped: {skipped} images")
    print(f"  Output: {output_folder}")


if __name__ == "__main__":
    print("Converting MIDV-2020 annotations to YOLO format...")
    print("photo_zone class index: 0")
    print("NOTE: MRZ (class 1) and text_fields (class 2) still need manual annotation in Roboflow")

    for subset in ["scan_upright", "photo"]:
        convert_annotations(subset)

    print("\nDone! Upload images + these txt files to Roboflow.")
    print("In Roboflow, add labels: photo_zone, mrz, text_fields")
    print("Then manually draw MRZ and text_fields boxes on each image.")