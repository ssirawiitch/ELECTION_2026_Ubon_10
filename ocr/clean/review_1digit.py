import json
import random
import pandas as pd
import streamlit as st
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
DATA_FILE      = Path("data/data.json")
CSV_FILE       = Path("data/score_ocr_results.csv")
CROPS_DIR      = Path("yolo_score_crops/yolo_score_crops")
BACKUP_FILE    = Path("data/data.BACKUP_1digit.json")

TOTAL_SAMPLE   = 2000       # จำนวนที่สุ่มทั้งหมด
ZERO_PCT       = 0.20       # 20% จากค่า 0
# ที่เหลือ 80% แบ่งเท่ากันให้ 1–9 → ~8.9% ต่อค่า
RANDOM_SEED    = 42

st.set_page_config(
    page_title="ตรวจสอบคะแนนหลักหน่วย (0–9) | เขต 10 อุบลราชธานี",
    page_icon="🔢",
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
    background: linear-gradient(90deg, #e17055, #fdcb6e);
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
.badge-source  { background: #2d1a4e; color: #bb86fc; }
.badge-digit   { background: #3d2a0e; color: #fdcb6e; }

/* Score chip ────────────────────────────── */
.score-chip {
    font-size: 3rem;
    font-weight: 700;
    color: #fdcb6e;
    background: #1a150a;
    border: 2px solid #6b5500;
    border-radius: 12px;
    padding: 8px 36px;
    display: inline-block;
    letter-spacing: 4px;
}

/* Stat box ──────────────────────────────── */
.stat-box {
    background: #1a1d2e;
    border: 1px solid #2d3561;
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
}
.stat-num  { font-size: 1.8rem; font-weight: 700; color: #e17055; }
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


# ─── Load & save helpers ──────────────────────────────────────────────────────
def load_data():
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


# ─── Collect & stratified-sample single-digit items ──────────────────────────
def collect_1digit_stratified(data, seed=RANDOM_SEED):
    """
    รวบรวมรายการที่ score เป็นเลขหลักหน่วย (0–9)
    แล้วสุ่มแบบแบ่งชั้น:
      • score=0  →  20% ของ TOTAL_SAMPLE  (400 รายการ)
      • score=1–9 → 80% แบ่งเท่าๆ กัน   (~178 รายการต่อค่า)
    """
    # จัดกลุ่มตาม score
    buckets = {d: [] for d in range(10)}  # 0,1,...,9

    for s_idx, station in enumerate(data):
        for list_type in ("party_list_results", "constituency_results"):
            for i_idx, entry in enumerate(station.get(list_type, [])):
                score = entry.get("score")
                if score is not None and 0 <= score <= 9:
                    buckets[score].append({
                        "station_idx":  s_idx,
                        "list_type":    list_type,
                        "item_idx":     i_idx,
                        "station_name": station["station_name"],
                        "number":       entry["number"],
                        "score":        score,
                        "score_source": entry.get("score_source", ""),
                        "name_ocr":     entry.get("name_ocr", ""),
                        "image_crop":   entry.get("image_crop", ""),
                    })

    total_pool = sum(len(b) for b in buckets.values())
    pool_detail = {d: len(buckets[d]) for d in range(10)}

    rng = random.Random(seed)

    # คำนวณจำนวนที่ต้องสุ่มต่อ bucket
    n_zero = int(TOTAL_SAMPLE * ZERO_PCT)           # 400
    n_rest = TOTAL_SAMPLE - n_zero                    # 1600
    n_per_digit = n_rest // 9                         # ~177
    leftover = n_rest - n_per_digit * 9               # เศษ

    quotas = {0: n_zero}
    for d in range(1, 10):
        quotas[d] = n_per_digit
    # กระจายเศษให้ digit 1..leftover
    for d in range(1, leftover + 1):
        quotas[d] += 1

    sampled = []
    sample_detail = {}
    for d in range(10):
        pool = buckets[d]
        want = quotas[d]
        if len(pool) <= want:
            chosen = pool[:]
        else:
            chosen = rng.sample(pool, want)
        sample_detail[d] = len(chosen)
        sampled.extend(chosen)

    rng.shuffle(sampled)
    return sampled, total_pool, pool_detail, sample_detail


# ─── Session state init ───────────────────────────────────────────────────────
if "data"           not in st.session_state: st.session_state.data = load_data()
if "csv_df"         not in st.session_state: st.session_state.csv_df = load_csv()
if "review_items"   not in st.session_state:
    sampled, total_pool, pool_detail, sample_detail = collect_1digit_stratified(st.session_state.data)
    st.session_state.review_items  = sampled
    st.session_state.total_pool    = total_pool
    st.session_state.pool_detail   = pool_detail
    st.session_state.sample_detail = sample_detail
if "current_idx"    not in st.session_state: st.session_state.current_idx = 0
if "reviewed_count" not in st.session_state: st.session_state.reviewed_count = 0

make_backup(st.session_state.data)

data         = st.session_state.data
review_items = st.session_state.review_items
total        = len(review_items)
cur_idx      = st.session_state.current_idx
total_pool   = st.session_state.get("total_pool", total)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def find_image(crop_path: str) -> Path | None:
    if not crop_path:
        return None
    filename = Path(crop_path).name
    candidate = CROPS_DIR / filename
    if candidate.exists():
        return candidate
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
        df.loc[mask, "review_note"]   = "human_reviewed_1digit"
        save_csv(df)
        st.session_state.csv_df = df

    review_items[cur_idx]["score"] = correct_score
    review_items[cur_idx]["score_source"] = "human"

    st.session_state.reviewed_count += 1
    st.session_state.current_idx    += 1

def skip_item():
    st.session_state.current_idx += 1

def go_back():
    if st.session_state.current_idx > 0:
        st.session_state.current_idx -= 1


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("## 🔢 ตรวจสอบคะแนนหลักหน่วย (0–9) สุ่มตรวจ — เขต 10 อุบลราชธานี")
st.caption(f"สุ่มแบบแบ่งชั้น: ค่า 0 → 20%, ค่า 1–9 → ~8% ต่อค่า  ·  seed={RANDOM_SEED}")

# Stat row
c1, c2, c3, c4, c5 = st.columns(5)
pct_done = ((cur_idx) / total * 100) if total else 0

c1.markdown(f"""<div class="stat-box"><div class="stat-num">{total_pool:,}</div>
<div class="stat-label">ทั้งหมดในช่วง 0–9</div></div>""", unsafe_allow_html=True)
c2.markdown(f"""<div class="stat-box"><div class="stat-num" style="color:#fdcb6e">{total:,}</div>
<div class="stat-label">สุ่มตรวจ</div></div>""", unsafe_allow_html=True)
c3.markdown(f"""<div class="stat-box"><div class="stat-num" style="color:#27ae60">{st.session_state.reviewed_count:,}</div>
<div class="stat-label">ตรวจสอบแล้ว</div></div>""", unsafe_allow_html=True)
c4.markdown(f"""<div class="stat-box"><div class="stat-num" style="color:#f39c12">{total - cur_idx:,}</div>
<div class="stat-label">เหลือ</div></div>""", unsafe_allow_html=True)
c5.markdown(f"""<div class="stat-box"><div class="stat-num" style="color:#8e54e9">{pct_done:.1f}%</div>
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
    st.success("🎉 ตรวจสอบครบทุกรายการที่สุ่มแล้ว! ข้อมูลถูกบันทึกเรียบร้อย")
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
      <span class="badge badge-party">🏛️ {type_label}</span>
      <span class="badge badge-party">🔢 #{item['number']}</span>
      <span class="badge badge-source">📊 {item['score_source']}</span>
      <span class="badge badge-digit">🎯 หลักหน่วย (0–9)</span>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown("### ✏️ ยืนยันหรือแก้ไขคะแนน")

    raw_score = item["score"]
    default_score = int(raw_score) if raw_score is not None else 0
    score_display = str(raw_score) if raw_score is not None else "?"

    st.markdown(f"""
    <p style="color:#8892a4;margin-bottom:6px">คะแนนที่โมเดลอ่านได้ (หลักหน่วย):</p>
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

    # ─── JSON Inline Editor ──────────────────────────────────────────────
    st.markdown("### 📝 แก้ไข JSON โดยตรง")
    entry = data[item["station_idx"]][item["list_type"]][item["item_idx"]]
    json_str = json.dumps(entry, ensure_ascii=False, indent=2)
    edited_json = st.text_area(
        "JSON ของรายการนี้ (แก้ไขได้)",
        value=json_str,
        height=220,
        key=f"json_editor_{cur_idx}",
    )

    if st.button("💾 บันทึก JSON", use_container_width=True, key="btn_save_json"):
        try:
            parsed = json.loads(edited_json)
            data[item["station_idx"]][item["list_type"]][item["item_idx"]] = parsed
            save_data(data)

            if "score" in parsed:
                review_items[cur_idx]["score"] = parsed["score"]
            if "score_source" in parsed:
                review_items[cur_idx]["score_source"] = parsed.get("score_source", "")

            st.success("✅ บันทึก JSON สำเร็จ!")
            st.rerun()
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON ไม่ถูกต้อง: {e}")

    st.markdown("---")
    st.markdown("""
    <div style="color:#8892a4;font-size:0.82rem;line-height:1.8">
    💡 <b>วิธีใช้</b><br>
    • ดูภาพทางซ้าย แล้วอ่านตัวเลขคะแนน<br>
    • ถ้าตัวเลขในช่องถูกต้อง → กด <b>✅ ยืนยัน</b><br>
    • ถ้าตัวเลขผิด → แก้ไขตัวเลขก่อน แล้วกด <b>✅ ยืนยัน</b><br>
    • หรือแก้ไข JSON โดยตรงแล้วกด <b>💾 บันทึก JSON</b><br>
    • กด <b>⏭️ ข้าม</b> ถ้ายังตัดสินใจไม่ได้<br>
    • ข้อมูลจะถูกบันทึกลง <code>data.json</code> & CSV อัตโนมัติ
    </div>
    """, unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 นำทาง")
    jump = st.number_input("ไปยังรายการที่:", min_value=1, max_value=total, value=cur_idx+1, step=1)
    if st.button("ไป", use_container_width=True):
        st.session_state.current_idx = int(jump) - 1
        st.rerun()

    st.divider()

    # ─── สัดส่วนการสุ่ม ───────────────────────────────────────
    st.markdown("### 📊 สัดส่วนการสุ่ม")
    pool_d  = st.session_state.get("pool_detail", {})
    samp_d  = st.session_state.get("sample_detail", {})
    rows = []
    for d in range(10):
        p = pool_d.get(d, 0)
        s = samp_d.get(d, 0)
        pct = f"{s/total*100:.1f}%" if total else "–"
        rows.append({"ค่า": d, "ทั้งหมด": p, "สุ่มมา": s, "สัดส่วน": pct})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.divider()

    # ─── Resample ─────────────────────────────────────────────
    st.markdown("### 🎲 สุ่มใหม่")
    new_seed = st.number_input("เปลี่ยน Seed:", min_value=0, max_value=99999, value=RANDOM_SEED, step=1)
    if st.button("🔄 สุ่มใหม่ด้วย seed นี้", use_container_width=True):
        fresh_data = load_data()
        st.session_state.data = fresh_data
        sampled, total_pool, pool_detail, sample_detail = collect_1digit_stratified(fresh_data, seed=int(new_seed))
        st.session_state.review_items  = sampled
        st.session_state.total_pool    = total_pool
        st.session_state.pool_detail   = pool_detail
        st.session_state.sample_detail = sample_detail
        st.session_state.current_idx   = 0
        st.session_state.reviewed_count = 0
        st.rerun()

    st.divider()

    # ─── รายการใกล้เคียง ──────────────────────────────────────
    st.markdown("### 📋 รายการใกล้เคียง")
    start_show = max(0, cur_idx - 3)
    end_show   = min(total, cur_idx + 8)
    for i in range(start_show, end_show):
        itm = review_items[i]
        marker = "✅" if i < cur_idx else ("👉" if i == cur_idx else "⬜")
        st.markdown(f"`{marker}` **#{i+1}** — #{itm['number']} | score={itm['score']} | {itm['score_source']}")

    st.divider()
    st.markdown(f"""
    **ไฟล์:** `{DATA_FILE}`  
    **Backup:** `{BACKUP_FILE}`  
    **สุ่ม {total:,} จาก {total_pool:,}** รายการ (score 0–9)
    """)
    if BACKUP_FILE.exists():
        st.success("✅ Backup พร้อมแล้ว")
