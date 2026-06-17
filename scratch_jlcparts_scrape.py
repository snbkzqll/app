import requests
from bs4 import BeautifulSoup

def test_jlcparts_scrape(code):
    url = f"https://jlcparts.com/part/{code}"
    try:
        res = requests.get(url, timeout=5)
        print("jlcparts:", res.status_code)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # The description might be somewhere in the text
            print("Title:", soup.title.string if soup.title else "No title")
            # Usually it's in a specific meta tag or div
            for meta in soup.find_all("meta"):
                print(meta.get("name"), meta.get("content"))
    except Exception as e:
        print("err:", e)

test_jlcparts_scrape("C2906873")
