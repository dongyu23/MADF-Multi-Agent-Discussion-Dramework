import pytest
from app.agent.ooc_detector import OOCDetector
from unittest.mock import patch

def test_ooc_detector_detect_ooc():
    constitution = "你是一个坚定的唯物主义者，绝不相信神秘学。不要使用官方套话。"
    current_states = {
        "relations": "和张三关系一般",
        "beliefs": "坚守唯物主义",
        "temporal": "情绪平稳"
    }

    # Test normal speech
    normal_speech = "我认为这背后一定有科学的解释，我们不能迷信。"
    with patch("app.agent.ooc_detector.get_chat_completion") as mock_get_chat_completion:
        mock_get_chat_completion.return_value.choices = [
            type('obj', (object,), {'message': type('obj', (object,), {'content': '{"is_ooc": false, "reason": "符合唯物主义立场"}'})})
        ]
        is_ooc, reason = OOCDetector.detect_ooc("TestAgent", constitution, current_states, normal_speech)
        assert is_ooc is False
        assert "唯物主义" in reason

    # Test OOC speech
    ooc_speech = "我昨晚遇到了一个幽灵，现在我确信世界上有鬼。"
    with patch("app.agent.ooc_detector.get_chat_completion") as mock_get_chat_completion:
        mock_get_chat_completion.return_value.choices = [
            type('obj', (object,), {'message': type('obj', (object,), {'content': '{"is_ooc": true, "reason": "严重违背唯物主义信念"}'})})
        ]
        is_ooc, reason = OOCDetector.detect_ooc("TestAgent", constitution, current_states, ooc_speech)
        assert is_ooc is True
        assert "唯背" in reason or "唯物" in reason
