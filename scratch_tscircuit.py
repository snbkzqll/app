import requests

def test_tscircuit(code):
    url = f"https://jlcsearch.tscircuit.com/components/list.json?search={code}"
    try:
        res = requests.get(url, timeout=5)
        print("tscircuit:", res.status_code)
        if res.status_code == 200:
            print(res.json())
    except Exception as e:
        print(e)

test_tscircuit("C2906873")
test_tscircuit("C12345")
