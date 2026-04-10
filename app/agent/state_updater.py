import json
import logging
from typing import Dict, Any

from utils import get_chat_completion, parse_json_from_response

logger = logging.getLogger(__name__)

class StateUpdater:
    @staticmethod
    def update_states(agent_name: str, context: str, current_states: Dict[str, Any], thought: Dict[str, Any], speech_content: str) -> Dict[str, Any]:
        """
        Updates the agent's internal states based on the latest interaction.
        Returns the updated states.
        """
        prompt = f"""
        你是一个专门负责更新智能体内部状态的“状态更新器”。
        你需要基于角色当前的内部状态、最近的思考过程以及刚发生的交互上下文，更新角色的关系状态、信念置信度、情绪/疲劳度以及行为模式。

        【角色名称】
        {agent_name}

        【刚发生的交互上下文】
        {context}

        【角色的思考过程】
        {json.dumps(thought, ensure_ascii=False)}

        【角色最终的发言】
        {speech_content if speech_content else "（选择了倾听，未发言）"}

        【角色当前的状态】
        {json.dumps(current_states, ensure_ascii=False)}

        请分析以上信息，并输出更新后的状态。输出必须是一个合法的JSON对象，包含以下结构：
        {{
            "relations": "更新后的关系状态描述（如亲疏变化、新冲突等）",
            "beliefs": "更新后的议题信念及置信度变化说明",
            "temporal": "更新后的情绪、疲劳度和当前注意力焦点",
            "behavior_patterns": "提炼或更新的行为模式（如：遇到特定攻击时更倾向于反击）"
        }}
        """

        messages = [
            {"role": "system", "content": "你是一个严谨的心理与行为状态分析引擎，输出标准的JSON格式。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = get_chat_completion(messages)
            if response:
                content = response.choices[0].message.content
                import re
                json_match = re.search(r'(\{[\s\S]*\})', content)
                if json_match:
                    content = json_match.group(1)
                
                updated_states = parse_json_from_response(content)
                if updated_states and isinstance(updated_states, dict):
                    # Merge with original if any missing
                    for key in ["relations", "beliefs", "temporal", "behavior_patterns"]:
                        if key not in updated_states:
                            updated_states[key] = current_states.get(key, "")
                    return updated_states
        except Exception as e:
            logger.error(f"Failed to update states for {agent_name}: {e}")
            
        return current_states

