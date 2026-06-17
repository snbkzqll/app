import requests
import json

def fetch_easyeda(code):
    url = f"https://pro.lceda.cn/api/components/search"
    payload = {
        "searchKeyword": code,
        "page": 1,
        "pageSize": 10
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        print("EasyEDA Status:", res.status_code)
        if res.status_code == 200:
            print(res.json())
    except Exception as e:
        print("error", e)

fetch_easyeda("C12345")
