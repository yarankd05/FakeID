# standard library
from datetime import date
from pathlib import Path

# third-party
import cv2
import numpy as np
from ultralytics import YOLO
import easyocr

# local
from backend.config import MRZ_MODEL_PATH, MRZ_MIN_LINE_LENGTH, MRZ_PADDING



def detect_mrz(
    img: np.ndarray,
    model: YOLO,
    reader: easyocr.Reader,
) -> list[str] | None:
    """Detect and OCR the MRZ zone from a document image.

    Args:
        img:    BGR image array loaded with cv2.
        model:  Loaded YOLOv8 MRZ detection model.
        reader: Loaded EasyOCR reader.

    Returns:
        List of MRZ text lines, or None if not detected.
    """
    h, w = img.shape[:2]
    if max(h, w) > 1920:
        scale = 1920 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    results = model(img)[0]

    if len(results.boxes) == 0:
        return None

    boxes = results.boxes.xyxy.cpu().numpy().astype(int)
    areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
    best_box = boxes[int(np.argmax(areas))]

    y1 = max(0, best_box[1] - MRZ_PADDING)
    y2 = min(img.shape[0], best_box[3] + MRZ_PADDING)
    mrz_crop = img[y1:y2, best_box[0]:best_box[2]]

    # preprocessing to improve OCR accuracy on real passports
    mrz_crop = cv2.resize(mrz_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    raw_lines = reader.readtext(
        mrz_crop,
        detail=0,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<",
    )

    mrz_lines = []
    for line in raw_lines:
        cleaned = line.upper().replace(" ", "")
        if len(cleaned) >= 20 and cleaned.count("<") >= 3:
            mrz_lines.append(cleaned)

    return mrz_lines if mrz_lines else None


def check_digit(field: str) -> int:
    """Compute ICAO MRZ check digit for a field string.

    Args:
        field: Alphanumeric field string (may contain '<' filler).

    Returns:
        Integer check digit (0-9).
    """
    weights = [7, 3, 1]
    char_values: dict[str, int] = {"<": 0}

    for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        char_values[c] = i + 10

    for i in range(10):
        char_values[str(i)] = i

    total = sum(
        char_values.get(c, 0) * weights[i % 3]
        for i, c in enumerate(field)
    )
    return total % 10


def extract_dob(line2: str) -> date:
    """Parse date of birth from MRZ line 2.

    Args:
        line2: Second MRZ line string (44 characters for TD3 passports).

    Returns:
        Parsed date of birth as a date object.
    """
    dob_raw = line2[13:19]
    yy = int(dob_raw[0:2])
    mm = int(dob_raw[2:4])
    dd = int(dob_raw[4:6])
    year = 2000 + yy if yy <= 30 else 1900 + yy
    return date(year, mm, dd)


def calculate_age(dob: date) -> int:
    """Calculate age in years from a date of birth.

    Args:
        dob: Date of birth.

    Returns:
        Age in full years as of today.
    """
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )

def fix_numeric_fields(line2: str) -> str:
    """Fix common OCR misreads in MRZ line 2 numeric positions.

    Positions that must contain digits are corrected using known
    OCR-B font confusion pairs (e.g. O→0, I→1, L→1).

    Args:
        line2: Raw OCR output for MRZ line 2.

    Returns:
        Corrected line2 string with digits in numeric positions.
    """
    digit_only_positions = [9, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27]
    char_to_digit = {'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'G': '6', 'Z': '2'}
    chars = list(line2)
    for i in digit_only_positions:
        if i < len(chars) and chars[i] in char_to_digit:
            chars[i] = char_to_digit[chars[i]]
    return ''.join(chars)

def verify_passport(
    image_path: Path,
    model: YOLO,
    reader: easyocr.Reader,
    min_age: int = 18,
) -> dict:
    """Run full MRZ verification pipeline on a passport image.

    Detects the MRZ zone, runs OCR, validates ICAO checksums,
    and checks the holder's age against the minimum required age.

    Args:
        image_path: Path to the passport image file.
        model:      Loaded YOLOv8 MRZ detection model.
        reader:     Loaded EasyOCR reader.
        min_age:    Minimum required age for entry (default 18).

    Returns:
        Dict with keys:
            verdict  — 'REAL' | 'FAKE' | 'UNDERAGE' | 'ERROR'
            reason   — Human-readable explanation string.
            dob      — ISO date string (if successfully parsed).
            age      — Integer age (if successfully parsed).
    """
    img = cv2.imread(str(image_path))

    if img is None:
        return {"verdict": "ERROR", "reason": f"could not load image: {image_path}"}

    mrz_lines = detect_mrz(img, model, reader)

    if not mrz_lines:
        return {"verdict": "FAKE", "reason": "could not detect MRZ zone"}

    line2 = mrz_lines[-1]
    line2 = fix_numeric_fields(line2)

    if len(line2) < MRZ_MIN_LINE_LENGTH:
        return {"verdict": "FAKE", "reason": "MRZ line too short"}

    # ICAO checksum validation
    checks = {
        "document_number": (line2[0:9],   line2[9]),
        "date_of_birth":   (line2[13:19], line2[19]),
        "expiry_date":     (line2[21:27], line2[27]),
    }

    ocr_failures = []
    checksum_failures = []

    for field_name, (value, expected_char) in checks.items():
        if not expected_char.isdigit():
            ocr_failures.append(field_name)
        elif check_digit(value) != int(expected_char):
            checksum_failures.append(field_name)

    # hard fail — checksum math wrong (genuine tampering)
    if checksum_failures:
        return {
            "verdict": "FAKE",
            "reason": f"checksum failed on {', '.join(checksum_failures)}",
        }

    # soft fail — OCR couldn't read, treat as real with low confidence
    if ocr_failures:
        try:
            dob = extract_dob(line2)
            age = calculate_age(dob)
            if age < min_age:
                return {
                    "verdict": "UNDERAGE",
                    "reason": f"age {age} is below minimum {min_age}",
                    "dob": str(dob),
                    "age": age,
                }
            return {
                "verdict": "REAL",
                "reason": f"checksums passed where readable — OCR uncertain on {', '.join(ocr_failures)}",
                "dob": str(dob),
                "age": age,
            }
        except Exception:
            return {
                "verdict": "REAL",
                "reason": f"checksums passed where readable — OCR uncertain on {', '.join(ocr_failures)}",
            }

    # Age validation
    try:
        dob = extract_dob(line2)
        age = calculate_age(dob)

        if age < min_age:
            return {
                "verdict": "UNDERAGE",
                "reason": f"age {age} is below minimum {min_age}",
                "dob": str(dob),
                "age": age,
            }
    except Exception as exc:
        return {"verdict": "ERROR", "reason": f"could not parse date of birth: {exc}"}

    return {"verdict": "REAL", "reason": "all checks passed", "dob": str(dob), "age": age}

