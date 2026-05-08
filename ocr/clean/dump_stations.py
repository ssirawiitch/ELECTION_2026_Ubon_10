import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r'data\data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('station_names.txt', 'w', encoding='utf-8') as out:
    for i, item in enumerate(data):
        clen = len(item["constituency_results"])
        plen = len(item["party_list_results"])
        out.write(f'{i}: {item["station_name"]}  | const={clen}, party={plen}\n')

print("Done. Written to station_names.txt")
