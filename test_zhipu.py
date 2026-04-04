from zhipuai import ZhipuAI
import os

client = ZhipuAI(
    api_key="1a8ea1d1c38d45c38ca221b884492a46.lxGhbfNhMEPUmucZ",
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

try:
    response = client.chat.completions.create(
        model="GLM-4.7-Flash",
        messages=[
            {"role": "user", "content": "你好"}
        ]
    )
    print("Success:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error:")
    print(e)
