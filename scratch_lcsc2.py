import requests

def fetch_lceda(code):
    url = f"https://lceda.cn/api/components/search"
    payload = {
        "keyword": code,
        "type": 3,
        "page": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        res = requests.post(url, data=payload, headers=headers, timeout=5)
        print("Status:", res.status_code)
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                item = data['result']['lists'][0]
                print("Title:", item.get('title'))
                print("Package:", item.get('packageDetail'))
                print("Supplier Code:", item.get('supplierNumber'))
                print("Supplier:", item.get('supplier'))
                print("Value:", item.get('description'))
                print("Data:", item.get('dataStr'))
            else:
                print("API Error:", data)
    except Exception as e:
        print("LCEDA error:", e)

fetch_lceda("C12345")
