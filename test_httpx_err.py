import httpx
try:
    httpx.get("http://0.0.0.0:12345")
except Exception as e:
    print("str(e) is:", repr(str(e)))
