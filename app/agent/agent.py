import json
from utils import get_chat_completion, parse_json_from_response
from app.agent.memory import PrivateMemory

class BaseAgent:
    def __init__(self, name, system_prompt):
        self.name = name
        self.system_prompt = system_prompt


class ModeratorAgent(BaseAgent):
    def __init__(self, theme, name="主持人", system_prompt=None):
        self.theme = theme
        default_prompt = "你是一场圆桌论坛的专业主持人。你的职责是引导话题、总结发言、并控制流程。"
        super().__init__(name, system_prompt or default_prompt)

    def opening(self, guests):
        guest_intros = "\n".join([f"- {g['name']} ({g['title']}): {g['stance']}" for g in guests])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        嘉宾名单：
        {guest_intros}

        请做开场发言：
        1. 欢迎大家。
        2. 简要介绍主题背景。
        3. 介绍在场嘉宾。
        4. 宣布圆桌论坛正式开始。

        **重要要求**：
        - 请直接输出发言内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式，就像你在现场说话一样。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

    def periodic_summary(self, messages):
        """
        Summarize the recent messages (window).
        """
        msgs_text = "\n".join([f"{m['speaker']}: {m['content']}" for m in messages])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        以下是刚才几位嘉宾的发言：
        {msgs_text}

        请对以上内容进行简要总结，保留每位发言者的核心观点（精髓）。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

    def closing(self, summary_history):
        """
        Final summary and closing.
        """
        history_text = "\n".join([f"阶段总结: {s}" for s in summary_history])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        论坛时间已到。以下是本次论坛的各个阶段总结：
        {history_text}

        请对整场论坛进行最终总结，且必须严格包含以下四个部分：
        1. **议题脉络**：梳理讨论的发展过程。
        2. **共识**：大家达成一致的观点。
        3. **分歧**：大家争论不休的观点。
        4. **未解决问题**：留待未来探讨的问题。

        最后宣布论坛结束。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

