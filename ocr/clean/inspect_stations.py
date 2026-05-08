import json

# Read raw bytes and detect encoding
with open(r'data\data.json', 'rb') as f:
    raw = f.read(200)
print("First 200 bytes:", raw[:200])
print()

# Try reading with different encodings
for enc in ['utf-8', 'cp874', 'tis-620', 'utf-8-sig']:
    try:
        with open(r'data\data.json', 'r', encoding=enc) as f:
            data = json.load(f)
        print(f"Encoding {enc} works!")
        for i, item in enumerate(data[:5]):
            print(f"  {i}: {item['station_name']}")
        break
    except Exception as e:
        print(f"Encoding {enc} failed: {e}")
