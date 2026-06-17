import requests

def fetch_jlcpcb(code):
    url = "https://jlcpcb.com/shoppingCart/smtGood/selectSmtComponentList"
    payload = {
        "keyword": code,
        "searchSource": "search",
        "componentAttributes": []
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        print("JLCPCB Status:", res.status_code)
        if res.status_code == 200:
            print("JLCPCB JSON keys:", res.json().keys())
            data = res.json().get('data', {}).get('componentPageInfo', {}).get('list', [])
            if data:
                item = data[0]
                print(item.get('componentCode'), item.get('componentModelEn'), item.get('describe'))
            else:
                print("No results found or different structure")
    except Exception as e:
        print("error", e)

fetch_jlcpcb("C12345")
