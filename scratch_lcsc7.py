import requests

def fetch_lceda_form(code):
    url = f"https://pro.lceda.cn/api/components/search"
    payload = {
        "searchKeyword": code,
        "page": 1,
        "pageSize": 10
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        res = requests.post(url, data=payload, headers=headers, timeout=5)
        print("EasyEDA Form Status:", res.status_code)
        if res.status_code == 200:
            print(res.json().get('success'))
            if res.json().get('success'):
                data = res.json().get('result', {})
                print("Found:", data.keys())
            else:
                print(res.json())
    except Exception as e:
        print("error", e)

fetch_lceda_form("C12345")
