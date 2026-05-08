"""
Election Map Visualization: อุบลราชธานี เขต 10  (v2 — 2D + Labels)
====================================================================
Dependencies:
    pip install pandas geopandas pydeck shapely
"""

import json
import re
import os
import pandas as pd
import geopandas as gpd
import pydeck as pdk

# ════════════════════════════════════════════════════════════════════
# 1. โหลด Mapping ผู้สมัคร
# ════════════════════════════════════════════════════════════════════
with open("candidate_mapping_color.json", encoding="utf-8") as f:
    candidates_raw = json.load(f)

def hex_to_rgb(h: str) -> list:
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

candidate_map = {
    c["number"]: {
        "name":      c["candidate_name"],
        "party":     c["party_name"],
        "color_hex": c["color_hex"],
        "color_rgb": hex_to_rgb(c["color_hex"]),
    }
    for c in candidates_raw
}

# ════════════════════════════════════════════════════════════════════
# 2. โหลด data.json → Parse อำเภอ/ตำบล → Flatten คะแนน
# ════════════════════════════════════════════════════════════════════
with open("data.json", encoding="utf-8") as f:
    raw_data = json.load(f)

records = []
for station in raw_data:
    name    = station["station_name"]
    results = station["constituency_results"]
    if not results:
        continue

    parts = name.replace("\\\\", "\\").split("\\")
    amphoe = tambon = ""

    if len(parts) >= 2 and parts[1].startswith("อำเภอ"):
        raw_amphoe = parts[1].strip()
        m = re.match(r"(อำเภอ\S+)\s*\(เฉพาะ(ตำบล\S+)\)", raw_amphoe)
        if m:
            amphoe, tambon = m.group(1), m.group(2)
        else:
            amphoe = raw_amphoe
            if len(parts) >= 3 and parts[2].startswith("ตำบล"):
                tambon = parts[2].strip()

    if not amphoe or not tambon:
        continue

    for r in results:
        records.append({
            "amphoe":           amphoe,
            "tambon":           tambon,
            "candidate_number": r["number"],
            "score":            r["score"],
        })

df_stations = pd.DataFrame(records)
print(f"✅ โหลดข้อมูล: {len(df_stations):,} แถว | {df_stations['tambon'].nunique()} ตำบล")

# ════════════════════════════════════════════════════════════════════
# 3. Aggregate + Rank ต่อตำบล
# ════════════════════════════════════════════════════════════════════
df_agg = (
    df_stations
    .groupby(["amphoe", "tambon", "candidate_number"], as_index=False)["score"]
    .sum()
    .rename(columns={"score": "total_score"})
)
df_agg["rank"] = (
    df_agg.groupby(["amphoe", "tambon"])["total_score"]
    .rank(method="first", ascending=False)
    .astype(int)
)

def enrich(df, suffix):
    df = df.copy()
    df[f"name_{suffix}"]      = df["candidate_number"].map(lambda n: candidate_map.get(n, {}).get("name",      "ไม่ทราบ"))
    df[f"party_{suffix}"]     = df["candidate_number"].map(lambda n: candidate_map.get(n, {}).get("party",     "ไม่ทราบ"))
    df[f"color_hex_{suffix}"] = df["candidate_number"].map(lambda n: candidate_map.get(n, {}).get("color_hex", "#888888"))
    df[f"color_rgb_{suffix}"] = df["candidate_number"].map(lambda n: candidate_map.get(n, {}).get("color_rgb", [128,128,128]))
    df[f"score_{suffix}"]     = df["total_score"]
    return df[["amphoe","tambon",f"name_{suffix}",f"party_{suffix}",
               f"color_hex_{suffix}",f"color_rgb_{suffix}",f"score_{suffix}"]]

df_result = (
    enrich(df_agg[df_agg["rank"]==1], "1st")
    .merge(enrich(df_agg[df_agg["rank"]==2], "2nd"), on=["amphoe","tambon"], how="left")
)

df_total = df_agg.groupby(["amphoe","tambon"])["total_score"].sum().reset_index()
df_total.columns = ["amphoe","tambon","total_votes"]
df_result = df_result.merge(df_total, on=["amphoe","tambon"], how="left")

# ════════════════════════════════════════════════════════════════════
# 4. โหลด GeoJSON + กรองเฉพาะเขต 10 + Merge คะแนน
# ════════════════════════════════════════════════════════════════════
gdf = gpd.read_file("ubon_map.geojson", encoding="utf-8")

