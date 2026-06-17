import requests
import json

url = "https://jlcsearch.tscircuit.com/components/list.json?search=C2906873"
try:
    res = requests.get(url, timeout=5)
    data = res.json()
    print(json.dumps(data["components"][0], indent=2))
except Exception as e:
    print(e)
