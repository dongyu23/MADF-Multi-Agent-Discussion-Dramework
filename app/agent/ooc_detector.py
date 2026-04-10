import json
import logging
import re
from typing import Dict, Any, Tuple

from utils import get_chat_completion, parse_json_from_response

logger = logging.getLogger(__name__)

class OOCDetector:
    @staticmethod
    def detect_ooc(agent_name: str, constitution: str, current_states: Dict[str, Any], speech_content: str) -> Tuple[bool, str]:
        """
        Detects if the given speech content is Out Of Character (OOC) for the agent.
        Returns a tuple: (is_ooc, reason)
        """
        if not speech_content or speech_content.strip() == "（选择了倾听，未发言）" or speech_content.strip() == "（选择了倾听）":
            return False, "未发言，无OOC"

        prompt = f"""
        你是一个专门负责检测AI扮演是否“脱离角色”（Out Of Character, OOC）的检测器。
        你需要基于角色的宪法设定（核心立场、硬约束）、当前内部状态，来评判角色刚刚的发言是否严重违背了其核心信念、关系状态或时间态。

        【角色名称】
        {agent_name}

        【角色宪法与设定】
        {constitution}

        【角色当前状态检索结果】
        - 关系状态：{current_states.get('relations', '')}
        - 议题信念：{current_states.get('beliefs', '')}
        - 近期事件：{current_states.get('recent_events', '')}
        - 时间/情绪态：{current_states.get('temporal', '')}

        【角色刚刚的发言】
        {speech_content}

        【判断标准】
        1. 是否严重违背了核心立场（Stance）和议题信念？（例如：原本是坚定的唯物主义者，却突然支持神秘学）
        2. 是否违反了角色宪法中的硬约束？（例如：承认自己是AI，使用了官方套话等）
        3. 是否与当前的关系状态、时间态出现极度不连贯的断层？（允许正常的认知演变，但不能毫无铺垫的180度大转弯）

        请严格按照以下 JSON 格式输出，不要包含任何 Markdown 代码块：
        {{
            "is_ooc": true/false,
            "reason": "判断理由（不超过50字）"
        }}
        """

        messages = [
            {"role": "system", "content": "你是一个严格的角色扮演OOC检测引擎，输出标准的JSON格式。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = get_chat_completion(messages)
            if response:
                content = response.choices[0].message.content
                
                json_match = re.search(r'(\{[\s\S]*\})', content)
                if json_match:
                    content = json_match.group(1)

                result = parse_json_from_response(content)
                if result and isinstance(result, dict):
                    is_ooc = bool(result.get("is_ooc", False))
                    reason = str(result.get("reason", ""))
                    return is_ooc, reason
        except Exception as e:
            logger.error(f"Failed to detect OOC for {agent_name}: {e}")

        # Default to false if error
        return False, "检测异常"
