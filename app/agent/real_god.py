import json
import re
import requests
from typing import List, Dict, Any, Generator, Tuple, Optional
from utils import get_chat_completion, parse_json_from_response
from app.core.config import settings
from zhipuai import ZhipuAI

# ==========================================
# Prompts
# ==========================================

COUNT_EXTRACT_PROMPT = """
你是一个辅助助手。请从用户的描述中提取需要生成的角色数量。
用户描述：{user_prompt}

请仅输出一个数字（整数）。
如果用户没有明确指定数量，默认为 1。
如果用户暗示了多个（例如“几个”、“一对”），请根据语境推断最合理的数量（不超过 5）。

只输出数字，不要包含任何其他文字。
"""

REACT_SYS_PROMPT = """
你是一个拥有互联网搜索能力的上帝智能体（RealGodAgent）。
你的任务是根据用户需求，通过联网搜索获取真实信息，并基于这些信息生成详细的角色设定（Persona）。

【当前任务】
用户需求：{user_prompt}
进度：正在生成第 {current_index} 位角色（计划生成 {total_count} 位）。
已生成角色列表（本轮）：{generated_names}

【本轮生成上下文 (避免重复/保持连贯)】
{session_context}

【严禁重复 (Anti-Duplication)】
- **绝对禁止**再次生成已生成的角色（{generated_names}）。
- **绝对禁止**生成数据库中已存在的角色（{db_existing_names}）。
- **绝对禁止**对已生成的角色进行“补充”、“深化”或“更详细版本”的生成。
- 你必须生成一个**全新的**、与上述角色**不同的**人物。
- 如果用户需求比较模糊（如“生成两个物理学家”），请确保每位角色都是独立的个体。

【思维与行动准则 (ReAct)】
你必须严格遵循 "Thought" -> "Action" -> "Observation" 的循环模式。

1. **Thought (思考)**：
   - 分析当前需要什么信息。
   - 第一次搜索应广泛，确定人物原型。
   - 第二次搜索应深入，补充细节。
   - 关键词至少有3个
   - 注意：你最多只能进行 **2次** 搜索。
   - **去重检查**：如果上下文中已存在某个角色的详细信息，请务必选择一个完全不同的人物进行生成。

2. **Action (行动)**：
   - 使用 `Search[关键词]` 进行搜索。
   - 使用 `Finish[JSON数据]` 提交最终结果。

3. **Observation (观察)**：
   - 搜索工具会返回结果，请基于结果进行下一步思考。

【输出格式】
Thought: <你的思考内容>
Action: Search[关键词]  (或 Finish[JSON])

【JSON 数据格式要求】
提交的 JSON 必须包含以下字段（确保是合法的 JSON，不要使用 Markdown 代码块，不要包含注释）：
- name: 姓名
- title: 头衔/职业
- bio: 深度生平（400字以上，包含教育、成就、挫折）
- theories: 7个具体理论/主张/成就（数组，字符串列表）
- stance: 性格与立场（400字以上，包含价值观、对待争议的态度）
- system_prompt: 第一人称扮演提示词

【Action 样例】
Action: Search[2024年诺贝尔物理学奖得主]
Action: Finish[{{"name": "杰弗里·辛顿", "title": "AI教父", "bio": "...", "theories": ["深度信念网络", "反向传播"], "stance": "...", "system_prompt": "..."}}]

请确保所有字符串中的双引号都已正确转义（例如使用 \"），不要使用单引号包围 JSON 键或值。
JSON必须是标准的，不要使用 ```json ... ``` 包裹。
请开始你的思考。
"""

# ==========================================
# Agent Class
# ==========================================

import logging
import asyncio
from datetime import datetime
from app.core.config import settings
from utils import get_chat_completion

# Configure logging
logger = logging.getLogger(__name__)

