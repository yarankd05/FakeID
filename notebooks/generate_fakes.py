# Dataset: MIDV-2020
# Citation: K.B. Bulatov, E.V. Emelianova, D.V. Tropin, N.S. Skoryukina,
# Y.S. Chernyshova, A.V. Sheshkus, S.A. Usilin, Z. Ming,
# J.-C. Burie, M.M. Luqman, V.V. Arlazarov:
# "MIDV-2020: A Comprehensive Benchmark Dataset for Identity Document Analysis"
# Computer Optics, 2021.
# Never commit raw MIDV-2020 images or generated fakes to GitHub.

import csv
import json
from pathlib import Path

import cv2
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

SCAN_DIR = Path.home() / "Desktop" / "datasets" / "midv2020" / "scan_upright" / "images" / "esp_id"
PHOTO_DIR = Path.home() / "Desktop" / "datasets" / "midv2020" / "photo" / "images" / "esp_id"
TEMPLATE_PATH = BASE_DIR / "data" / "templates" / "spain.json"
SYNTHETIC_DIR = BASE_DIR / "data" / "synthetic"
MANIFEST_PATH = SYNTHETIC_DIR / "split_manifest.csv"

FAMILY_DIRS: dict[str, Path] = {
    "family1": SYNTHETIC_DIR / "family1",
    "family2": SYNTHETIC_DIR / "family2",
    "family3": SYNTHETIC_DIR / "family3",
    "family4": SYNTHETIC_DIR / "family4",
}

VERSIONS_PER_IMAGE: int = 3
IMAGE_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})


def assign_split(source_number: int, random_seed: int = 42) -> str:
    """
    Deterministically assign a split label using source_number as a seed offset.
    All fakes from the same source image receive the same split.
    Ratio: 85% train, 9% val, 6% test.

    Args:
        source_number: index of the source image within its input directory
        random_seed: base seed for reproducibility across runs

    Returns:
        one of "train", "val", or "test"
    """
    rng = np.random.default_rng(random_seed + source_number)
    value = float(rng.random())
    if value < 0.85:
        return "train"
    elif value < 0.94:
        return "val"
    else:
        return "test"


def _zone_to_pixels(
    zone: dict, image_h: int, image_w: int
) -> tuple[int, int, int, int]:
    """
    Convert normalised zone coords (centre x, centre y, w, h) to a pixel bounding box.

    Args:
        zone: dict with keys x, y, w, h — all normalised 0-1, x/y are zone centres
        image_h: image height in pixels
        image_w: image width in pixels

    Returns:
        (x1, y1, x2, y2) pixel bounding box clamped to image dimensions
    """
    cx = int(zone["x"] * image_w)
    cy = int(zone["y"] * image_h)
    half_w = int(zone["w"] * image_w / 2)
    half_h = int(zone["h"] * image_h / 2)
    x1 = max(0, cx - half_w)
    y1 = max(0, cy - half_h)
    x2 = min(image_w, cx + half_w)
    y2 = min(image_h, cy + half_h)
    return x1, y1, x2, y2


def apply_family1_tamper(
    image: np.ndarray, template: dict, rng: np.random.Generator
) -> np.ndarray:
    """
    Family 1: photo zone tampering.
    Extracts the photo zone, resizes it, blurs it, and pastes it at a shifted position.

    Args:
        image: source document image — never modified directly
        template: spain.json zone position dict
        rng: seeded random number generator for reproducibility

    Returns:
        tampered image copy with original dimensions preserved
    """
    fake = image.copy()
    h_img, w_img = fake.shape[:2]
    x1, y1, x2, y2 = _zone_to_pixels(template["photo_zone"], h_img, w_img)
    zone_h = y2 - y1
    zone_w = x2 - x1
    if zone_h <= 0 or zone_w <= 0:
        return fake

    region = fake[y1:y2, x1:x2].copy()

    # resize region to 0.7-0.9x of original size
    scale = rng.uniform(0.7, 0.9)
    new_w = max(1, int(zone_w * scale))
    new_h = max(1, int(zone_h * scale))
    region = cv2.resize(region, (new_w, new_h))

    # blur only the photo zone region
    sigma = rng.uniform(2.0, 4.0)
    k = int(sigma * 3) | 1
    region = cv2.GaussianBlur(region, (k, k), sigma)

    # shift destination by 15-30% of zone dimension in a random direction
    dx = int(rng.uniform(0.15, 0.30) * zone_w) * int(rng.choice([-1, 1]))
    dy = int(rng.uniform(0.15, 0.30) * zone_h) * int(rng.choice([-1, 1]))
    nx1 = int(np.clip(x1 + dx, 0, w_img - new_w))
    ny1 = int(np.clip(y1 + dy, 0, h_img - new_h))
    nx2 = nx1 + new_w
    ny2 = ny1 + new_h

    fake[y1:y2, x1:x2] = 0
    fake[ny1:ny2, nx1:nx2] = region
    return fake


