#run_score_ocr.py
import argparse
import os
import sys

import pandas as pd

# Force UTF-8 output so Thai filenames don't crash the terminal
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1, closefd=False)

from score_ocr import config, client, utils

def parse_debug_fields(raw):
    raw = str(raw or "")

    def get_field(name):
        import re
        m = re.search(rf"{name}=([^|]+)", raw)
        return m.group(1).strip() if m else ""

    return {
        "qwen_value": get_field("qwen_value"),
        "qwen_source": get_field("qwen_source"),
        "qwen_digit": get_field("qwen_digit"),
        "qwen_word_value": get_field("qwen_word"),
        "qwen_word_text": get_field("qwen_word_text"),
        "qwen_conf": get_field("qwen_conf"),
        "qwen_blank": get_field("qwen_blank"),
        "qwen_uncertain": get_field("qwen_uncertain"),
        "typhoon_value": get_field("typhoon_value"),
        "typhoon_source": get_field("typhoon_source"),
        "typhoon_digit": get_field("typhoon_digit"),
        "typhoon_word_value": get_field("typhoon_word"),
        "typhoon_word_text": get_field("typhoon_word_text"),
        "typhoon_conf": get_field("typhoon_conf"),
        "typhoon_blank": get_field("typhoon_blank"),
        "typhoon_uncertain": get_field("typhoon_uncertain"),
    }
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=0)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--checkpoint", type=str, default="")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--debug-map", action="store_true")
    parser.add_argument("--debug-crops", action="store_true")
    return parser.parse_args()


def is_repeated_noise(text):
    text = utils.clean_digits(text)
    return len(text) >= 5 and len(set(text)) <= 2


def is_valid_score(text):
    text = utils.clean_digits(text)

    if not text:
        return False

    if len(text) > config.MAX_DIGITS:
        return False

    if len(text) > 1 and text.startswith("0"):
        return False

    if is_repeated_noise(text):
        return False

    return True


def choose_score(qwen_digits, qwen_raw, ocr_mode):
    qwen_digits = utils.clean_digits(qwen_digits)
    qwen_raw = str(qwen_raw)

    if ocr_mode == "blank_cell":
        return None, "blank", False, "blank_cell"

    if "ERROR:" in qwen_raw:
        return None, "review_required", True, "model_error"

    if ocr_mode == "zero_detected_cv":
        return 0, "cv_zero", False, "zero_detected_cv"

    if not is_valid_score(qwen_digits):
        return None, "review_required", True, "no_valid"

    val = int(qwen_digits)

    # safest accepts
    if ocr_mode == "word_digit_agree":
        return val, "word_digit_agree", False, "word_digit_agree"

    if ocr_mode == "qwen_typhoon_agree":
        return val, "qwen_typhoon_agree", False, "qwen_typhoon_agree"

    if ocr_mode == "qwen_typhoon_agree_zero":
        return 0, "qwen_typhoon_agree_zero", False, "qwen_typhoon_agree_zero"

    # zero from word is okay
    if ocr_mode == "word_primary" and val == 0:
        return 0, "word_zero", False, "word_zero"

    # word-only one digit accept
    if ocr_mode == "word_primary" and 1 <= val <= 9:
        return val, "word_primary_one_digit", False, "word_primary_one_digit"

    # word-only multi digit = review unless Typhoon agrees
    if ocr_mode == "word_primary" and val >= 10:
        return val, "word_primary_multidigit_review", True, "word_only_multidigit"

    # conflicts/review
    if ocr_mode == "qwen_typhoon_mismatch":
        return val, "qwen_typhoon_mismatch_review", True, "qwen_typhoon_mismatch"

    if ocr_mode == "typhoon_only_unverified":
        return val, "typhoon_only_review", True, "typhoon_only_unverified"

    if ocr_mode == "digit_fallback":
        if val == 0:
            return 0, "digit_zero_fallback", False, "digit_zero_fallback"
        return val, "digit_only_review", True, "digit_only_unverified"

    if ocr_mode == "qwen_unverified":
        return val, "qwen_unverified_review", True, "qwen_unverified"

    if ocr_mode == "no_read":
        return None, "review_required", True, "no_read"

    return val, "unverified_review", True, "unverified"

def has_ambiguous_digit(digits):
    return any(ch in config.AMBIGUOUS_DIGITS for ch in str(digits))


def base_row(item):
    return {
        "id": f"{item.get('record_id')}_row_{int(item.get('row_index')):02d}",
        "record_id": item.get("record_id"),
        "batch_index": item.get("batch_index"),
        "row_index": item.get("row_index"),
        "form_type": item.get("form_type"),
        "source_parent": item.get("source_parent"),
        "source_basename": item.get("source_basename"),
        "image_rel": item.get("image_rel"),
        "candidate_no": item.get("candidate_no"),
        "candidate_name": item.get("candidate_name"),
        "name_ocr_confidence": item.get("name_ocr_confidence"),
        "raw_score_text": item.get("raw_score_text"),
    }


