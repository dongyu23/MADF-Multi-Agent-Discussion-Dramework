from zhipuai import ZhipuAI

api_key = "1a8ea1d1c38d45c38ca221b884492a46.lxGhbfNhMEPUmucZ"
client = ZhipuAI(api_key=api_key)
print("Starting search...")
try:
    response = client.web_search.web_search(
        search_engine="search_std",
        search_query="阿尔伯特·爱因斯坦"
    )
    print("Search result:", response)
except Exception as e:
    print("Error:", e)
