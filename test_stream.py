import requests

# Login
res = requests.post("http://127.0.0.1:8000/api/v1/auth/login", data={"username": "test2", "password": "password123"})
print("Login:", res.text)
token = res.json().get("access_token")

if token:
    print("Starting generation...")
    res = requests.post("http://127.0.0.1:8000/api/v1/god/generate_real", json={"prompt": "阿尔伯特·爱因斯坦", "n": 1}, headers={"Authorization": f"Bearer {token}"}, stream=True)

    try:
        for line in res.iter_lines():
            if line:
                print(line.decode("utf-8"))
    except Exception as e:
        print(f"Exception during stream: {e}")
