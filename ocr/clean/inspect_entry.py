import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'data\data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show first station with both results types (index 10 = ทุ่งศรีอุดม กุดเรือ หน่วยที่ 1)
item = data[10]
print("Station:", item['station_name'])
print()
print("constituency_results:")
for r in item['constituency_results']:
    print(" ", r)
print()
print("party_list_results (first 5):")
for r in item['party_list_results'][:5]:
    print(" ", r)

# Also check ล่วงหน้า entry
print("\n=== ล่วงหน้า ชุดที่ 1 ===")
item0 = data[0]
print("Station:", item0['station_name'])
print("constituency_results:", item0['constituency_results'])
print("party_list_results (first 10):")
for r in item0['party_list_results'][:10]:
    print(" ", r)
