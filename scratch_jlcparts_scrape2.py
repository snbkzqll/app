import requests
from bs4 import BeautifulSoup

url = "https://jlcparts.com/part/C2906873"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
try:
    res = requests.get(url, headers=headers, timeout=5)
    print("status", res.status_code)
    soup = BeautifulSoup(res.text, 'html.parser')
    for h1 in soup.find_all("h1"): print(h1.text)
    for p in soup.find_all("p"):
        if "Ω" in p.text or "F" in p.text: print(p.text)
except Exception as e:
    print(e)
