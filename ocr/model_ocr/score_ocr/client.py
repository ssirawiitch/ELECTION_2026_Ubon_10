import base64
import json
import time
import cv2
import requests
import re

from . import config
from .utils import clean_digits, thai_word_to_digit


FULL_SCORE_PROMPT = """
You are reading ONE score cell crop from a Thai election form.

The image may contain:
- a handwritten digit on the left
- a Thai handwritten number word on the right
- dotted guide lines
- table borders or horizontal lines

Important rules:
- Read ONLY this one score cell.
- Do NOT guess.
- Dotted lines and table borders are NOT handwriting.
- If the score writing area is blank, return is_blank=true.
- Thai word evidence is more important than digit shape.
- Digit 0/๐ may look like 6. If word says ศูนย์, prefer word=0.
- Digit 4/๔ may look like 1. If word conflicts, mark uncertain=true.
- Never guess multi-digit numbers.
- If digit and Thai word conflict, mark uncertain=true.
- If unsure, leave score empty.

Return ONLY valid JSON:
{
  "digit_text": "",
  "word_text": "",
  "word_value": "",
  "score": "",
  "confidence": "low|medium|high",
  "is_blank": false,
  "uncertain": true,
  "reason": ""
}
"""


def _call_model_json(model_name, img, prompt):
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        return None, "ERROR: image_encode_failed"

    img_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    payload = {
        "model": model_name,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 128,
        },
        "format": "json",
    }

    last_error = ""
    for _ in range(config.MAX_RETRIES):
        try:
            res = requests.post(config.OLLAMA_URL, json=payload, timeout=config.REQUEST_TIMEOUT)
            res.raise_for_status()
            raw = res.json().get("response", "").strip()
            try:
                return json.loads(raw), raw
            except json.JSONDecodeError:
                return None, f"ERROR: invalid_json - {raw[:80]}"
        except Exception as e:
            last_error = str(e)
            time.sleep(1.0)

    return None, f"ERROR: {last_error}"


def _parse_full_result(data, raw):
    if data is None:
        return {
            "digit": "",
            "word_text": "",
            "word_value": "",
            "score": "",
            "confidence": "low",
            "is_blank": False,
            "uncertain": True,
            "raw": raw,
        }

    digit = clean_digits(data.get("digit_text", ""))
    word_text = str(data.get("word_text", "")).strip()
    word_value = clean_digits(data.get("word_value", ""))

    if not word_value and word_text:
        word_value = thai_word_to_digit(word_text)

    score = clean_digits(data.get("score", ""))
    confidence = str(data.get("confidence", "low")).lower()
    is_blank = bool(data.get("is_blank", False))
    uncertain = bool(data.get("uncertain", True))

    return {
        "digit": digit,
        "word_text": word_text,
        "word_value": word_value,
        "score": score,
        "confidence": confidence,
        "is_blank": is_blank,
        "uncertain": uncertain,
        "raw": raw,
    }


def call_full_score_ocr(img, model_name):
    data, raw = _call_model_json(model_name, img, FULL_SCORE_PROMPT)
    return _parse_full_result(data, raw)


def _best_value(result):
    """
    Word-first decision inside one model result.
    """
    digit = result.get("digit", "")
    word_value = result.get("word_value", "")
    score = result.get("score", "")
    conf = result.get("confidence", "low")
    uncertain = bool(result.get("uncertain", True))
    is_blank = bool(result.get("is_blank", False))

    if is_blank:
        return "", "blank"

    # word is primary
    if word_value:
        return word_value, "word"

    if score:
        return score, "score"

    if digit:
        return digit, "digit"

    return "", "empty"


def _needs_typhoon(qwen_result, qwen_value, qwen_source, cv_blank):
    if not getattr(config, "ENABLE_TYPHOON_VERIFY", True):
        return False

    if cv_blank and qwen_result.get("is_blank"):
        return False

    if not qwen_value:
        return True

    conf = qwen_result.get("confidence", "low")
    uncertain = bool(qwen_result.get("uncertain", True))
    digit = qwen_result.get("digit", "")
    word_value = qwen_result.get("word_value", "")

    # strong accept cases do not need Typhoon
    if qwen_value == "0" and word_value == "0" and conf in {"medium", "high"} and not uncertain:
        return False

    if digit and word_value and digit == word_value and conf in {"medium", "high"} and not uncertain:
        return False

    # risky cases
    if uncertain:
        return True

    if conf == "low":
        return True

    if digit and word_value and digit != word_value:
        return True

    if len(qwen_value) >= 2:
        return True

    if qwen_source == "digit" and qwen_value != "0":
        return True

    return False