valid_pairs = set(zip(
    df_result["amphoe"].str.replace("อำเภอ", "", regex=False),
    df_result["tambon"].str.replace("ตำบล",  "", regex=False),
))
mask = (
    (gdf["pro_th"] == "อุบลราชธานี") &
    gdf.apply(lambda r: (r["amp_th"], r["tam_th"]) in valid_pairs, axis=1)
)
gdf = gdf[mask].copy()
print(f"🗺️  GeoJSON หลังกรอง: {len(gdf)} ตำบล")

gdf["_amphoe"] = "อำเภอ" + gdf["amp_th"]
gdf["_tambon"]  = "ตำบล"  + gdf["tam_th"]

gdf = gdf.merge(df_result,
                left_on=["_amphoe","_tambon"],
                right_on=["amphoe","tambon"],
                how="left")

print(f"   Merge สำเร็จ: {gdf['name_1st'].notna().sum()} | "
      f"ไม่พบคู่: {gdf['name_1st'].isna().sum()} ตำบล")

# ════════════════════════════════════════════════════════════════════
# 5. คำนวณ Centroid สำหรับ TextLayer
# ════════════════════════════════════════════════════════════════════
gdf_proj = gdf.to_crs(epsg=32648)
gdf["centroid_lon"] = gdf_proj.centroid.to_crs(epsg=4326).x
gdf["centroid_lat"] = gdf_proj.centroid.to_crs(epsg=4326).y

# ════════════════════════════════════════════════════════════════════
# 6. เตรียม Fill Color + Tooltip
# ════════════════════════════════════════════════════════════════════
def make_fill(rgb, alpha=185):
    if isinstance(rgb, list):
        return rgb + [alpha]
    return [180, 180, 180, alpha]

def make_line(rgb):
    if isinstance(rgb, list):
        return [min(255, v + 70) for v in rgb] + [255]
    return [220, 220, 220, 255]

gdf["fill_color"] = gdf["color_rgb_1st"].apply(lambda x: make_fill(x))
gdf["line_color"] = gdf["color_rgb_1st"].apply(make_line)

def tooltip_html(row):
    c1  = row["color_hex_1st"]
    c2  = row.get("color_hex_2nd", "#aaaaaa")
    s2  = f'{int(row["score_2nd"]):,}' if pd.notna(row.get("score_2nd")) else "-"
    n2  = row.get("name_2nd")  or "-"
    p2  = row.get("party_2nd") or "-"
    gap = int(row["score_1st"] - (row["score_2nd"] if pd.notna(row.get("score_2nd")) else 0))
    pct = row["score_1st"] / row["total_votes"] * 100 if row["total_votes"] else 0
    return (
        f'<div style="font-family:Sarabun,sans-serif;font-size:13px;line-height:1.7">'
        f'<div style="font-size:15px;font-weight:700;margin-bottom:6px;'
        f'border-bottom:1px solid rgba(255,255,255,0.2);padding-bottom:5px">'
        f'📍 {row["_tambon"]} &middot; {row["_amphoe"]}</div>'
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">'
        f'<span style="background:{c1};width:10px;height:10px;border-radius:50%;'
        f'display:inline-block;flex-shrink:0"></span>'
        f'<b>🥇 {row["name_1st"]}</b></div>'
        f'<div style="padding-left:16px;color:#ccc">{row["party_1st"]} &nbsp;'
        f'<b style="color:#fff">{int(row["score_1st"]):,}</b> คะแนน '
        f'<span style="color:#888">({pct:.1f}%)</span></div>'
        f'<div style="display:flex;align-items:center;gap:6px;margin:5px 0 2px">'
        f'<span style="background:{c2};width:10px;height:10px;border-radius:50%;'
        f'display:inline-block;flex-shrink:0"></span>'
        f'<b>🥈 {n2}</b></div>'
        f'<div style="padding-left:16px;color:#ccc">{p2} &nbsp;'
        f'<b style="color:#fff">{s2}</b> คะแนน</div>'
        f'<div style="margin-top:7px;padding-top:6px;'
        f'border-top:1px solid rgba(255,255,255,0.12);'
        f'color:#888;font-size:11px">ห่าง {gap:,} คะแนน &nbsp;·&nbsp; รวม {int(row["total_votes"]):,} คะแนน</div>'
        f'</div>'
    )

gdf["tooltip_html"] = gdf.apply(tooltip_html, axis=1)
gdf["label"]        = gdf["tam_th"]   # ชื่อตำบล (ไม่มี prefix)