def error_row(item, reason):
    row = base_row(item)

    row.update({
        "qwen_value": "",
        "qwen_source": "",
        "qwen_digit": "",
        "qwen_word_value": "",
        "qwen_word_text": "",
        "qwen_conf": "",
        "qwen_blank": "",
        "qwen_uncertain": "",
        "typhoon_value": "",
        "typhoon_source": "",
        "typhoon_digit": "",
        "typhoon_word_value": "",
        "typhoon_word_text": "",
        "typhoon_conf": "",
        "typhoon_blank": "",
        "typhoon_uncertain": "",
        "ocr_text": "",
        "ocr_mode": "error",
        "final_score": None,
        "final_source": "error",
        "need_review": True,
        "review_reason": reason,
        "qwen_raw_text": "",
        "manual_score": "",
        "review_note": "",
    })
    return row


def main():
    args = parse_args()

    checkpoint_path = config.CHECKPOINT_CSV
    output_path = config.OUTPUT_CSV

    if args.checkpoint:
        checkpoint_path = config.BASE_DIR / args.checkpoint

    if args.output:
        output_path = config.BASE_DIR / args.output

    if args.reset and checkpoint_path.exists():
        checkpoint_path.unlink()
        print("Deleted checkpoint")

    # Setup debug crops dir
    debug_crops_dir = None
    debug_crop_counter = 0
    if args.debug_crops:
        debug_crops_dir = config.BASE_DIR / "score_annotation_export" / "debug_crops"
        debug_crops_dir.mkdir(parents=True, exist_ok=True)
        print(f"Debug crops will be saved to: {debug_crops_dir}")

    manifest = utils.load_json(config.MANIFEST_PATH)

    if args.end > 0:
        manifest = manifest[args.start:args.end]
    elif args.start > 0:
        manifest = manifest[args.start:]

    if args.limit > 0:
        manifest = manifest[:args.limit]

    done_map, rows = utils.load_checkpoint(checkpoint_path)

    for i, item in enumerate(manifest, start=1):
        key = utils.make_key(item)

        if key in done_map:
            continue

        img_path = utils.resolve_image_path(item)

        if args.debug_map and i <= 20:
            print(
                "MAP:",
                item.get("record_id"),
                item.get("row_index"),
                "=>",
                img_path.name if img_path else None,
            )

        if img_path is None:
            rows.append(error_row(item, "missing_image"))
            continue

        img = utils.imread_unicode(img_path)

        if img is None:
            rows.append(error_row(item, "unreadable_image"))
            continue

        # Save debug crops for first 20 items
        if debug_crops_dir is not None and debug_crop_counter < 20:
            idx_str = f"{debug_crop_counter:03d}"
            digit_crop = utils.crop_digit_area(img)
            word_crop = utils.crop_word_area(img)
            import cv2 as _cv2
            _cv2.imwrite(str(debug_crops_dir / f"{idx_str}_digit.png"), digit_crop)
            _cv2.imwrite(str(debug_crops_dir / f"{idx_str}_word.png"), word_crop)
            debug_crop_counter += 1

        qwen_digits, qwen_raw, ocr_mode = client.predict_score_multi(img)

        final_score, final_source, need_review, review_reason = choose_score(
            qwen_digits,
            qwen_raw,
            ocr_mode,
        )

        row = base_row(item)
        debug_fields = parse_debug_fields(qwen_raw)

        row.update({
            **debug_fields,
            "ocr_text": qwen_digits,
            "ocr_mode": ocr_mode,
            "final_score": final_score,
            "final_source": final_source,
            "need_review": need_review,
            "review_reason": review_reason,
            "qwen_raw_text": str(qwen_raw)[:250],
            "manual_score": "",
            "review_note": "",
        })

        rows.append(row)

        if len(rows) % 10 == 0:
            print(f"{len(rows)}/{len(manifest)}")

        if len(rows) % config.SAVE_EVERY == 0:
            utils.save_csv(rows, checkpoint_path)
            print("checkpoint saved")

    utils.save_csv(rows, checkpoint_path)
    utils.save_csv(rows, output_path)

    df = pd.DataFrame(rows)

    print("DONE")
    print("total:", len(df))
    print("accepted:", int((df["need_review"] == False).sum()))
    print("review:", int((df["need_review"] == True).sum()))
    print("missing_image:", int((df["final_source"] == "missing_image").sum()))
    print("zero_detected_cv:", int((df["ocr_mode"] == "zero_detected_cv").sum()))
    print("word_digit_agree:", int((df["ocr_mode"] == "word_digit_agree").sum()))
    print("word_primary:", int((df["ocr_mode"] == "word_primary").sum()))
    print("word_close_mismatch:", int((df["ocr_mode"] == "word_primary_close_mismatch").sum()))
    print("word_mismatch:", int((df["ocr_mode"] == "word_primary_digit_mismatch").sum()))
    print("digit_fallback:", int((df["ocr_mode"] == "digit_fallback").sum()))
    print("saved:", output_path)


if __name__ == "__main__":
    main()