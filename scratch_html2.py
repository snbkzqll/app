import requests

def fetch_html(code):
    url = f"https://item.szlcsc.com/{code}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        print("HTML Status:", res.status_code)
        if res.status_code == 200:
            print(res.text[:1500])
    except Exception as e:
        print("HTML error:", e)

fetch_html("C12345")
