import requests
from bs4 import BeautifulSoup
import re

def fetch_html(code):
    url = f"https://item.szlcsc.com/{code}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        print("HTML Status:", res.status_code)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # extract basic info
            # print(soup.title.text)
            
            # We can also extract from scripts window.pageConfig
            script_tags = soup.find_all("script")
            for tag in script_tags:
                if tag.string and "window.pageConfig =" in tag.string:
                    # extract json
                    match = re.search(r'window\.pageConfig\s*=\s*({.*});', tag.string, re.DOTALL)
                    if match:
                        import json
                        try:
                            data = json.loads(match.group(1))
                            product = data.get("productDetail", {})
                            print("Name:", product.get("productModel"))
                            print("Package:", product.get("encapsulation"))
                            print("Category:", product.get("catalogName"))
                            print("Description:", product.get("productDesc"))
                            
                            img = data.get("productImages", [])
                            if img:
                                print("Image:", img[0])
                            return
                        except Exception as e:
                            print("JSON parse error", e)
                            
    except Exception as e:
        print("HTML error:", e)

fetch_html("C12345")
