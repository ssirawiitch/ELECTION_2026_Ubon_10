import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'data\data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show all ล่วงหน้า entries
print("=== ล่วงหน้า entries ===")
for i, item in enumerate(data):
    if 'ล่วงหน้า' in item['station_name']:
        sn = item['station_name']
        clen = len(item['constituency_results'])
        plen = len(item['party_list_results'])
        print(f"Index {i}: {sn} | const={clen}, party={plen}")
        if item['constituency_results']:
            print("  const results:")
            for r in item['constituency_results']:
                print(f"    no={r['number']}, score={r['score']}")
        if item['party_list_results']:
            # show just no 2 and no 5 and no 21 and no 46
            for r in item['party_list_results']:
                if r['number'] in [2, 5, 21, 46]:
                    print(f"  party no={r['number']}, score={r['score']}")
        print()