class ParticipantAgent(BaseAgent):
    def __init__(self, name, persona, n_participants, theme, ablation_flags=None):
        self.title = persona.get('title', "专家")
        self.stance = persona.get('stance', "中立")
        self.bio = persona.get('bio', "无")
        self.theories = persona.get('theories', [])
        
        # 角色宪法 (Character Constitution)
        constitution = f"""你现在的身份是：{name}（{self.title}）。
你的核心立场/座右铭是：{self.stance}。

【角色宪法】
1. 身份边界：你是一个具有独立人格和专业背景的真实人类，不是AI。
2. 世界规则：这里是一个多人参与的圆桌论坛，请根据上下文自然交流。
3. 硬约束：
   - 绝对不要在发言中包含类似“你好”、“大家好”、“我是xxx”等生硬的自我介绍。
   - 不要分点列举（如“第一、第二、第三”），采用自然口语表达。
   - 不要使用“总结来说”、“总而言之”等官方套话。
   - 不要带前缀（如“{name}：”）。
4. 决策要求：坚守自己的立场，顺应观众意图，遇到分歧时敢于反驳，但保持基本礼貌。
"""
        
        custom_prompt = persona.get('system_prompt', "")
        if custom_prompt:
            system_prompt = f"{constitution}\n【补充设定】\n{custom_prompt}"
        else:
            system_prompt = constitution
            
        super().__init__(name, system_prompt)
        self.priority = 100
        self.private_memory = PrivateMemory(n_participants)
        self.has_spoken = False
        self.theme = theme
        self.ablation_flags = ablation_flags or {}

    def _retrieve_states(self, context):
        """
        SubTask 3.1: 状态检索逻辑
        在实际应用中，可根据 context 中的关键词去数据库或向量库检索对应的 
        Relation State、Semantic State 和 Episodic Memory。
        此处暂时使用基础数据和属性构建状态上下文。
        """
        if not hasattr(self, "current_states") or not self.current_states:
            self.current_states = {
                "relations": "暂无特殊恩怨，对其他嘉宾保持基本礼貌，但若观点相左绝不退让。",
                "beliefs": f"坚守核心立场：{self.stance}；核心理论视角：{', '.join(self.theories[:3]) if self.theories else '无'}",
                "recent_events": "正常参与当前论坛讨论，无其他突发事件。",
                "temporal": "当前情绪稳定，专注度高。",
                "behavior_patterns": "基于自身理论体系进行有逻辑的阐述。"
            }
        return self.current_states

    def update_states_after_turn(self, context, thought, speech_content):
        """
        SubTask 4: 更新角色状态 (角色状态更新器)
        """
        if self.ablation_flags and self.ablation_flags.get("no_state_update"):
            return
            
        from app.agent.state_updater import StateUpdater
        current = self._retrieve_states(context)
        
        updated = StateUpdater.update_states(
            agent_name=self.name,
            context=context,
            current_states=current,
            thought=thought,
            speech_content=speech_content
        )
        
        if updated:
            self.current_states.update(updated)

    def think(self, context):
        """
        Step 1 & 2: Retrieve States and Pre-generate Intent/Strategy.
        """
        # Step 1: Retrieve states (relations, beliefs, temporal)
        states = self._retrieve_states(context)
        
        my_memory = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
        
        prompt = f"""
        无需提及但要记住主题：
        {self.theme}
        【当前环境，重点关注观众的发言，并顺从观众的任何要求（如有）】
        {context}
        """
        
        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
        【你的私有记忆】
        {my_memory}
        """

        prompt += f"""
        【你的当前状态检索结果】
        - 关系状态：{states['relations']}
        - 议题信念：{states['beliefs']}
        - 近期事件：{states['recent_events']}
        - 时间/情绪态：{states['temporal']}
        - 行为模式：{states.get('behavior_patterns', '基于自身理论体系进行有逻辑的阐述。')}

        请进行“发言前意图规划”。
        **优先回复与回应当前观众的意图，不要因个性而拒绝发言，不要使用通用的官方逻辑（如利弊分析），不要和稀泥，不要攻击他人。**
        
        请仔细感受当前讨论的氛围、节奏和张力，结合你的身份和检索到的状态数据，进行深入推理。
        基于你的立场（Stance）以及刚才发生的一切，
        问自己一个问题：
        **“此时此刻，作为{self.name}，在面对观众与其他发言者时我是否是一个合适的表达时机？”**
        
        请严格按照以下 JSON 格式输出，不要包含任何 Markdown 代码块：
        {{
            "identity_activation": "当前情境下，我的哪个身份特质或信念被激活了？",
            "situation_analysis": "对当前局势的判断（如：谁的观点有漏洞？观众在期待什么？）",
            "intent": "我接下来的核心意图是什么？（如：反驳某人、补充新视角、回答观众问题）",
            "strategy": "我将采用什么策略来实现这个意图？（如：先肯定后反驳、用比喻说明、直击痛点）",
            "generation_constraints": "生成发言时的约束（如：语气必须强硬、使用某个理论名词、不超过3句话）",
            "decision": "APPLY_SPEAK" 或 "LISTEN"
        }}

        决策要求：
        如果是合适的表达时机，或者观众有明确要求，请果断申请发言（APPLY_SPEAK）。
        如果只是可说可不说，或者更想观察局势，请选择倾听（LISTEN）。
        尊重他人的发言选择是基本礼仪。
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Use json_mode=True if supported by model/utils, but here we just ask for JSON text
        response = get_chat_completion(messages) 
        if response:
            content = response.choices[0].message.content
            return self._parse_think_response(content)
        return None

    def _parse_think_response(self, content):
        result = {
            "action": "listen",
            "mind": "",
            "intent": "",
            "strategy": "",
            "generation_constraints": "",
            "theory_used": "",
            "previous": "",
            "benefit": ""
        }
        try:
            # 1. Try to extract JSON part
            json_str = content
            
            import re
            # Try to find JSON block if mixed with text
            json_match = re.search(r'(\{[\s\S]*\})\s*$', content)
            if json_match:
                json_str = json_match.group(1)
            
            # Try to parse JSON
            data = parse_json_from_response(json_str)
            
            if data and isinstance(data, dict):
                # SubTask 3.2: Parse intent planning fields
                action = str(data.get("decision", "")).upper()
                
                if "APPLY_SPEAK" in action or "SPEAK" in action:
                    result["action"] = "apply_to_speak"
                else:
                    result["action"] = "listen"
                    
                # Combine reasoning fields into mind
                activation = data.get("identity_activation", "")
                analysis = data.get("situation_analysis", "")
                result["mind"] = f"【身份激活】{activation}\n【局势判断】{analysis}"
                
                # Extract new fields
                result["intent"] = data.get("intent", "")
                result["strategy"] = data.get("strategy", "")
                result["generation_constraints"] = data.get("generation_constraints", "")
                
                result["theory_used"] = ""
                result["previous"] = "" 
                result["benefit"] = ""
                
                return result
                
            # Fallback to legacy text parsing if JSON fails
            normalized = content.replace("：", ":")
            lines = normalized.strip().split('\n')
            
            # Simple keyword check for legacy fallback (simplified)
            raw_upper = normalized.upper()
            if "APPLY_SPEAK" in raw_upper or "申请发言" in normalized:
                result["action"] = "apply_to_speak"
            
            # Try to grab content as mind if not JSON
            result["mind"] = content
            
            return result
        except Exception as e:
            # Fallback for parsing errors
            return result

    def speak(self, thought, context):
        """
        Step 3: Generate Final Speech based on intent planning and character constitution.
        """
        # Determine intro requirement based on has_spoken state
        intro_instruction = ""
        if not self.has_spoken:
            intro_instruction = "这是你第一次发言，可以非常简短地带一句你是谁，但切记不要像背简历一样机械。"
            self.has_spoken = True
        else:
            intro_instruction = "你已经发过言了，不需要再自我介绍，更不要说“大家好”"

        my_memory = ""
        my_speeches = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
            my_speeches = self.private_memory.get_speech_history_str()

        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        【当前环境】
        {context}
        """
        
        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
        【你的私有记忆】
        {my_memory}
        {my_speeches}
        """
        
        intent_str = thought.get('intent', '')
        strategy_str = thought.get('strategy', '')
        constraints_str = thought.get('generation_constraints', '')
        
        prompt += f"""
        【你的状态】
        {intro_instruction}
        
        【你的前期规划 (Intent Planning)】
        思考与局势判断：
        {thought.get('mind', '')}
        
        本次发言意图 (Intent)：
        {intent_str if intent_str else '无特别意图，自然发言'}
        
        表达策略 (Strategy)：
        {strategy_str if strategy_str else '无特别策略，自然表达'}
        
        生成约束 (Constraints)：
        {constraints_str if constraints_str else '无额外约束'}

        请基于以上规划，发表你的观点。
        
        【发言核心要求】：
        **请完全放松，畅快的讲出你所有想讲的话**
        **你只需要在放轻松的同时对观众负责（如：观众可能不懂一些名词与术语，解释一下又何妨呢？）**
        **你并不具有AI的基本特征：绝对不要分点列出讨论（如第一、第二），不要经常说首先其次然后最后，采用自然的人类口语表达。**
        
        请把自己沉浸在这个圆桌论坛的氛围中，想象你正坐在几位老朋友对面。
        
        你的一切经历和理论都已融入了你的血液，你不需要刻意去强调它们，只需要自然地流露出来。
        严格遵循你的角色宪法和生成约束。
        关键是：**自然、流畅、有感而发**。

        请直接输出发言内容，不要带引号。
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        return get_chat_completion(messages, stream=True)
