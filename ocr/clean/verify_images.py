import json
from pathlib import Path

data = json.load(open("data/election_insights_final.json", encoding="utf-8"))
CROPS_DIR = Path("yolo_score_crops/yolo_score_crops")

print("=== ตรวจสอบ 5 รายการแรกที่ needs_review = True ===\n")
count = 0
for station in data:
    sname = station["station_name"]
    for party in station.get("party_list_results", []):
        if party.get("needs_review"):
            img_path = party["image_crop"]
            filename = Path(img_path).name
            full_path = CROPS_DIR / filename
            file_ok = full_path.exists()

            # แกะชื่อ station จากชื่อไฟล์เพื่อเทียบว่าตรงกัน
            # ชื่อไฟล์: file_XXXXX_party_<station_encoded>_row_YY_no_ZZ.png
            print(f"Station (JSON) : ...{sname[-40:]}")
            print(f"Party #        : {party['number']}")
            print(f"Score          : {party['score']}")
            print(f"image_crop     : {img_path}")
            print(f"filename       : {filename}")
            print(f"file exists    : {'[OK]' if file_ok else '[NOT FOUND]'}")
            print("-" * 60)
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break

# ─── ตรวจทั้งหมด: นับว่ารูปที่ needs_review=True มีกี่ไฟล์ที่หาไม่เจอ ───
print("\n=== สรุปทุก needs_review รายการ ===")
total = 0
found = 0
not_found = []
for station in data:
    for party in station.get("party_list_results", []):
        if party.get("needs_review"):
            total += 1
            fname = Path(party["image_crop"]).name
            if (CROPS_DIR / fname).exists():
                found += 1
            else:
                not_found.append(party["image_crop"])

print(f"ทั้งหมด      : {total} รายการ")
print(f"หาไฟล์เจอ   : {found} รายการ")
print(f"หาไฟล์ไม่เจอ: {total - found} รายการ")
if not_found:
    print("\nไฟล์ที่หาไม่เจอ 5 ตัวแรก:")
    for f in not_found[:5]:
        print(f"  {f}")
