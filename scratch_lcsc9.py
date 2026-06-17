import requests

def test_easyeda_with_cookies(code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://pro.lceda.cn",
        "Referer": "https://pro.lceda.cn/editor",
    }
    try:
        url = "https://pro.lceda.cn/api/components/search"
        payload = {"searchKeyword": code, "page": 1, "pageSize": 10}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        print("status:", res.status_code)
        if res.status_code == 200:
            print(res.json())
        else:
            print(res.text)
    except Exception as e:
        print(e)

test_easyeda_with_cookies("C2906873")
test_easyeda_with_cookies("C12345")
