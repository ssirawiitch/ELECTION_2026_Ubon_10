import json, sys, shutil
sys.stdout.reconfigure(encoding='utf-8')

# Backup first
shutil.copy(r'data\data.json', r'data\data.BACKUP_manual.json')
print("Backup created.")

with open(r'data\data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Build a lookup: station_name -> index
sn_to_idx = {}
for i, item in enumerate(data):
    sn_to_idx[item['station_name']] = i

def set_score(item, results_key, candidate_no, score):
    """Set score for a candidate number in results list."""
    results = item[results_key]
    for r in results:
        if r['number'] == candidate_no:
            r['score'] = score
            r['score_source'] = 'human'
            r['needs_review'] = False
            return True
    print(f"  WARNING: candidate {candidate_no} not found in {results_key} of {item['station_name']}")
    return False

def get_item(station_name):
    idx = sn_to_idx.get(station_name)
    if idx is None:
        print(f"WARNING: station not found: {station_name}")
        return None
    return data[idx]

changes = 0

# ============================================================
# ล่วงหน้านอกเขตเลือกตั้ง
# Index mapping (from station_names.txt):
# ชุดที่ 1 -> idx 0
# ชุดที่ 2 -> idx 1
# ชุดที่ 3 -> idx 2
# ชุดที่ 4 -> idx 3
# ชุดที่ 5 -> idx 4
# ชุดที่ 7 -> idx 5  (note: 7, not 6)
# ชุดที่ 8 -> idx 6
# ชุดที่ 9 (บช) -> idx 7
# ชุดที่6 (no space) -> idx 8
# ชุดที่ 9 (เขต/const) -> idx 9
# ============================================================

# แบบ party list (candidate 2 and 5 in party_list_results)
party_list_data = [
    # (idx, cand2_score, cand5_score)
    (0, 254, 224),  # ชุดที่ 1
    (1, 240, 221),  # ชุดที่ 2
    (2, 280, 222),  # ชุดที่ 3
    (3, 250, 215),  # ชุดที่ 4
    (4, 231, 228),  # ชุดที่ 5
    (8, 249, 236),  # ชุดที่ 6 (idx 8, station name has no space: ชุดที่6)
    (5, 253, 207),  # ชุดที่ 7 (idx 5)
    (6, 277, 214),  # ชุดที่ 8 (idx 6)
    (7, 257, 20),   # ชุดที่ 9 (idx 7) -- user wrote "5 ได้ 20" (possibly 207 but we trust the user)
]

for (idx, s2, s5) in party_list_data:
    item = data[idx]
    if set_score(item, 'party_list_results', 2, s2): changes += 1
    if set_score(item, 'party_list_results', 5, s5): changes += 1

# แบบ บัญชีรายชื่อ (candidate 21 and 46 in party_list_results)
party_list_data2 = [
    # (idx, cand21_score, cand46_score)
    (0, 158, 319),  # ชุดที่ 1
    (1, 160, 303),  # ชุดที่ 2
    (2, 182, 307),  # ชุดที่ 3
    (3, 165, 280),  # ชุดที่ 4
    (4, 140, 321),  # ชุดที่ 5
    (8, 167, 302),  # ชุดที่ 6 (idx 8)
    (5, 156, 310),  # ชุดที่ 7 (idx 5)
    (6, 190, 315),  # ชุดที่ 8 (idx 6)
    (7, 163, 284),  # ชุดที่ 9 (idx 7)
]

for (idx, s21, s46) in party_list_data2:
    item = data[idx]
    if set_score(item, 'party_list_results', 21, s21): changes += 1
    if set_score(item, 'party_list_results', 46, s46): changes += 1

# ล่วงหน้า แบบเขต ชุดที่ 9 (idx 9) - constituency_results
item9 = data[9]
if set_score(item9, 'constituency_results', 2, 257): changes += 1

# ============================================================
# อำเภอเดชอุดม (เฉพาะตำบลทุ่งเทิง)
# Indices 288-302 from station_names.txt
# ============================================================
base = "election_data\\อำเภอเดชอุดม (เฉพาะตำบลทุ่งเทิง)"

detch_data = {
    1:  {'const': {2: 236, 3: 122},        'party': {9: 111, 21: 113}},
    2:  {'const': {2: 192, 3: 52},          'party': {9: 69,  21: 80}},
    3:  {'const': {2: 257, 3: 44},          'party': {9: 56,  21: 120}},
    4:  {'const': {2: 40,  3: 89, 5: 40},   'party': {9: 91,  46: 48}},
    5:  {'const': {2: 196, 3: 30},          'party': {9: 34,  21: 119}},
    6:  {'const': {2: 141, 3: 22},          'party': {9: 37,  21: 60}},
    7:  {'const': {2: 53,  3: 6},           'party': {9: 14,  21: 24}},
    8:  {'const': {2: 102, 3: 31},          'party': {9: 25,  21: 52}},
    9:  {'const': {2: 213, 5: 30},          'party': {9: 57,  21: 108}},
    10: {'const': {2: 151, 5: 39},          'party': {9: 32,  21: 64}},
    11: {'const': {2: 272, 5: 43},          'party': {9: 91,  21: 131}},
    12: {'const': {2: 114, 3: 95},          'party': {9: 76,  21: 77}},
    13: {'const': {2: 91,  3: 30},          'party': {9: 31,  21: 61}},
    14: {'const': {2: 114, 3: 15},          'party': {9: 23,  21: 64}},
    15: {'const': {2: 196, 3: 38},          'party': {9: 52,  21: 88}},
}

for unit, scores in detch_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอทุ่งศรีอุดม (ตำบลกุดเรือ)
# ============================================================
base = "election_data\\อำเภอทุ่งศรีอุดม\\ตำบลกุดเรือ"

kudrua_data = {
    1:  {'const': {2: 304, 3: 52},       'party': {9: 62,  21: 196}},
    2:  {'const': {2: 363, 5: 28},       'party': {46: 43, 21: 209}},
    3:  {'const': {2: 144},              'party': {9: 11,  21: 95}},
    4:  {'const': {2: 174, 5: 18},       'party': {9: 19,  21: 118}},
    5:  {'const': {2: 199},              'party': {9: 11,  21: 105}},
    6:  {'const': {2: 223, 3: 21},       'party': {46: 37, 21: 136}},
    7:  {'const': {2: 242, 3: 25},       'party': {9: 30,  21: 167}},
    8:  {'const': {2: 247, 3: 16},       'party': {9: 33,  21: 135}},
    9:  {'const': {2: 181, 3: 14},       'party': {9: 28,  21: 116}},
    10: {'const': {2: 186, 5: 15},       'party': {9: 13,  21: 128}},
    11: {'const': {2: 126, 3: 8},        'party': {9: 11,  21: 74}},
}

for unit, scores in kudrua_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอทุ่งศรีอุดม (ตำบลโคกชำแระ)
# ============================================================
base = "election_data\\อำเภอทุ่งศรีอุดม\\ตำบลโคกชำแระ"

khokchum_data = {
    1:  {'const': {2: 219, 5: 31},       'party': {9: 32,  21: 175}},
    2:  {'const': {2: 182, 5: 10},       'party': {46: 19, 21: 98}},
    3:  {'const': {2: 306},              'party': {9: 29,  21: 193}},
    4:  {'const': {2: 193, 5: 11},       'party': {9: 22,  21: 106}},
    5:  {'const': {2: 168},              'party': {9: 23,  21: 80}},
    6:  {'const': {2: 141, 3: 21},       'party': {9: 32,  21: 73}},
    7:  {'const': {2: 283, 3: 31},       'party': {9: 43,  21: 178}},
    8:  {'const': {2: 255, 3: 11},       'party': {9: 17,  21: 158}},
    9:  {'const': {2: 152, 5: 14},       'party': {9: 23,  21: 103}},
    10: {'const': {2: 204, 5: 26},       'party': {9: 31,  21: 121}},
    11: {'const': {2: 214, 5: 17},       'party': {9: 22,  21: 123}},
}

for unit, scores in khokchum_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอทุ่งศรีอุดม (ตำบลนาเกษม)
# ============================================================
base = "election_data\\อำเภอทุ่งศรีอุดม\\ตำบลนาเกษม"

nakasem_data = {
    1:  {'const': {2: 296, 3: 35},       'party': {9: 28,  21: 204}},
    2:  {'const': {2: 170, 5: 21},       'party': {46: 28, 21: 100}},
    3:  {'const': {2: 253},              'party': {9: 24,  21: 134}},
    4:  {'const': {2: 192, 5: 15},       'party': {9: 21,  21: 120}},
    5:  {'const': {2: 333, 3: 40},       'party': {9: 44,  21: 189}},
    6:  {'const': {2: 96,  3: 5},        'party': {9: 16,  21: 53}},
    7:  {'const': {2: 98,  3: 16},       'party': {9: 16,  21: 54}},
    8:  {'const': {2: 80,  3: 3},        'party': {9: 6,   21: 60}},
    9:  {'const': {2: 233, 5: 22},       'party': {9: 19,  21: 151}},
    10: {'const': {2: 22},               'party': {9: 6,   21: 66}},
    11: {'const': {2: 184, 5: 13},       'party': {9: 16,  21: 104}},
}

for unit, scores in nakasem_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอทุ่งศรีอุดม (ตำบลนาห่อม)
# ============================================================
base = "election_data\\อำเภอทุ่งศรีอุดม\\ตำบลนาห่อม"

nahom_data = {
    1:  {'const': {2: 131, 3: 27},       'party': {9: 40,  21: 64}},
    2:  {'const': {2: 147, 5: 12},       'party': {46: 23, 21: 80}},
    3:  {'const': {2: 206},              'party': {9: 26,  21: 123}},
    4:  {'const': {2: 101, 3: 6},        'party': {9: 12,  21: 60}},
    5:  {'const': {2: 132, 3: 16},       'party': {9: 33,  21: 63}},
    6:  {'const': {2: 214, 3: 22},       'party': {9: 38,  21: 126}},
    7:  {'const': {2: 171, 3: 19},       'party': {9: 27,  21: 119}},
    8:  {'const': {2: 88,  3: 22},       'party': {9: 36,  21: 32}},
    9:  {'const': {2: 105, 5: 5},        'party': {9: 19,  21: 53}},
    10: {'const': {2: 95},               'party': {9: 28,  21: 47}},
    11: {'const': {2: 164, 5: 53},       'party': {9: 53,  21: 92}},
}

for unit, scores in nahom_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอทุ่งศรีอุดม (ตำบลหนองอ้ม)
# ============================================================
base = "election_data\\อำเภอทุ่งศรีอุดม\\ตำบลหนองอ้ม"

nonghom_data = {
    1:  {'const': {2: 249, 3: 39},       'party': {9: 46,  21: 140}},
    2:  {'const': {2: 277, 3: 53},       'party': {46: 69, 21: 153}},
    3:  {'const': {2: 202},              'party': {9: 51,  21: 100}},
    4:  {'const': {2: 289, 3: 39},       'party': {9: 39,  21: 160}},
    5:  {'const': {2: 122, 3: 20},       'party': {9: 35,  21: 73}},
    6:  {'const': {2: 181, 3: 37},       'party': {9: 51,  21: 123}},
    7:  {'const': {2: 184, 3: 24},       'party': {9: 27,  21: 99}},
    8:  {'const': {2: 96,  3: 9},        'party': {9: 11,  21: 72}},
    9:  {'const': {2: 177, 5: 28},       'party': {9: 28,  21: 116}},
    10: {'const': {2: 142},              'party': {9: 10,  21: 103}},
}

for unit, scores in nonghom_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอน้ำขุ่น (ตำบลขี้เหล็ก)
# ============================================================
base = "election_data\\อำเภอน้ำขุ่น\\ตำบลขี้เหล็ก"

khilek_data = {
    1:  {'const': {2: 252, 3: 7},        'party': {9: 17,  21: 166}},
    # หน่วยที่ 2 - only party: 21=229 (no เขต given)
    2:  {'const': {},                     'party': {21: 229}},
    3:  {'const': {2: 372},              'party': {46: 53, 21: 231}},
    4:  {'const': {2: 309, 5: 29},       'party': {21: 204}},
    5:  {'const': {2: 295, 3: 10},       'party': {9: 20,  21: 206}},
    6:  {'const': {2: 250, 3: 3},        'party': {9: 12,  21: 168}},
    7:  {'const': {2: 279},              'party': {9: 12,  21: 195}},
    8:  {'const': {2: 133, 3: 5},        'party': {9: 13,  21: 100}},
    9:  {'const': {2: 167, 5: 4},        'party': {9: 20,  21: 101}},
    10: {'const': {2: 271},              'party': {9: 34,  21: 183}},
    11: {'const': {2: 217, 3: 7},        'party': {9: 15,  21: 155}},
    12: {'const': {2: 131, 5: 10},       'party': {9: 7,   21: 94}},
    13: {'const': {2: 454},              'party': {9: 13,  21: 324}},
}

for unit, scores in khilek_data.items():
    # หน่วยที่ 2 has a special station name with สส.5-18(บช.) suffix
    if unit == 2:
        sn = f"{base}\\หน่วยที่ 2\\สส.5-18(บช.)"
    else:
        sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอน้ำขุ่น (ตำบลโคกสะอาด)
# ============================================================
base = "election_data\\อำเภอน้ำขุ่น\\ตำบลโคกสะอาด"

khoksa_data = {
    1:  {'const': {2: 190, 3: 6},        'party': {9: 15,  21: 120}},
    2:  {'const': {2: 90,  3: 3},        'party': {9: 11,  21: 60}},
    3:  {'const': {2: 237},              'party': {9: 11,  21: 147}},
    4:  {'const': {2: 318, 3: 18},       'party': {9: 48,  21: 214}},
    5:  {'const': {2: 85},               'party': {9: 5,   21: 49}},
    6:  {'const': {2: 408, 5: 31},       'party': {9: 22,  21: 284}},
    7:  {'const': {2: 309, 3: 21},       'party': {9: 22,  21: 199}},
    8:  {'const': {2: 348, 3: 9},        'party': {9: 22,  21: 328}},
    9:  {'const': {2: 158},              'party': {9: 10,  21: 105}},
    10: {'const': {2: 261},              'party': {9: 12,  21: 175}},
    11: {'const': {2: 151},              'party': {9: 13,  21: 100}},
    12: {'const': {2: 121},              'party': {9: 10,  21: 87}},
}

for unit, scores in khoksa_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอน้ำขุ่น (ตำบลตาเกา)
# Note: only หน่วยที่ 1, 10, 11, 12, 13, 14, 15 provided
# หน่วยที่ 1 has no party data given
# ============================================================
base = "election_data\\อำเภอน้ำขุ่น\\ตำบลตาเกา"

takao_data = {
    1:  {'const': {2: 256, 3: 14},       'party': {}},
    10: {'const': {2: 397, 3: 18},       'party': {9: 22,  21: 293}},
    11: {'const': {2: 90},               'party': {9: 5,   21: 65}},
    12: {'const': {2: 355, 3: 6},        'party': {9: 14,  21: 254}},
    13: {'const': {2: 202},              'party': {9: 30,  21: 140}},
    14: {'const': {2: 255, 5: 4},        'party': {9: 10,  21: 173}},
    15: {'const': {2: 184, 3: 3},        'party': {21: 141}},
}

for unit, scores in takao_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# อำเภอน้ำขุ่น (ตำบลไพบูลย์)
# ============================================================
base = "election_data\\อำเภอน้ำขุ่น\\ตำบลไพบูลย์"

paibun_data = {
    1:  {'const': {2: 288, 3: 33},       'party': {9: 30,  21: 181}},
    2:  {'const': {2: 100, 3: 19},       'party': {9: 22,  21: 71}},
    3:  {'const': {2: 108},              'party': {9: 24,  21: 75}},
    4:  {'const': {2: 166, 3: 10},       'party': {9: 10,  21: 127}},
    5:  {'const': {2: 197},              'party': {9: 20,  21: 130}},
    6:  {'const': {2: 207, 5: 13},       'party': {9: 20,  21: 152}},
    7:  {'const': {2: 171, 3: 9},        'party': {9: 22,  21: 102}},
    8:  {'const': {2: 207},              'party': {21: 166}},
    9:  {'const': {2: 74},               'party': {9: 22,  21: 60}},
    10: {'const': {2: 180},              'party': {9: 28,  21: 118}},
    11: {'const': {2: 147},              'party': {9: 12,  21: 115}},
    12: {'const': {2: 115},              'party': {9: 12,  21: 96}},
    13: {'const': {2: 145},              'party': {9: 26,  21: 90}},
    14: {'const': {2: 258},              'party': {9: 31,  21: 169}},
    15: {'const': {2: 263},              'party': {9: 14,  21: 186}},
}

for unit, scores in paibun_data.items():
    sn = f"{base}\\หน่วยที่ {unit}"
    item = get_item(sn)
    if item is None: continue
    for cand, score in scores['const'].items():
        if set_score(item, 'constituency_results', cand, score): changes += 1
    for cand, score in scores['party'].items():
        if set_score(item, 'party_list_results', cand, score): changes += 1

# ============================================================
# Save
# ============================================================
with open(r'data\data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nDone! Total score changes applied: {changes}")
