# export_yolo_score_crops.py

import json
import re
from pathlib import Path

import cv2
import fitz
import numpy as np

from src.yolo_layout import YoloLayoutDetector, LayoutConfig
from src.onnx_ocr import OnnxThaiOCR, OnnxOCRConfig, resolve_onnx_paths


INPUT_JSON = Path("intermediate_batch_output/master_intermediate.json")
OUTPUT_DIR = Path("score_annotation_export/yolo_score_crops")
OUTPUT_MANIFEST = Path("score_annotation_export/yolo_score_annotation_manifest.json")
FAILED_PATH = Path("score_annotation_export/yolo_score_crop_failed.json")

DPI = 200


def safe_name(text, max_len=28):
    text = str(text or "")
    text = text.replace("\\", "_").replace("/", "_")
    text = re.sub(r"[^\wก-๙]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] or "unknown"


def pdf_to_image(doc, page_index=0, dpi=200):
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)

    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )

    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    return img


def imwrite_safe(path, img):
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix, img)
    if not ok:
        return False
    buf.tofile(str(path))
    return True


def build_filename(rec, form_short, loc, global_row_index):
    no = global_row_index + 1
    return (
        f"{safe_name(rec.get('record_id'))}_"
        f"{form_short}_"
        f"{loc}_"
        f"row_{global_row_index:02d}_"
        f"no_{int(no):02d}.png"
    )


def get_location_string(source_parent):
    parts = Path(source_parent).parts
    useful_parts = [p for p in parts if p not in ("election_data", ".", "")]
    loc_parts = useful_parts[-3:] if useful_parts else ["unknown"]
    return "_".join(safe_name(p, 20) for p in loc_parts)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records = json.loads(INPUT_JSON.read_text(encoding="utf-8"))

    # Deduplicate records by source_file to avoid processing the same PDF multiple times
    unique_records = {}
    for rec in records:
        source_file = rec["source_file"]
        if source_file not in unique_records:
            unique_records[source_file] = rec
            
    records_to_process = list(unique_records.values())

    # Initialize YOLO Layout Detector
    config = LayoutConfig(model_path="models/doclayout_yolov10n.pt")
    detector = YoloLayoutDetector(config)

    # Initialize ONNX OCR for candidate/party names
    det_path, rec_path, yml_path = resolve_onnx_paths("models")
    ocr_config = OnnxOCRConfig(det_model_path=det_path, rec_model_path=rec_path, rec_config_path=yml_path)
    ocr_detector = OnnxThaiOCR(ocr_config)

    manifest = []
    failed = []

    for rec_idx, rec in enumerate(records_to_process):
        source_file = Path(rec["source_file"])
        record_id = rec["record_id"]
        form_type = rec["form_type"]
        form_short = "party" if form_type == "party_list" else "const"
        loc = get_location_string(rec.get("source_parent", ""))

        if not source_file.exists():
            failed.append({"record_id": record_id, "error": "file_not_found", "source_file": str(source_file)})
            continue

        try:
            doc = fitz.open(str(source_file))
        except Exception as e:
            failed.append({"record_id": record_id, "error": f"pdf_open_error: {e}", "source_file": str(source_file)})
            continue

        global_row_index = 0

        for page_index in range(len(doc)):
            try:
                page_img = pdf_to_image(doc, page_index=page_index, dpi=DPI)
            except Exception as e:
                failed.append({"record_id": record_id, "error": f"pdf_render_error: {e}", "page_index": page_index})
                continue

            # Detect using YOLO
            boxes = detector.detect(page_img, page_index=page_index)
            paired = detector.pair_rows(boxes, image_shape=page_img.shape)
            valid_score_x1 = [sb.x1 for _, sb in paired if sb is not None and sb.confidence > 0.1]
            valid_score_x2 = [sb.x2 for _, sb in paired if sb is not None and sb.confidence > 0.1]
            page_score_x1 = int(np.median(valid_score_x1)) if valid_score_x1 else int(page_img.shape[1] * 0.55)
            page_score_x2 = int(np.median(valid_score_x2)) if valid_score_x2 else int(page_img.shape[1] * 0.96)

            for pair_idx, (name_box, score_box) in enumerate(paired):
                # Process Name OCR
                candidate_name = ""
                name_confidence = 0.0
                if name_box is not None:
                    name_crop = detector.crop_box(page_img, name_box, padding=2)
                    if name_crop is not None and name_crop.size > 0:
                        ocr_result = ocr_detector.recognize_crop(name_crop)
                        candidate_name = ocr_result.text
                        name_confidence = ocr_result.confidence

                # Get Optimized Score Row Crop
                crop, score_crop_box = detector.get_score_cell_crop(
                    page_img,
                    pair_idx,
                    paired,
                    page_score_x1,
                    page_score_x2
                )

                if crop is None or crop.size == 0:
                    failed.append({
                        "record_id": record_id,
                        "page_index": page_index,
                        "row_index": global_row_index,
                        "reason": "empty_yolo_crop",
                    })
                    global_row_index += 1
                    continue


                filename = build_filename(rec, form_short, loc, global_row_index)
                out_path = OUTPUT_DIR / filename

                if not imwrite_safe(out_path, crop):
                    failed.append({
                        "record_id": record_id,
                        "page_index": page_index,
                        "row_index": global_row_index,
                        "reason": "write_failed",
                    })
                    global_row_index += 1
                    continue

                # Convert YOLO bounding box to dict format for manifest
                score_box_dict = None
                if score_box is not None:
                    score_box_dict = {
                        "label": score_box.label,
                        "x1": score_box.x1,
                        "y1": score_box.y1,
                        "x2": score_box.x2,
                        "y2": score_box.y2,
                        "confidence": score_box.confidence,
                        "page_index": page_index,
                        "row_hint": score_box.row_hint,
                    }

                manifest.append({
                    "image": str(out_path),
                    "image_rel": str(out_path).replace("\\", "/"),
                    "record_id": record_id,
                    "batch_index": rec.get("batch_index"),
                    "source_file": str(source_file),
                    "source_basename": rec.get("source_basename"),
                    "source_parent": rec.get("source_parent"),
                    "page": page_index + 1,
                    "form_type": form_type,
                    "row_index": global_row_index,
                    "candidate_no": global_row_index + 1,
                    "party_no": global_row_index + 1,
                    "candidate_name": candidate_name,
                    "party_name": candidate_name,
                    "name_ocr_confidence": name_confidence,
                    "score_box": score_box_dict,
                    "score_crop_box": score_crop_box,
                    "raw_score_text": "",
                    "score_source": "yolo",
                    "review_required": True,
                })

                global_row_index += 1

        doc.close()

        if (rec_idx + 1) % 10 == 0:
            print(f"Processed PDFs: {rec_idx + 1}/{len(records_to_process)} (Total crops so far: {len(manifest)})")

    OUTPUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    FAILED_PATH.write_text(
        json.dumps(failed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("DONE")
    print("Unique PDFs:", len(records_to_process))
    print("yolo crops extracted:", len(manifest))
    print("failed extractions:", len(failed))
    print("manifest saved to:", OUTPUT_MANIFEST)


if __name__ == "__main__":
    main()
