import requests
import json

def test_jlcpcb_api(code):
    # JLCPCB SMT parts search endpoint (often public)
    url = "https://jlcpcb.com/shoppingCart/smtGood/selectSmtComponentList"
    payload = {
        "keyword": code,
        "searchSource": "search",
        "componentAttributes": []
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        print("selectSmtComponentList POST:", res.status_code)
        if res.status_code == 200:
            print(res.text[:200])
    except Exception as e:
        print("error 1:", e)

    # Another JLCPCB endpoint
    url2 = "https://jlcpcb.com/api/ext/component/searchComponentInfo"
    payload2 = {
        "keyword": code,
        "pageNumber": 1,
        "pageSize": 10
    }
    try:
        res2 = requests.post(url2, json=payload2, headers=headers)
        print("searchComponentInfo POST:", res2.status_code)
        if res2.status_code == 200:
            print(res2.text[:200])
    except Exception as e:
        print("error 2:", e)

test_jlcpcb_api("C12345")
test_jlcpcb_api("C2906873")
