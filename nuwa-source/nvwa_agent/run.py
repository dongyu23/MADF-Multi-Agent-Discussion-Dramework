#!/usr/bin/env python3
"""
Nvwa Agent 启动脚本

使用方法:
    python run.py                    # 交互模式
    python run.py "你的问题"          # 单次查询
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from agent import create_nvwa_agent

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}")


def print_stream_event(event):
    """打印流式事件"""
    for node_name, node_data in event.items():
        if node_name == "__start__" or node_name == "__end__":
            continue

        print(f"\n{'='*60}")
        print(f"📍 节点: {node_name}")
        print(f"{'='*60}")

        # 跳过空节点数据
        if node_data is None:
            continue

        # 打印消息
        if "messages" in node_data:
            messages = node_data["messages"]
            if not isinstance(messages, list):
                messages = [messages]

            for msg in messages:
                if hasattr(msg, "content"):
                    content = msg.content
                    msg_type = msg.__class__.__name__

                    if msg_type == "AIMessage":
                        print(f"\n🤖 AI: {content}")
                    elif msg_type == "ToolMessage":
                        print(f"\n🔧 工具结果: {content[:200]}..." if len(str(content)) > 200 else f"\n🔧 工具结果: {content}")
                    elif msg_type == "HumanMessage":
                        print(f"\n👤 用户: {content}")
                    else:
                        print(f"\n📝 {msg_type}: {content}")

                # 打印工具调用
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        print(f"\n🔨 调用工具: {tool_call.get('name', 'unknown')}")
                        print(f"   参数: {tool_call.get('args', {})}")


def main():
    """主函数"""
    print("🎭 女娲智能体 - 启动中...")
    print("=" * 60)

    # 创建 agent
    agent = create_nvwa_agent()
    print("\n✅ Agent 已就绪！\n")

    # 为多轮对话创建一个固定的 thread_id
    config = {"configurable": {"thread_id": "nvwa-conversation-1"}}

    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 单次查询模式
        query = " ".join(sys.argv[1:])
        print(f"📝 查询: {query}\n")

        # 使用流式输出，传入 config 以支持多轮对话
        for event in agent.stream({"messages": [{"role": "user", "content": query}]}, config):
            print_stream_event(event)

        print("\n" + "="*60)
        print("✅ 执行完成")
        print("="*60 + "\n")
    else:
        # 交互模式
        print("💬 交互模式 (输入 'quit' 或 'exit' 退出)")
        print("💡 支持多轮对话，agent 会记住之前的对话内容\n")

        while True:
            try:
                query = input("👤 你: ").strip()

                if not query:
                    continue

                if query.lower() in ["quit", "exit", "退出"]:
                    print("\n👋 再见！")
                    break

                print()
                # 使用流式输出，传入 config 以支持多轮对话
                for event in agent.stream({"messages": [{"role": "user", "content": query}]}, config):
                    print_stream_event(event)

                print("\n" + "="*60)
                print("✅ 执行完成")
                print("="*60 + "\n")

            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}\n")


if __name__ == "__main__":
    main()
