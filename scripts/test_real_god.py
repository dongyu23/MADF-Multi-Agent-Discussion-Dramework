import asyncio
import os
import sys

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.real_god import RealGodAgent
from app.core.config import settings

async def test_real_god():
    print(f"Testing RealGodAgent with LLM Base URL: {settings.final_base_url}")
    agent = RealGodAgent(max_steps=5)
    
    print("\n--- Starting Generation ---")
    try:
        generator = agent.run("生成爱因斯坦", n=1)
        for event in generator:
            if event["type"] == "thought_chunk":
                print(event["content"], end="", flush=True)
            elif event["type"] in ["thought", "action", "observation", "error", "result"]:
                print(f"\n[{event['type'].upper()}]: {str(event['content'])[:500]}")
    except Exception as e:
        print(f"\n[EXCEPTION]: {e}")
        
if __name__ == "__main__":
    asyncio.run(test_real_god())
