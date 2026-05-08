from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MANIFEST_PATH = BASE_DIR / "score_annotation_export" / "yolo_score_annotation_manifest.json"
SCORE_CROPS_DIR = BASE_DIR / "score_annotation_export" / "yolo_score_crops"

OUTPUT_CSV = BASE_DIR / "score_ocr_results.csv"
CHECKPOINT_CSV = BASE_DIR / "score_ocr_checkpoint.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5vl:7b"

MAX_DIGITS = 5
MAX_RETRIES = 3
REQUEST_TIMEOUT = 100
SAVE_EVERY = 20

MIN_CROP_HEIGHT = 140
MIN_CROP_WIDTH = 360

DIGIT_CROP_RATIO = 0.28
WORD_CROP_X1_RATIO = 0.30
WORD_CROP_X2_RATIO = 0.55   # จากเดิม 0.95 ❌

VERIFY_DIGIT_CROP_RATIO = 0.55
WIDE_DIGIT_CROP_RATIO = 0.70

AMBIGUOUS_DIGITS = {"0", "1", "4", "7"}

# blank ให้ conservative กว่าเดิม จะได้ไม่ตัดเลขจางเป็น blank ง่าย
MIN_HANDWRITING_COMPONENTS = 5
MIN_HANDWRITING_AREA = 500
BLANK_DARK_RATIO = 0.03

# ถ้า local image เห็นทรงวง/oval ชัด ให้ช่วยแก้เป็น 0
ZERO_LOOP_MIN_AREA = 35
ZERO_LOOP_MIN_RATIO = 0.35

QWEN_MODEL_NAME = "qwen2.5vl:7b"
TYPHOON_MODEL_NAME = "scb10x/typhoon-ocr-7b"  # แก้เป็นชื่อ model ที่ ollama ใช้จริง

# verify เฉพาะเคสเสี่ยง ไม่ยิง Typhoon ทุกภาพ
ENABLE_TYPHOON_VERIFY = True