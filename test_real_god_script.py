import sys
import os
# setup environment
os.environ["API_KEY"] = "1a8ea1d1c38d45c38ca221b884492a46.lxGhbfNhMEPUmucZ"
os.environ["MODEL_NAME"] = "glm-4.5"
os.environ["BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4/"

from app.agent.real_god import RealGodAgent

agent = RealGodAgent()
for event in agent.run("阿尔伯特·爱因斯坦", 1):
    print(event)
