import requests
from bs4 import BeautifulSoup
import re

def scrape_description_from_bing(code):
    url = f"https://www.bing.com/search?q={code}+lcsc"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Look at all h2 tags or cite
            for h2 in soup.find_all("h2"):
                text = h2.get_text()
                if "LCSC" in text or code in text:
                    print("Found heading:", text)
            for p in soup.find_all("p"):
                text = p.get_text()
                if "Ω" in text or "F" in text or "%" in text:
                    print("Found paragraph:", text)
    except Exception as e:
        print("err:", e)

scrape_description_from_bing("C2906873")
