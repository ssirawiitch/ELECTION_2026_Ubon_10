import json
import os

def count_needs_review():
    file_path = os.path.join("data", "election_insights_final.json")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        total_items = 0
        needs_review_count = 0
        
        for station in data:
            # ตรวจสอบรายการใน party_list_results
            for party in station.get('party_list_results', []):
                total_items += 1
                if party.get('needs_review') is True:
                    needs_review_count += 1
                    
            # ถ้ามี constituency_results ให้เช็คด้วย (ขึ้นอยู่กับโครงสร้างข้อมูลจริง)
            for constituency in station.get('constituency_results', []):
                total_items += 1
                if constituency.get('needs_review') is True:
                    needs_review_count += 1
                    
        print(f"รวมรายการทั้งหมดที่ OCR: {total_items:,} รายการ")
        print(f"จำนวนรายการที่ต้องตรวจสอบ (needs_review = True): {needs_review_count:,} รายการ")
        if total_items > 0:
            print(f"คิดเป็นร้อยละ: {(needs_review_count/total_items)*100:.2f}% ของทั้งหมด")
            
    except FileNotFoundError:
        print(f"ไม่พบไฟล์: {file_path}")
    except json.JSONDecodeError:
        print(f"ไฟล์ {file_path} ไม่ใช่รูปแบบ JSON ที่ถูกต้อง")

if __name__ == "__main__":
    count_needs_review()
