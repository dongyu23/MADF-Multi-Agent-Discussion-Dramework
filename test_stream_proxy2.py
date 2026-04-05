import requests

res = requests.post("http://127.0.0.1:5173/api/v1/auth/login", data={"username": "test2", "password": "password123"})
token = res.json().get("access_token")

res = requests.post("http://127.0.0.1:5173/api/v1/god/generate_real", json={"prompt": "爱因斯坦", "n": 1}, headers={"Authorization": f"Bearer {token}"}, stream=True)

try:
    for line in res.iter_lines():
        if line:
            print(line.decode("utf-8"))
except Exception as e:
    print(f"Exception during stream: {e}")
