import requests

def test_so_lcsc(code):
    url = f"https://so.szlcsc.com/api/search/global"
    payload = {"keyword": code, "page": 1, "pageSize": 10}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        print("so.szlcsc.com:", res.status_code)
        if res.status_code == 200:
            data = res.json()
            if data.get("result", {}).get("productDetailList"):
                print(data["result"]["productDetailList"][0])
            else:
                print("no productDetailList:", data)
    except Exception as e:
        print("err:", e)

test_so_lcsc("C2906873")