# ════════════════════════════════════════════════════════════════════
# 7. แปลง GeoDataFrame → GeoJSON dict
# ════════════════════════════════════════════════════════════════════
geojson_data = json.loads(gdf.to_json())

# ════════════════════════════════════════════════════════════════════
# 8. สร้าง Layers
# ════════════════════════════════════════════════════════════════════

# Layer 1: Polygon ตำบล — 2D flat
polygon_layer = pdk.Layer(
    "GeoJsonLayer",
    data=geojson_data,
    get_fill_color="properties.fill_color",
    get_line_color="properties.line_color",
    extruded=False,
    pickable=True,
    auto_highlight=True,
    highlight_color=[255, 255, 255, 55],
    line_width_min_pixels=1,
    line_width_max_pixels=2,
)

# Layer 2: TextLayer ชื่อตำบล
df_labels = gdf[["label","centroid_lon","centroid_lat","total_votes"]].copy()
df_labels = df_labels.dropna(subset=["centroid_lon","centroid_lat"])
max_votes = df_labels["total_votes"].max()
df_labels["font_size"] = ((df_labels["total_votes"] / max_votes * 4 + 11)).clip(11, 15).astype(int)

text_layer = pdk.Layer(
    "TextLayer",
    data=df_labels,
    get_position=["centroid_lon", "centroid_lat"],
    get_text="label",
    get_size="font_size",
    get_color=[255, 255, 255, 240],
    font_family="'Sarabun', 'Noto Sans Thai', sans-serif",
    font_weight=700,
    background=True,
    get_background_color=[0, 0, 0, 110],
    background_padding=[4, 2, 4, 2],
    get_text_anchor="'middle'",
    get_alignment_baseline="'center'",
    pickable=False,
)

# ════════════════════════════════════════════════════════════════════
# 9. Legend
# ════════════════════════════════════════════════════════════════════
legend_items = "".join(
    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
    f'<div style="width:13px;height:13px;border-radius:3px;flex-shrink:0;'
    f'background:{c["color_hex"]};box-shadow:0 0 0 1px rgba(255,255,255,0.15)"></div>'
    f'<div><div style="font-size:12px;color:#eee">{c["candidate_name"]}</div>'
    f'<div style="font-size:10px;color:#888">{c["party_name"]}</div></div>'
    f'</div>'
    for c in candidates_raw
)

description = f"""
<div style="position:fixed;top:16px;right:16px;
            background:rgba(10,10,18,0.93);
            border:1px solid rgba(255,255,255,0.1);
            border-radius:14px;padding:16px 18px;z-index:999;
            min-width:230px;
            box-shadow:0 8px 40px rgba(0,0,0,0.7);
            font-family:'Sarabun',sans-serif;color:#ddd">
  <div style="font-size:15px;font-weight:700;color:#fff;
              margin-bottom:12px;padding-bottom:10px;
              border-bottom:1px solid rgba(255,255,255,0.12)">
    🗳️ ผลเลือกตั้ง ส.ส.<br/>
    <span style="font-size:11px;font-weight:400;color:#888">
      อุบลราชธานี เขต 10
    </span>
  </div>
  {legend_items}
  <div style="margin-top:12px;padding-top:10px;
              border-top:1px solid rgba(255,255,255,0.08);
              font-size:10px;color:#666;line-height:1.8">
    🎨 สีพื้นที่ = พรรคผู้ชนะ<br/>
    🖱️ hover ที่ตำบล = ดูรายละเอียด
  </div>
</div>
"""

# ════════════════════════════════════════════════════════════════════
# 10. Render
# ════════════════════════════════════════════════════════════════════
view_state = pdk.ViewState(
    latitude=14.88,
    longitude=105.35,
    zoom=9.2,
    pitch=0,
    bearing=0,
)

tooltip = {
    "html": "{properties.tooltip_html}",
    "style": {
        "backgroundColor": "rgba(10,10,18,0.96)",
        "color":           "white",
        "borderRadius":    "12px",
        "padding":         "14px 18px",
        "maxWidth":        "300px",
        "boxShadow":       "0 8px 32px rgba(0,0,0,0.7)",
        "border":          "1px solid rgba(255,255,255,0.12)",
    }
}

deck = pdk.Deck(
    layers=[polygon_layer, text_layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    description=description,
)

OUTPUT = "election_map_ubon10.html"
deck.to_html(OUTPUT, open_browser=True)
print(f"\n✅ บันทึกแล้ว: {OUTPUT}")