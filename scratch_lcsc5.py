import requests

def fetch_lceda_get(code):
    url = f"https://lceda.cn/api/components/search?keyword={code}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        print("EasyEDA GET Status:", res.status_code)
        if res.status_code == 200:
            print(res.json())
    except Exception as e:
        print("error", e)

fetch_lceda_get("C12345")
