import requests

def fetch_lcsc3(code):
    url = "https://wmsc.lcsc.com/wmsc/search/global"
    # url = "https://so.szlcsc.com/api/search/global" (if above fails)
    
    # Try different payloads based on common JLC endpoints
    payload = {
        "keyword": code,
        "pageNumber": 1,
        "pageSize": 10
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        # wmsc needs json sometimes
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        print("wmsc json Status:", res.status_code)
        if res.status_code == 200:
            print("wmsc json result:", res.json().get('code'))
            if res.json().get('code') == 200:
                print(res.json()['result']['productDetailList'][0])
                return
    except Exception as e:
        print("wmsc json error:", e)

fetch_lcsc3("C12345")
