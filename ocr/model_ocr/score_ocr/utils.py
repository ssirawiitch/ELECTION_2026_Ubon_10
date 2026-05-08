# utils.py
from . import config

import json
import re
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def imread_unicode(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def normalize_thai_digits(text):
    if text is None:
        return ""
    table = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
    return str(text).translate(table)


def thai_word_to_digit(text):
    if not text:
        return ""

    text = str(text).strip()

    # Already Arabic digits
    if re.match(r'^\d+$', text):
        return text

    # Normalize: remove zero-width chars and strip
    text = text.replace("\u200b", "").strip()

    # ---- Direct exact-match table (including สิบX compounds) ----
    EXACT = {
        # Zero
        "ศูนย์": "0", "ศูน": "0", "สูน": "0", "ซูน": "0",
        # One
        "หนึ่ง": "1", "หนึง": "1", "นึ่ง": "1", "เอ็ด": "1", "เอ็ต": "1",
        # Two
        "สอง": "2",
        # Three
        "สาม": "3",
        # Four
        "สี่": "4", "สี": "4",
        # Five
        "ห้า": "5", "หา": "5", "ห้": "5",
        # Six
        "หก": "6",
        # Seven
        "เจ็ด": "7", "เจด": "7", "เจ็ต": "7",
        # Eight
        "แปด": "8", "แปต": "8",
        # Nine
        "เก้า": "9", "เกา": "9", "เก้": "9",
        # Ten
        "สิบ": "10",
        # 11-19
        "สิบเอ็ด": "11", "สิบหนึ่ง": "11",
        "สิบสอง": "12",
        "สิบสาม": "13",
        "สิบสี่": "14",
        "สิบห้า": "15", "สิบหา": "15",
        "สิบหก": "16",
        "สิบเจ็ด": "17", "สิบเจด": "17",
        "สิบแปด": "18",
        "สิบเก้า": "19", "สิบเกา": "19",
        # Twenty
        "ยี่สิบ": "20",
    }

    # Exact match first
    if text in EXACT:
        return EXACT[text]

    # Partial prefix match (handles slight suffix noise like trailing space/period)
    for word, digit in EXACT.items():
        if text.startswith(word) or word.startswith(text):
            if abs(len(text) - len(word)) <= 2:
                return digit

    # Generic สิบX decomposition as last resort
    if "สิบ" in text:
        after = text.split("สิบ", 1)[-1].strip()
        ones_map = {
            "หนึ่ง": "1", "หนึง": "1", "นึ่ง": "1", "เอ็ด": "1",
            "สอง": "2", "สาม": "3", "สี่": "4", "สี": "4",
            "ห้า": "5", "หา": "5", "หก": "6",
            "เจ็ด": "7", "เจด": "7", "แปด": "8",
            "เก้า": "9", "เกา": "9",
        }
        if not after:
            return "10"
        for w, d in ones_map.items():
            if after == w or after.startswith(w):
                return "1" + d

    return ""


def clean_digits(text):
    text = normalize_thai_digits(text)
    return re.sub(r"[^0-9]", "", str(text))


def resolve_image_path(item):
    rel = str(item.get("image_rel") or "").replace("\\", "/")

    # 1) path ตรงจาก manifest
    if rel:
        p = config.BASE_DIR / rel
        if p.exists():
            return p

    # 2) ชื่อไฟล์ตรง
    filename = Path(rel).name
    if filename:
        p = config.SCORE_CROPS_DIR / filename
        if p.exists():
            return p

    # 3) fallback: record_id + row_index
    record_id = item.get("record_id")
    row_index = item.get("row_index")

    if record_id is not None and row_index is not None:
        prefix = f"{record_id}_row_{int(row_index):02d}_"
        matches = sorted(config.SCORE_CROPS_DIR.glob(prefix + "*.png"))
        if matches:
            return matches[0]

    return None


# ---------------------------------------------------------------------------
# Dotted-separator detection — find where handwriting ends
# ---------------------------------------------------------------------------

def find_content_cut_y(img):
    """
    Find the Y pixel where content (handwriting) ends and the dotted separator
    line (or table rule) begins.

    Uses the RIGHT portion of the word-zone strip (x = 50%..95% of width).

    Why x=50-95%?
      - Thai words (หนึ่ง, สิบสอง, etc.) are written starting from x≈30%
        and end by x≈50%. The right half (x=50-95%) is nearly blank during
        handwriting rows, so transitions stay LOW.
      - The dotted separator spans the FULL width, but because the dots form
        a near-solid band in this region, they also show LOW transitions (≤4).
      - BUT: the row just ABOVE the dots still shows moderate transitions
        from the tails of letters. So the PEAK is detectable and the DROP
        is clean.

    Algorithm:
      1. Compute per-row transition count in x=50-95% strip.
      2. Find the peak transition value in the top 65% of image.
      3. Scan downward; return the first Y where transitions < 40% of peak.

    Fallback: int(h * 0.48) — handwriting always stays in top ~48%.

    IMPORTANT: Call this on the FULL original image before any x-cropping.
    """
    if img is None or img.size == 0:
        return 0

    h, w = img.shape[:2]

    if h < 30:
        return h

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # RIGHT portion of word zone — Thai word strokes end before x=50%
    # so this strip primarily shows the dotted-line pattern on one side
    # and blank space on the other. Clean drop at separator.
    xa = max(0, int(w * 0.50))
    xb = min(w, int(w * 0.95))
    if xa >= xb:
        return int(h * 0.48)

    strip = gray[:, xa:xb]

    # Compute per-row dark pixel transitions
    t_vals = []
    for y in range(h):
        row = strip[y, :].astype(np.float32)
        dark = (row < 180).astype(np.int32)
        t = int(np.abs(np.diff(dark)).sum())
        t_vals.append(t)

    # Find handwriting peak in upper 65%
    upper_end = max(1, int(h * 0.65))
    peak_t = max(t_vals[:upper_end]) if t_vals[:upper_end] else 12
    peak_t = max(peak_t, 12)

    # Drop threshold = 40% of peak
    threshold = peak_t * 0.40

    # Scan top-down; return first Y past the peak where t < threshold
    found_peak = False
    search_end = int(h * 0.72)
    for y in range(int(h * 0.15), search_end):
        t = t_vals[y]
        if t >= peak_t * 0.70:
            found_peak = True
        if found_peak and t < threshold:
            return max(1, y - 1)

    # Fallback
    return int(h * 0.48)


# ---------------------------------------------------------------------------
# Image enhancement — upscale + CLAHE
# ---------------------------------------------------------------------------

def enhance_for_ocr(img, scale=4.0, clahe_clip=3.0, cut_y=None):
    """
    Prepare a crop for OCR:
      1. If cut_y is provided, strip everything at or below cut_y.
      2. Upscale by `scale` (default 4x).
      3. CLAHE contrast enhancement.
      4. Light sharpening.
      5. White border padding (20px each side).

    `cut_y` should always be pre-computed by find_content_cut_y() on the
    FULL original image before any x-cropping. Do NOT call find_content_cut_y
    inside this function — it will get the wrong answer on sub-crops.
    """
    if img is None or img.size == 0:
        return img

    # Step 1: Strip separator zone
    if cut_y is not None and cut_y > 5:
        h_now = img.shape[0]
        if cut_y < h_now:
            img = img[:cut_y, :].copy()

    if img.size == 0:
        return img

    # Step 2: Upscale
    img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Step 3: CLAHE
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
    gray_eq = clahe.apply(gray)
    img = cv2.cvtColor(gray_eq, cv2.COLOR_GRAY2BGR)

    # Step 4: Sharpen
    blur = cv2.GaussianBlur(img, (0, 0), 1.0)
    img = cv2.addWeighted(img, 1.5, blur, -0.5, 0)

    # Step 5: Padding
    img = cv2.copyMakeBorder(
        img, top=20, bottom=20, left=20, right=20,
        borderType=cv2.BORDER_CONSTANT, value=(255, 255, 255)
    )
    return img


def prepare_image(img):
    """Scale-up small crops to meet minimum dimensions, then sharpen + pad."""
    if img is None or img.size == 0:
        return img

    h, w = img.shape[:2]
    scale = 1.0

    if h < config.MIN_CROP_HEIGHT:
        scale = max(scale, config.MIN_CROP_HEIGHT / h)

    if w < config.MIN_CROP_WIDTH:
        scale = max(scale, config.MIN_CROP_WIDTH / w)

    scale = min(scale, 3.5)

    if scale > 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    blur = cv2.GaussianBlur(img, (0, 0), 1.0)
    img = cv2.addWeighted(img, 1.45, blur, -0.45, 0)

    img = cv2.copyMakeBorder(
        img,
        top=24, bottom=24, left=24, right=24,
        borderType=cv2.BORDER_CONSTANT,
        value=(255, 255, 255),
    )

    return img


# ---------------------------------------------------------------------------
# Crop functions — all use full-image cut_y for consistent Y trimming
# ---------------------------------------------------------------------------

def crop_digit_area(img):
    if img is None or img.size == 0:
        return img

    h, w = img.shape[:2]
    x2 = int(w * 0.28)
    crop = img[0:h, 0:x2].copy()

    return prepare_image(crop)


def crop_word_area(img):
    if img is None or img.size == 0:
        return img

    h, w = img.shape[:2]
    x1 = int(w * 0.30)
    x2 = int(w * 0.58)
    crop = img[0:h, x1:x2].copy()

    return prepare_image(crop)



def crop_digit_area_verify(img):
    """Wider digit crop for verification pass."""
    if img is None or img.size == 0:
        return img

    h, w = img.shape[:2]
    x2 = int(w * config.VERIFY_DIGIT_CROP_RATIO)
    crop = img[0:h, 0:x2].copy()
    return prepare_image(crop)


def crop_digit_area_wide(img):
    """Even wider digit crop for majority-vote pass."""
    if img is None or img.size == 0:
        return img

    h, w = img.shape[:2]
    x2 = int(w * config.WIDE_DIGIT_CROP_RATIO)
    crop = img[0:h, 0:x2].copy()
    return prepare_image(crop)


def crop_digit_area_tight(img):
    """Tight digit crop — used for CV zero detection."""
    if img is None or img.size == 0:
        return img

    h, w = img.shape[:2]
    x2 = int(w * 0.25)
    crop = img[0:h, 0:x2].copy()
    return prepare_image(crop)


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def save_csv(rows, path):
    tmp = path.with_suffix(".tmp.csv")
    pd.DataFrame(rows).to_csv(tmp, index=False, encoding="utf-8-sig")

    try:
        tmp.replace(path)
    except PermissionError:
        backup = path.with_name(path.stem + "_backup.csv")
        tmp.replace(backup)
        print(f"WARNING: {path.name} locked. Saved backup to {backup.name}")


def make_key(item):
    return f"{item.get('record_id')}__{item.get('row_index')}"


def load_checkpoint(path):
    if not path.exists():
        return {}, []

    df = pd.read_csv(path)
    done = {}

    for _, row in df.iterrows():
        key = f"{row.get('record_id')}__{row.get('row_index')}"
        done[key] = row.to_dict()

    return done, df.to_dict("records")


# ---------------------------------------------------------------------------
# Handwriting scoring / blank cell detection
# ---------------------------------------------------------------------------

def handwriting_score(img):
    if img is None or img.size == 0:
        return 0, 0, 0.0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask = (gray < 130).astype("uint8") * 255
    dark_ratio = float(mask.mean() / 255.0)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    count = 0
    total_area = 0

    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]

        if area < 16:
            continue

        # ignore dotted line / tiny noise
        if h <= 7 and w <= 14:
            continue

        # ignore long table line
        if w > 150 and h < 14:
            continue

        # handwriting-like component
        if area >= 22 and h >= 8:
            count += 1
            total_area += int(area)

    return count, total_area, dark_ratio


def is_blank_cell(digit_img, word_img):
    digit_count, digit_area, digit_ratio = handwriting_score(digit_img)
    word_count, word_area, word_ratio = handwriting_score(word_img)

    total_count = digit_count + word_count
    total_area = digit_area + word_area
    total_ratio = digit_ratio + word_ratio

    if total_area < config.MIN_HANDWRITING_AREA:
        return True

    return (
        total_count < config.MIN_HANDWRITING_COMPONENTS
        and total_ratio < config.BLANK_DARK_RATIO
    )


# ---------------------------------------------------------------------------
# CV-based zero detection
# ---------------------------------------------------------------------------

def detect_zero_like_digit(img):
    """
    Use image processing to help catch digit 0 (oval-shaped contour).
    """
    if img is None or img.size == 0:
        return False

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        area = cv2.contourArea(c)
        if area < config.ZERO_LOOP_MIN_AREA:
            continue

        x, y, w, h = cv2.boundingRect(c)
        if w <= 0 or h <= 0:
            continue

        aspect = w / float(h)
        extent = area / float(w * h)

        if 0.35 <= aspect <= 1.45 and extent >= config.ZERO_LOOP_MIN_RATIO and h >= 18 and w >= 10:
            return True

    return False