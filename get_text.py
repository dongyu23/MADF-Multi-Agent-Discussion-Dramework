import requests
print(requests.get("http://localhost:5173/personas").text[:100])
