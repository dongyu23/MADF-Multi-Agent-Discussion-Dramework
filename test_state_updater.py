from app.agent.state_updater import StateUpdater
import json

context = "[张三] 发言: 我认为这个观点大错特错！"
thought = {"intent": "反击", "decision": "APPLY_SPEAK"}
speech_content = "我不认同你的说法，这是没有根据的。"
current_states = {
    "relations": "对张三保持礼貌",
    "beliefs": "坚守中立",
    "temporal": "情绪平稳",
    "behavior_patterns": "讲道理"
}

updated = StateUpdater.update_states("李四", context, current_states, thought, speech_content)
print(json.dumps(updated, ensure_ascii=False, indent=2))
