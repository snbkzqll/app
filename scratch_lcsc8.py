import requests

def test_wd():
    url = "https://lceda.cn/api/components/search"
    res = requests.get(url, params={'wd': 'C12345'}, headers={'User-Agent': 'Mozilla/5.0'})
    print(res.status_code)
    try:
        print(res.json())
    except:
        pass

test_wd()
