import requests

def test_jlcparts(code):
    # Testing known community aggregators
    url1 = f"https://jlcparts.com/api/part/{code}"
    try:
        res = requests.get(url1, timeout=5)
        print("url1:", res.status_code)
    except: pass

test_jlcparts("C12345")
