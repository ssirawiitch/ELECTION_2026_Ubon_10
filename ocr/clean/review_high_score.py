import json
import pandas as pd
import streamlit as st
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
DATA_FILE      = Path("data/data.json")
CSV_FILE       = Path("data/score_ocr_results.csv")
CROPS_DIR      = Path("yolo_score_crops/yolo_score_crops")  # ที่อยู่จริงของรูปตัด
BACKUP_FILE    = Path("data/data.BACKUP_highscore.json")

SCORE_THRESHOLD = 300  # แสดงรายการที่ score > 300

st.set_page_config(
    page_title="ตรวจสอบคะแนนสูง > 300 | เขต 10 อุบลราชธานี",
    page_icon="⚠️",
    layout="wide",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap');

*, html, body, [class*="css"] { font-family: 'Noto Sans Thai', sans-serif !important; }

.stApp { background: #0f1117; }

/* Card ──────────────────────────────────── */
.review-card {
    background: linear-gradient(135deg, #1a1d2e 0%, #16213e 100%);
    border: 1px solid #2d3561;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
}

/* Progress ──────────────────────────────────── */
.progress-bar-wrap {
    background: #1e2235;
    border-radius: 999px;
    height: 10px;
    overflow: hidden;
    margin: 8px 0;
}
.progress-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #e74c3c, #f39c12);
    transition: width 0.4s ease;
}

/* Badge ─────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 6px;
}
.badge-party   { background: #1a3a6c; color: #6faee8; }
.badge-station { background: #1e2a1e; color: #6ecb7f; }
.badge-warn    { background: #4a2000; color: #f39c12; }

/* Score chip ────────────────────────────── */
.score-chip {
    font-size: 2.4rem;
    font-weight: 700;
    color: #e74c3c;
    background: #1e0e0e;
    border: 2px solid #6b1010;
    border-radius: 12px;
    padding: 6px 20px;
    display: inline-block;
    letter-spacing: 2px;
}

/* Stat box ──────────────────────────────── */
.stat-box {
    background: #1a1d2e;
    border: 1px solid #2d3561;
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
}
.stat-num  { font-size: 1.8rem; font-weight: 700; color: #e74c3c; }
.stat-label{ font-size: 0.78rem; color: #8892a4; margin-top: 2px; }

/* Button overrides ──────────────────────── */
div[data-testid="stHorizontalBlock"] > div:first-child button {
    background: linear-gradient(135deg, #1e6f3f, #27ae60) !important;
    border: none !important; color: white !important;
    font-weight: 700 !important; border-radius: 10px !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
    background: linear-gradient(135deg, #7d3c98, #8e54e9) !important;
    border: none !important; color: white !important;
    font-weight: 700 !important; border-radius: 10px !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(3) button {
    background: linear-gradient(135deg, #922b21, #e74c3c) !important;
    border: none !important; color: white !important;
    font-weight: 700 !important; border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Load & cache data ────────────────────────────────────────────────────────
def load_data():
    """โหลดข้อมูลจากดิสก์เสมอ (ไม่ cache เพื่อให้เห็นการแก้ไขล่าสุด)"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_csv() -> pd.DataFrame:
    return pd.read_csv(CSV_FILE, dtype=str, low_memory=False)

def save_csv(df: pd.DataFrame):
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def make_backup(data):
    if not BACKUP_FILE.exists():
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Collect items with score > 300 ──────────────────────────────────────────
def collect_high_score_items(data):
    items = []
    for s_idx, station in enumerate(data):
        for p_idx, party in enumerate(station.get("party_list_results", [])):
            score = party.get("score")
            if score is not None and score > SCORE_THRESHOLD:
                items.append({
                    "station_idx":  s_idx,
                    "list_type":    "party_list_results",
                    "item_idx":     p_idx,
                    "station_name": station["station_name"],
                    "number":       party["number"],
                    "score":        party["score"],
                    "score_source": party.get("score_source", ""),
                    "name_ocr":     party.get("name_ocr", ""),
                    "image_crop":   party.get("image_crop", ""),
                })
        for c_idx, cand in enumerate(station.get("constituency_results", [])):
            score = cand.get("score")
            if score is not None and score > SCORE_THRESHOLD:
                items.append({
                    "station_idx":  s_idx,
                    "list_type":    "constituency_results",
                    "item_idx":     c_idx,
                    "station_name": station["station_name"],
                    "number":       cand["number"],
                    "score":        cand["score"],
                    "score_source": cand.get("score_source", ""),
                    "name_ocr":     cand.get("name_ocr", ""),
                    "image_crop":   cand.get("image_crop", ""),
                })
    return items


# ─── Session state init ───────────────────────────────────────────────────────
if "data"           not in st.session_state: st.session_state.data = load_data()
if "csv_df"         not in st.session_state: st.session_state.csv_df = load_csv()
if "review_items"   not in st.session_state: st.session_state.review_items = collect_high_score_items(st.session_state.data)
if "current_idx"    not in st.session_state: st.session_state.current_idx = 0
if "reviewed_count" not in st.session_state: st.session_state.reviewed_count = 0

make_backup(st.session_state.data)

data         = st.session_state.data
review_items = st.session_state.review_items
total        = len(review_items)
cur_idx      = st.session_state.current_idx


# ─── Helpers ──────────────────────────────────────────────────────────────────
def find_image(crop_path: str) -> Path | None:
    """ดึงชื่อไฟล์จาก crop_path แล้วหาใน CROPS_DIR โดยตรง"""
    if not crop_path:
        return None
    filename = Path(crop_path).name          # เอาแค่ชื่อไฟล์ เช่น file_00000_...png
    candidate = CROPS_DIR / filename
    if candidate.exists():
        return candidate
    # fallback: ลอง path ตรงๆ
    direct = Path(crop_path)
    if direct.exists():
        return direct
    return None

def approve_item(correct_score: int):
    """บันทึกค่าที่ถูกต้อง อัปเดตทั้ง JSON และ CSV"""
    item = review_items[cur_idx]

    # ── อัปเดต JSON ──────────────────────────────────────────
    entry = data[item["station_idx"]][item["list_type"]][item["item_idx"]]
    entry["score"]        = correct_score
    entry["needs_review"] = False
    entry["score_source"] = "human"
    save_data(data)

    # ── อัปเดต CSV ───────────────────────────────────────────
    df = st.session_state.csv_df
    mask = df["image_rel"] == item["image_crop"]
    if mask.any():
        df.loc[mask, "manual_score"]  = str(correct_score)
        df.loc[mask, "final_score"]   = str(correct_score)
        df.loc[mask, "final_source"]  = "human"
        df.loc[mask, "need_review"]   = "False"
        df.loc[mask, "review_note"]   = "human_reviewed"
        save_csv(df)
        st.session_state.csv_df = df

    # อัปเดต item ใน list ด้วย เพื่อให้ UI แสดงค่าล่าสุด
    review_items[cur_idx]["score"] = correct_score

    st.session_state.reviewed_count += 1
    st.session_state.current_idx    += 1

def skip_item():
    st.session_state.current_idx += 1

def go_back():
    if st.session_state.current_idx > 0:
        st.session_state.current_idx -= 1


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("## ⚠️ ตรวจสอบคะแนนสูงผิดปกติ (> 300) — เขต 10 อุบลราชธานี")

# Stat row
c1, c2, c3, c4 = st.columns(4)
pct_done = ((cur_idx) / total * 100) if total else 0

c1.markdown(f"""<div class="stat-box"><div class="stat-num">{total:,}</div>
<div class="stat-label">รายการ score > 300</div></div>""", unsafe_allow_html=True)
c2.markdown(f"""<div class="stat-box"><div class="stat-num" style="color:#27ae60">{st.session_state.reviewed_count:,}</div>
<div class="stat-label">แก้ไขแล้ว</div></div>""", unsafe_allow_html=True)
c3.markdown(f"""<div class="stat-box"><div class="stat-num" style="color:#f39c12">{total - cur_idx:,}</div>
<div class="stat-label">รายการที่เหลือ</div></div>""", unsafe_allow_html=True)
c4.markdown(f"""<div class="stat-box"><div class="stat-num" style="color:#8e54e9">{pct_done:.1f}%</div>
<div class="stat-label">ความคืบหน้า</div></div>""", unsafe_allow_html=True)

# Progress bar
st.markdown(f"""
<div class="progress-bar-wrap">
  <div class="progress-bar-fill" style="width:{pct_done:.1f}%"></div>
</div>
<p style="color:#8892a4;font-size:0.8rem;margin:2px 0 12px">รายการที่ {min(cur_idx+1, total):,} / {total:,}</p>
""", unsafe_allow_html=True)

st.divider()

# ─── Main review area ─────────────────────────────────────────────────────────
if cur_idx >= total:
    st.balloons()
    st.success("🎉 ตรวจสอบครบทุกรายการแล้ว! ข้อมูลถูกบันทึกเรียบร้อย")
    st.stop()

item = review_items[cur_idx]

left, right = st.columns([1.1, 1], gap="large")

with left:
    st.markdown("### 🖼️ ภาพคะแนนจาก OCR")
    img_path = find_image(item["image_crop"])
    if img_path:
        st.image(str(img_path), use_container_width=True)
    else:
        st.warning(f"⚠️ ไม่พบภาพ: `{item['image_crop']}`")

    # Station info
    station_short = item["station_name"].replace("election_data\\", "").replace("election_data/", "")
    type_label = "บัญชีรายชื่อ (Party List)" if item["list_type"] == "party_list_results" else "แบ่งเขต (Constituency)"
    st.markdown(f"""
    <div class="review-card" style="margin-top:12px">
      <span class="badge badge-station">📍 {station_short}</span><br><br>
      <span class="badge badge-party">🏛️ ประเภท: {type_label}</span>
      <span class="badge badge-party">🔢 พรรค/ผู้สมัคร #{item['number']}</span>
      <span class="badge badge-warn">📊 แหล่งที่มา: {item['score_source']}</span>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown("### ✏️ ยืนยันหรือแก้ไขคะแนน")

    raw_score = item["score"]
    default_score = int(raw_score) if raw_score is not None else 0
    score_display = str(raw_score) if raw_score is not None else "?"

    st.markdown(f"""
    <p style="color:#e74c3c;font-weight:600;margin-bottom:6px">⚠️ คะแนนสูงผิดปกติ (> 300):</p>
    <div class="score-chip">{score_display}</div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    correct_score = st.number_input(
        "คะแนนที่ถูกต้อง (ดูจากภาพ)",
        min_value=0,
        max_value=9999,
        value=default_score,
        step=1,
        key=f"score_input_{cur_idx}",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("✅ ยืนยัน", use_container_width=True, key="btn_approve"):
            approve_item(correct_score)
            st.rerun()
    with b2:
        if st.button("⏭️ ข้าม", use_container_width=True, key="btn_skip"):
            skip_item()
            st.rerun()
    with b3:
        if st.button("◀️ ย้อนกลับ", use_container_width=True, key="btn_back"):
            go_back()
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="color:#8892a4;font-size:0.82rem;line-height:1.8">
    💡 <b>วิธีใช้</b><br>
    • ดูภาพทางซ้าย แล้วอ่านตัวเลขคะแนน<br>
    • ถ้าตัวเลขในช่องถูกต้อง → กด <b>✅ ยืนยัน</b><br>
    • ถ้าตัวเลขผิด → แก้ไขตัวเลขก่อน แล้วกด <b>✅ ยืนยัน</b><br>
    • กด <b>⏭️ ข้าม</b> ถ้ายังตัดสินใจไม่ได้<br>
    • ข้อมูลจะถูกบันทึกลง JSON & CSV อัตโนมัติทุกครั้งที่กดยืนยัน
    </div>
    """, unsafe_allow_html=True)

# ─── Sidebar: jump to index & overview ────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 นำทาง")
    jump = st.number_input("ไปยังรายการที่:", min_value=1, max_value=total, value=cur_idx+1, step=1)
    if st.button("ไป", use_container_width=True):
        st.session_state.current_idx = int(jump) - 1
        st.rerun()

    st.divider()
    st.markdown("### 📋 รายการทั้งหมด")
    for i, itm in enumerate(review_items):
        marker = "✅" if i < cur_idx else ("👉" if i == cur_idx else "⬜")
        st.markdown(f"`{marker}` **#{i+1}** — พรรค {itm['number']} | score={itm['score']}")

    st.divider()
    st.markdown(f"""
    **ไฟล์ข้อมูล:**  
    `{DATA_FILE}`

    **Backup:**  
    `{BACKUP_FILE}`
    """)
    if BACKUP_FILE.exists():
        st.success("✅ Backup พร้อมแล้ว")