class RealGodAgent:
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self.searched_queries = set()

    def search(self, query: str) -> str:
        """
        Perform web search using ZhipuAI Web Search API via SDK.
        """
        # Ensure we use the latest configuration (e.g. from environment)
        current_api_key = settings.final_api_key
        
        try:
            if not current_api_key:
                return "Error: API_KEY is not set."

            logger.info(f"Searching with ZhipuAI Web Search: {query}")
            
            # Initialize ZhipuAI client (simulating 'zai' usage as requested)
            client = ZhipuAI(api_key=current_api_key)
            
            # Call web_search as per user sample
            response = client.web_search.web_search(
                search_engine="search_std",
                search_query=query,
                count=5, 
                search_recency_filter="noLimit",
                content_size="high"
            )
            
            
            search_results = []
            if isinstance(response, dict):
                 search_results = response.get("search_result", [])
            elif hasattr(response, "search_result"):
                 search_results = response.search_result
            else:
                 # Fallback/Debug
                 logger.warning(f"Unknown response format: {response}")
                 return f"Search returned unknown format: {response}"

            if search_results:
                formatted_results = []
                for r in search_results:
                    # Handle both dict and object access if possible
                    if isinstance(r, dict):
                        title = r.get("title", "No Title")
                        link = r.get("link", "#")
                        content = r.get("content", "No Content")
                        media = r.get("media", "")
                    else:
                        title = getattr(r, "title", "No Title")
                        link = getattr(r, "link", "#")
                        content = getattr(r, "content", "No Content")
                        media = getattr(r, "media", "")
                        
                    formatted_results.append(f"Title: {title}\nSource: {media}\nLink: {link}\nSnippet: {content}")
                
                return "\n\n".join(formatted_results)
            else:
                return "No search results found."

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search error: {str(e)}"

    def _call_llm(self, messages: List[Dict[str, str]], stream: bool = True) -> Generator[Dict[str, Any], None, str]:
        """Helper to call LLM and yield events."""
        full_text = ""
        
        try:
            # Increase timeout to 60s for better stability
            # Enable raise_error to catch specific exceptions
            response_stream = get_chat_completion(messages, stream=True, timeout=60, raise_error=True)
            
            if not response_stream:
                yield {"type": "error", "content": "LLM未响应 (返回为空)"}
                return ""

            for chunk in response_stream:
                if not chunk.choices: continue
                delta = chunk.choices[0].delta.content or ""
                if not delta: continue
                
                full_text += delta
                # Stream raw delta as thought_chunk
                yield {"type": "thought_chunk", "content": delta}

        except Exception as e:
            error_msg = str(e)
            
            # 尝试获取当前的 API Key 以便调试 (仅在安全环境中)
            try:
                current_key = settings.final_api_key
                # Mask key for partial safety: first 5 and last 5 chars
                if len(current_key) > 10:
                    masked_key = f"{current_key}...{current_key[-5:]}"
                else:
                    masked_key = current_key
            except:
                masked_key = "Unknown/Not Set"
                
            logger.error(f"LLM Call Error in RealGodAgent: {error_msg}")
            
            # Use stdout for critical errors to ensure they appear in Docker logs
            import sys
            print(f"[CRITICAL] LLM Call Error: {error_msg}", file=sys.stderr)
            print(f"[CRITICAL] Debug Info - API Key: {masked_key}, Model: {settings.final_model_name}, Base URL: {settings.final_base_url}", file=sys.stderr)
            
            # Provide more user-friendly error messages for common issues
            if "401" in error_msg:
                user_msg = f"鉴权失败 (401): API Key 无效或过期。当前使用 Key: {masked_key}"
            elif "404" in error_msg:
                user_msg = f"资源未找到 (404): 模型 '{settings.final_model_name}' 不存在或 API 路径错误。URL: {settings.final_base_url}"
            elif "429" in error_msg:
                user_msg = "请求过于频繁 (429): 达到 API 速率限制，请稍后重试。"
            elif "timeout" in error_msg.lower():
                user_msg = "请求超时: LLM 响应时间过长 (Timeout)"
            elif "connection" in error_msg.lower():
                user_msg = f"网络错误: 无法连接到 LLM 服务 ({settings.final_base_url})"
            else:
                user_msg = f"LLM 错误: {error_msg}"
                
            yield {"type": "error", "content": user_msg}
            # Important: Log the error to frontend via 'error' type
            # And return empty string to stop this turn
            return ""

        return full_text

    def _get_persona_count(self, prompt: str) -> int:
        """Determines N using a lightweight LLM call."""
        try:
            sys_prompt = COUNT_EXTRACT_PROMPT.format(user_prompt=prompt)
            # Use a fresh, short call with 60s timeout
            response = get_chat_completion([{"role": "user", "content": sys_prompt}], stream=False, timeout=60)
            if response and response.choices:
                content = response.choices[0].message.content.strip()
                match = re.search(r"\d+", content)
                if match:
                    return int(match.group(0))
            return 1
        except Exception as e:
            # Fallback
            return 1

    def run(self, prompt: str, n: int = None, generated_names: List[str] = None, db_existing_names: List[str] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Runs the ReAct Agent loop.
        """
        if generated_names is None:
            generated_names = []
            
        if db_existing_names is None:
            db_existing_names = []
            
        # Combine for initial context awareness (but keep separate for logic)
        # Maybe just use db_existing_names in prompt.

        # Future for N
        future_n = None
        executor = None
        
        # 1. Start N determination in background if not provided
        if n is None:
             from concurrent.futures import ThreadPoolExecutor
             executor = ThreadPoolExecutor(max_workers=1)
             # Submit background task
             future_n = executor.submit(self._get_persona_count, prompt)
             
             # Assume 1 for now to start immediately
             n = 1 
             yield {"type": "count", "content": 1}
        
        # 2. Main Loop for each character
        i = 0
        session_context = "无"
        
        # Initialize searched queries set OUTSIDE the loop to persist across characters
        self.searched_queries = set()
        
        while i < n:
            current_index = i + 1
            
            # Check if N has been updated from background task
            if future_n and future_n.done():
                 try:
                     real_n = future_n.result()
                     if real_n > n:
                         n = real_n
                         # Limit N to prevent abuse
                         if n > 5: n = 5
                         yield {"type": "count", "content": n}
                         yield {"type": "thought", "content": f"已识别需求，更新计划生成 {n} 位角色。"}
                     future_n = None # Handled
                 except Exception as e:
                     yield {"type": "error", "content": f"获取数量失败: {e}"}
                     future_n = None

            # Dynamic message that reflects current N
            progress_msg = f"=== 开始生成第 {current_index} 位角色 (共 {n} 位) ==="
            yield {"type": "thought_start", "content": progress_msg}
            yield {"type": "progress", "current": current_index, "total": n}
            
            # Reset per-character state (but NOT searched_queries)
            character_history = [] 
            search_count = 0
            
            # Construct System Prompt
            sys_msg = REACT_SYS_PROMPT.format(
                user_prompt=prompt,
                current_index=current_index,
                total_count=n,
                generated_names=", ".join(generated_names) if generated_names else "无",
                db_existing_names=", ".join(db_existing_names[:50]) + "..." if len(db_existing_names) > 50 else (", ".join(db_existing_names) if db_existing_names else "无"),
                session_context=session_context
            )
            
            character_history.append({"role": "system", "content": sys_msg})
            character_history.append({"role": "user", "content": "请开始。"})
            
            # Pre-fill thought to reduce perceived latency
            yield {"type": "thought_chunk", "content": "正在根据当前进度和已生成角色列表，规划本轮角色的生成策略...\n"}
            
            # ReAct Inner Loop
            step = 0
            finished = False
            
            while step < self.max_steps and not finished:
                step += 1
                
                # Periodically check for N update inside the loop too
                if future_n and future_n.done():
                     try:
                         real_n = future_n.result()
                         if real_n > n:
                             n = real_n
                             if n > 5: n = 5
                             yield {"type": "count", "content": n}
                             yield {"type": "thought", "content": f"已识别需求，更新计划生成 {n} 位角色。"}
                         future_n = None
                     except Exception:
                         future_n = None

                # Call LLM
                full_resp = yield from self._call_llm(character_history)
                character_history.append({"role": "assistant", "content": full_resp})
                
                # Parse Thought/Action
                thought, action = self._parse_output(full_resp)
                
                if thought:
                    yield {"type": "thought", "content": thought}
                
                if not action:
                    # If LLM didn't output action, prompt it
                    if step >= self.max_steps:
                         yield {"type": "error", "content": "达到最大步数，停止。"}
                         break
                    obs = "系统提示：请输出 Action。例如 Action: Search[...] 或 Action: Finish[...]"
                    character_history.append({"role": "user", "content": f"Observation: {obs}"})
                    continue
                    
                # Execute Action
                if action.startswith("Search") or "Search[" in action:
                    tool_name, query = self._parse_action(action)
                    if not query:
                        # Parsing failed or empty
                        obs = "系统提示：无法解析搜索关键词。请使用格式：Action: Search[关键词]"
                        yield {"type": "error", "content": obs}
                        character_history.append({"role": "user", "content": f"Observation: {obs}"})
                        continue

                        
                    self.searched_queries.add(query)
                    search_count += 1
                    
                    yield {"type": "action", "content": f"搜索: {query}"}
                    obs = self.search(query)
                    yield {"type": "observation", "content": obs}
                    
                    # Prepare Next Prompt
                    next_user_msg = f"Observation: {obs}"
                    
                    # **Logic Injection**: Force Finish after 2nd search
                    if search_count >= 2:
                        next_user_msg += "\n\n[系统提示]: 这是你的最后一次搜索。请根据现有信息，立即使用 Action: Finish[...] 生成角色 JSON。"
                    
                    character_history.append({"role": "user", "content": next_user_msg})

                elif action.startswith("Finish") or "Finish[" in action:
                    json_str = self._parse_action_input(action)
                    
                    # Try to parse JSON
                    persona = parse_json_from_response(json_str)
                    
                    if persona:
                        if isinstance(persona, dict):
                            persona = [persona]
                        
                        # Add to generated names context
                        for p in persona:
                            if isinstance(p, dict) and "name" in p:
                                name = p["name"]
                                generated_names.append(name)
                                
                                # Update session context for next character
                                bio_snippet = p.get("bio", "")[:100] + "..."
                                if session_context == "无":
                                    session_context = ""
                                session_context += f"\n- 已生成角色: {name} ({p.get('title', '未知')})\n  简介: {bio_snippet}\n"
                            else:
                                # Handle case where p is not a dict or missing name
                                logger.warning(f"Skipping invalid persona entry: {p}")
                                
                        yield {"type": "result", "content": persona}
                        finished = True
                    else:
                        obs = "系统提示：JSON 解析失败，请检查格式（确保包含 name, bio, theories 等字段）并重试。"
                        yield {"type": "error", "content": obs}
                        character_history.append({"role": "user", "content": f"Observation: {obs}"})
                
                else:
                    obs = "系统提示：未知指令。请严格使用 Action: Search[...] 或 Action: Finish[...]"
                    character_history.append({"role": "user", "content": f"Observation: {obs}"})

            # Increment loop counter
            i += 1
            
        # Ensure executor shutdown if it was created
        if executor:
            executor.shutdown(wait=False)

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Parses Thought and Action from LLM output."""
        thought = None
        action = None
        
        # Regex for Thought
        # 优化：支持中文冒号，支持 Action 位于新行或同一行
        thought_match = re.search(r"(?:Thought|思考)[:：]\s*(.*?)(?=\n(?:Action|行动)[:：]|$)", text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
        else:
            # 如果没有找到明确的 Thought 标记，但有 Action 标记，
            # 那么 Action 之前的所有内容都可以被视为 Thought
            action_start_match = re.search(r"(?:Action|行动)[:：]", text, re.IGNORECASE)
            if action_start_match:
                thought = text[:action_start_match.start()].strip()
            
        # Regex for Action
        # 优化：支持中文冒号，确保能够匹配到行尾
        action_match = re.search(r"(?:Action|行动)[:：]\s*(.*?)$", text, re.DOTALL | re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()
        else:
            # Fallback for Finish[...], which might contain nested brackets breaking simple regex
            if "Finish[" in text:
                 # Find start of Finish[
                 start_idx = text.find("Finish[")
                 # Take everything from there to the end, assuming Action is last
                 candidate = text[start_idx:].strip()
                 action = candidate
            elif "Search[" in text:
                 match = re.search(r"(Search\[.*?\])", text, re.DOTALL)
                 if match: action = match.group(1)

        return thought, action

    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """Parses Tool and Input from Action string."""
        if action_text.startswith("Finish[") or "Finish[" in action_text:
            # Find the first 'Finish['
            start = action_text.find("Finish[")
            if start == -1: return None, None
            
            # Extract content: everything after 'Finish[' until the last ']'
            # This handles nested JSON brackets correctly
            content_start = start + len("Finish[")
            content = action_text[content_start:].rstrip("]")
            return "Finish", content
        
        # Fallback for Search
        match = re.search(r"(\w+)\[(.*?)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _parse_action_input(self, action_text: str) -> str:
        """Extracts input from Finish[...] specifically."""
        tool, content = self._parse_action(action_text)
        if tool == "Finish" and content:
            return content
        return ""
