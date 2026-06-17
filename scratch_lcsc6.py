import requests

def test_jlcpcb_detail(code):
    url = f"https://jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode={code}"
    try:
        res = requests.get(url, timeout=5)
        print("getComponentDetail:", res.status_code)
        if res.status_code == 200:
            print(res.text[:300])
    except Exception as e:
        print("err:", e)

def test_lcsc_detail(code):
    url = f"https://wmsc.lcsc.com/wmsc/product/detail?productCode={code}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        print("wmsc detail:", res.status_code)
        if res.status_code == 200:
            print(res.text[:300])
    except Exception as e:
        print("err:", e)

test_jlcpcb_detail("C12345")
test_lcsc_detail("C12345")