def predict_score_multi(img):
    from . import utils

    # ใช้ crop ย่อยแค่เช็ค blank/zero ด้วย CV ไม่ส่งเข้า VLM เป็นหลัก
    digit_img = utils.crop_digit_area(img)
    word_img = utils.crop_word_area(img)
    cv_blank = utils.is_blank_cell(digit_img, word_img)

    qwen_model = getattr(config, "QWEN_MODEL_NAME", config.MODEL_NAME)
    typhoon_model = getattr(config, "TYPHOON_MODEL_NAME", "typhoon-ocr")

    qwen = call_full_score_ocr(img, qwen_model)
    qwen_value, qwen_source = _best_value(qwen)

    qwen_raw_summary = (
        f"qwen_value={qwen_value} | qwen_source={qwen_source} | "
        f"qwen_digit={qwen['digit']} | qwen_word={qwen['word_value']} | "
        f"qwen_word_text={qwen['word_text']} | qwen_conf={qwen['confidence']} | "
        f"qwen_blank={qwen['is_blank']} | qwen_uncertain={qwen['uncertain']} | "
        f"qwen_raw={qwen['raw'][:160]}"
    )

    # blank ต้อง conservative: CV + model เห็นว่าง
    if cv_blank and qwen.get("is_blank"):
        return "", qwen_raw_summary, "blank_cell"

    # strong Qwen-only accept
    if qwen_value and qwen["digit"] and qwen["word_value"] and qwen["digit"] == qwen["word_value"]:
        return qwen_value, qwen_raw_summary, "word_digit_agree"

    if qwen_value == "0" and qwen["word_value"] == "0" and qwen["confidence"] in {"medium", "high"} and not qwen["uncertain"]:
        return "0", qwen_raw_summary, "word_primary"

    # CV zero fallback before Typhoon only if Qwen does not see meaningful conflicting word
    tight_crop = utils.crop_digit_area_tight(img)
    cv_zero = utils.detect_zero_like_digit(tight_crop)

    if cv_zero and not qwen["word_value"] and not qwen["digit"]:
        return "0", qwen_raw_summary + " [cv_zero]", "zero_detected_cv"

    # Typhoon verify only when needed
    if _needs_typhoon(qwen, qwen_value, qwen_source, cv_blank):
        typhoon = call_full_score_ocr(img, typhoon_model)
        ty_value, ty_source = _best_value(typhoon)

        raw_summary = (
            qwen_raw_summary
            + f" || typhoon_value={ty_value} | typhoon_source={ty_source} | "
            f"typhoon_digit={typhoon['digit']} | typhoon_word={typhoon['word_value']} | "
            f"typhoon_word_text={typhoon['word_text']} | typhoon_conf={typhoon['confidence']} | "
            f"typhoon_blank={typhoon['is_blank']} | typhoon_uncertain={typhoon['uncertain']} | "
            f"typhoon_raw={typhoon['raw'][:160]}"
        )

        if cv_blank and typhoon.get("is_blank"):
            return "", raw_summary, "blank_cell"

        if qwen_value and ty_value and qwen_value == ty_value:
            if qwen_value == "0":
                return "0", raw_summary, "qwen_typhoon_agree_zero"
            return qwen_value, raw_summary, "qwen_typhoon_agree"

        # ถ้า Qwen word ชัด แต่ Typhoon ไม่อ่านได้ ให้ส่ง review ไม่ accept
        if qwen_value:
            return qwen_value, raw_summary, "qwen_typhoon_mismatch"

        if ty_value:
            return ty_value, raw_summary, "typhoon_only_unverified"

        if cv_zero:
            return "0", raw_summary + " [cv_zero_after_verify]", "zero_detected_cv"

        return "", raw_summary, "no_read"

    # Qwen non-verified paths
    if qwen_value:
        if qwen_source == "word":
            return qwen_value, qwen_raw_summary, "word_primary"
        if qwen_source == "digit":
            return qwen_value, qwen_raw_summary, "digit_fallback"
        return qwen_value, qwen_raw_summary, "qwen_unverified"

    if cv_zero:
        return "0", qwen_raw_summary + " [cv_zero]", "zero_detected_cv"

    return "", qwen_raw_summary, "no_read"