def apply_family2_tamper(
    image: np.ndarray, template: dict, rng: np.random.Generator
) -> np.ndarray:
    """
    Family 2: id_number tampering.
    Extracts the id_number zone, applies blur and contrast reduction,
    then pastes it at a shifted position.

    Args:
        image: source document image — never modified directly
        template: spain.json zone position dict
        rng: seeded random number generator for reproducibility

    Returns:
        tampered image copy with original dimensions preserved
    """
    fake = image.copy()
    h_img, w_img = fake.shape[:2]
    x1, y1, x2, y2 = _zone_to_pixels(template["id_number"], h_img, w_img)
    zone_h = y2 - y1
    zone_w = x2 - x1
    if zone_h <= 0 or zone_w <= 0:
        return fake

    region = fake[y1:y2, x1:x2].copy()

    # blur id_number region only
    sigma = rng.uniform(1.0, 3.0)
    k = int(sigma * 3) | 1
    region = cv2.GaussianBlur(region, (k, k), sigma)

    # local contrast reduction
    factor = rng.uniform(0.6, 0.8)
    region = np.clip(region.astype(np.float32) * factor, 0, 255).astype(np.uint8)

    # shift destination by 10-25% of zone dimension in a random direction
    dx = int(rng.uniform(0.10, 0.25) * zone_w) * int(rng.choice([-1, 1]))
    dy = int(rng.uniform(0.10, 0.25) * zone_h) * int(rng.choice([-1, 1]))
    nx1 = int(np.clip(x1 + dx, 0, w_img - zone_w))
    ny1 = int(np.clip(y1 + dy, 0, h_img - zone_h))
    nx2 = nx1 + zone_w
    ny2 = ny1 + zone_h

    fake[y1:y2, x1:x2] = 0
    fake[ny1:ny2, nx1:nx2] = region
    return fake


def apply_family3_tamper(
    image: np.ndarray, template: dict, rng: np.random.Generator
) -> np.ndarray:
    """
    Family 3: text_fields tampering.
    Extracts the text_fields zone, applies blur and brightness inconsistency,
    then pastes it at a shifted position.
    Returns an unmodified copy if text_fields is not annotated in the template.

    Args:
        image: source document image — never modified directly
        template: spain.json zone position dict
        rng: seeded random number generator for reproducibility

    Returns:
        tampered image copy with original dimensions preserved
    """
    fake = image.copy()
    h_img, w_img = fake.shape[:2]
    x1, y1, x2, y2 = _zone_to_pixels(template["text_fields"], h_img, w_img)
    zone_h = y2 - y1
    zone_w = x2 - x1
    # text_fields is not yet annotated in spain.json — skip gracefully
    if zone_h <= 0 or zone_w <= 0:
        return fake

    region = fake[y1:y2, x1:x2].copy()

    # blur text_fields region only
    sigma = rng.uniform(1.0, 2.0)
    k = int(sigma * 3) | 1
    region = cv2.GaussianBlur(region, (k, k), sigma)

    # brightness inconsistency between text zone and rest of document
    brightness_factor = rng.uniform(0.8, 1.2)
    region = np.clip(region.astype(np.float32) * brightness_factor, 0, 255).astype(np.uint8)

    # shift destination by 8-20% of zone dimension in a random direction
    dx = int(rng.uniform(0.08, 0.20) * zone_w) * int(rng.choice([-1, 1]))
    dy = int(rng.uniform(0.08, 0.20) * zone_h) * int(rng.choice([-1, 1]))
    nx1 = int(np.clip(x1 + dx, 0, w_img - zone_w))
    ny1 = int(np.clip(y1 + dy, 0, h_img - zone_h))
    nx2 = nx1 + zone_w
    ny2 = ny1 + zone_h

    fake[y1:y2, x1:x2] = 0
    fake[ny1:ny2, nx1:nx2] = region
    return fake


