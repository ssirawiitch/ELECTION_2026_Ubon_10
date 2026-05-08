import geopandas as gpd
import json

# ────────────────────────────────────────────────────────────────────
# โหลด GeoJSON และกรองเฉพาะอำเภอในเขต 10
# ────────────────────────────────────────────────────────────────────
gdf = gpd.read_file(r"C:\\Users\siraw\Downloads\Data-DS\\OpenGISData-Thailand\\subdistricts.geojson", encoding="utf-8")

# อำเภอที่อยู่ในเขตเลือกตั้งที่ 10 (ตามข้อมูลจริงใน data.json)
AMPHOE_KHET10 = ["น้ำยืน", "น้ำขุ่น", "ทุ่งศรีอุดม", "สำโรง", "เดชอุดม"]

# กรองเฉพาะอุบลราชธานี + อำเภอที่ต้องการ
gdf = gdf[
    (gdf["pro_th"] == "อุบลราชธานี") &
    (gdf["amp_th"].isin(AMPHOE_KHET10))
].copy()

print(f"Features หลังกรอง: {len(gdf)}")
print(gdf[["amp_th", "tam_th"]].drop_duplicates().to_string(index=False))

# ────────────────────────────────────────────────────────────────────
# เติม prefix "อำเภอ" / "ตำบล" ให้ตรงกับ data.json
# (data.json ใช้ "อำเภอน้ำยืน" / "ตำบลบุเปือย")
# ────────────────────────────────────────────────────────────────────
gdf["_amphoe"] = "อำเภอ" + gdf["amp_th"]
gdf["_tambon"]  = "ตำบล"  + gdf["tam_th"]

# ────────────────────────────────────────────────────────────────────
# Merge คะแนนเลือกตั้ง (df_result มาจาก script หลัก)
# ────────────────────────────────────────────────────────────────────
gdf = gdf.merge(
    df_result,
    left_on=["_amphoe", "_tambon"],
    right_on=["amphoe", "tambon"],
    how="left"
)

# ตรวจสอบว่า merge สำเร็จกี่ตำบล
matched   = gdf["name_1st"].notna().sum()
unmatched = gdf["name_1st"].isna().sum()
print(f"\n✅ Merge สำเร็จ: {matched} ตำบล")
print(f"⚠️  ไม่พบคู่: {unmatched} ตำบล")

# ดู tambon ที่ match ไม่ได้ (ถ้ามี)
if unmatched:
    miss = gdf[gdf["name_1st"].isna()][["amp_th", "tam_th"]]
    print("ตำบลที่ match ไม่ได้:")
    print(miss.to_string(index=False))