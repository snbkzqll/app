import requests

url = "https://easyeda.com/api/components/search"
params = {"wd": "C12345"}
headers = {"User-Agent": "Mozilla/5.0"}
try:
    res = requests.get(url, params=params, headers=headers, timeout=5)
    print("status", res.status_code)
    if res.status_code == 200:
        print(res.json())
except Exception as e:
    print(e)