def apply_family4_tamper(
    image: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """
    Family 4: print/scan forgery artifacts.
    Applies JPEG compression, Gaussian noise, uneven corner blur, and a colour cast.

    Args:
        image: source document image — never modified directly
        rng: seeded random number generator for reproducibility

    Returns:
        tampered image copy with original dimensions preserved
    """
    fake = image.copy()
    h_img, w_img = fake.shape[:2]

    # save and reload at low JPEG quality to introduce compression artifacts
    quality = int(rng.integers(25, 46))
    _, encoded = cv2.imencode(".jpg", fake, [cv2.IMWRITE_JPEG_QUALITY, quality])
    fake = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    # Gaussian noise across entire image
    noise_std = rng.uniform(8.0, 20.0)
    noise = rng.normal(0, noise_std, fake.shape).astype(np.float32)
    fake = np.clip(fake.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # uneven blur — stronger in one randomly chosen corner
    corner = int(rng.integers(0, 4))  # 0=TL, 1=TR, 2=BL, 3=BR
    blur_size = int(rng.integers(5, 16)) | 1  # ensure odd kernel
    half_h = h_img // 2
    half_w = w_img // 2
    corner_slices = [
        (slice(0, half_h), slice(0, half_w)),
        (slice(0, half_h), slice(half_w, w_img)),
        (slice(half_h, h_img), slice(0, half_w)),
        (slice(half_h, h_img), slice(half_w, w_img)),
    ]
    row_sl, col_sl = corner_slices[corner]
    fake[row_sl, col_sl] = cv2.GaussianBlur(
        fake[row_sl, col_sl], (blur_size, blur_size), 0
    )

    # subtle colour cast — shift one channel by ±10-20 pixel values
    channel = int(rng.integers(0, 3))
    shift = int(rng.integers(10, 21)) * int(rng.choice([-1, 1]))
    channel_data = fake[:, :, channel].astype(np.int16) + shift
    fake[:, :, channel] = np.clip(channel_data, 0, 255).astype(np.uint8)

    return fake


def _collect_sources(directory: Path, source_type: str) -> list[tuple[Path, int, str]]:
    """
    Collect valid image files from a directory sorted alphabetically.

    Args:
        directory: path to image directory
        source_type: "scan" or "photo"

    Returns:
        list of (image_path, source_number, source_type) sorted by filename
    """
    if not directory.exists():
        print(f"WARNING: directory not found — {directory}")
        return []
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
    return [(path, idx, source_type) for idx, path in enumerate(paths)]


def generate_fakes() -> None:
    """Generate all synthetic fake ID images and write the split manifest CSV."""
    with open(TEMPLATE_PATH, "r") as f:
        template = json.load(f)

    for family_dir in FAMILY_DIRS.values():
        family_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict] = []
    family_counts: dict[str, int] = {k: 0 for k in FAMILY_DIRS}
    family_failures: dict[str, int] = {k: 0 for k in FAMILY_DIRS}
    total_sources = 0

    sources = _collect_sources(SCAN_DIR, "scan") + _collect_sources(PHOTO_DIR, "photo")

    for image_path, source_number, source_type in sources:
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"WARNING: could not read {image_path.name} — skipping")
            continue

        total_sources += 1
        split = assign_split(source_number)

        for version in range(1, VERSIONS_PER_IMAGE + 1):
            family_tampers = [
                ("family1", lambda img, v=version: apply_family1_tamper(
                    img, template, np.random.default_rng(source_number * 100 + v)
                )),
                ("family2", lambda img, v=version: apply_family2_tamper(
                    img, template, np.random.default_rng(source_number * 100 + v + 10)
                )),
                ("family3", lambda img, v=version: apply_family3_tamper(
                    img, template, np.random.default_rng(source_number * 100 + v + 20)
                )),
                ("family4", lambda img, v=version: apply_family4_tamper(
                    img, np.random.default_rng(source_number * 100 + v + 30)
                )),
            ]

            for family, tamper_fn in family_tampers:
                try:
                    fake = tamper_fn(image)
                    filename = (
                        f"fake_{family}_{source_type}_{source_number:03d}_v{version}.jpg"
                    )
                    cv2.imwrite(str(FAMILY_DIRS[family] / filename), fake)
                    manifest_rows.append({
                        "filename": filename,
                        "source_number": source_number,
                        "source_type": source_type,
                        "family": family,
                        "split": split,
                    })
                    family_counts[family] += 1
                except Exception as e:
                    print(f"ERROR {family} {image_path.name} v{version}: {e}")
                    family_failures[family] += 1

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["filename", "source_number", "source_type", "family", "split"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    total_fakes = sum(family_counts.values())
    print(f"\n── Generation complete ──────────────────────────")
    print(f"Source images processed : {total_sources}")
    print(f"Total fakes generated   : {total_fakes}")
    for family, count in family_counts.items():
        print(f"  {family}: {count} generated, {family_failures[family]} failed")
    print(f"Manifest written to     : {MANIFEST_PATH}")


if __name__ == "__main__":
    generate_fakes()
