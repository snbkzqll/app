import requests

def fetch_lcsc(code):
    url = f"https://wmsc.lcsc.com/wmsc/search/global?keyword={code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Alternatively try the new easyeda api if you know it
    # https://pro.lceda.cn/api/components/search
    
    try:
        res = requests.post("https://wmsc.lcsc.com/wmsc/search/global", data={"keyword": code}, headers=headers, timeout=5)
        print("LCSC WMSC POST Status:", res.status_code)
        # print(res.text[:200])
    except Exception as e:
        print("LCSC WMSC error:", e)

    try:
        payload = {"keyword": code, "page": 1, "pageSize": 10}
        res2 = requests.post("https://pro.lceda.cn/api/components/search", json=payload, headers=headers, timeout=5)
        print("LCEDA PRO Status:", res2.status_code)
        if res2.status_code == 200:
            print(res2.json())
    except Exception as e:
        print("LCEDA PRO error:", e)

fetch_lcsc("C12345")
