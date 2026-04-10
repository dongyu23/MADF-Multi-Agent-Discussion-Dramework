import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from app.services.forum_scheduler import ForumScheduler
from app.agent.agent import ParticipantAgent, ModeratorAgent

class TestRobustnessTimeout(unittest.IsolatedAsyncioTestCase):
    async def test_agent_speak_timeout_handling(self):
        """
        Test that _agent_speak handles LLM timeout (returning None) gracefully.
        """
        scheduler = ForumScheduler()
        mock_db = MagicMock()
        forum_id = 1
        
        # Mock agent
        agent = ParticipantAgent("Test Agent", {"system_prompt": "test"}, 1, "test")
        agent.persona_id = 123
        
        # Mock agent.speak to return None (simulating timeout/failure after retries)
        # In actual implementation, agent.speak calls get_chat_completion which returns None
        # Then agent.speak generator loop probably yields nothing or raises if not handled.
        # But here we mock agent.speak to return None directly (not a generator)
        # Our updated code checks `if gen:`.
        agent.speak = MagicMock(return_value=None)
        
        # Mock dependencies
        with patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock) as mock_broadcast, \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_log', new_callable=AsyncMock) as mock_log, \
             patch('app.services.forum_scheduler.update_forum_participant') as mock_update_p:
            
            # Run _agent_speak
            # We must mock asyncio.to_thread because we mock agent.speak to be sync function
            # Or make agent.speak async if we don't mock to_thread?
            # It's easier to mock to_thread to return agent.speak()
            
            with patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
                await scheduler._agent_speak(forum_id, agent, {}, "context")
            
            # Verify:
            # It should handle None generator by logging warning and setting content to "(沉默)"
            # Then call create_message
            mock_create_msg.assert_called_once()
            args, kwargs = mock_create_msg.call_args
            # Args are (db, MessageCreate(...))
            # Check content inside MessageCreate
            msg_create = args[1]
            self.assertEqual(msg_create.content, "(沉默)")
            
    async def test_moderator_speak_timeout_handling(self):
        """
        Test that _moderator_speak handles LLM timeout gracefully.
        """
        scheduler = ForumScheduler()
        mock_db = MagicMock()
        forum_id = 1
        
        # Mock moderator
        mock_mod = MagicMock()
        mock_mod.name = "Moderator"
        
        # Mock opening to return None
        mock_mod.opening.return_value = None
        
        with patch('app.services.forum_scheduler.get_forum') as mock_get_forum, \
             patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_log', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.update_forum') as mock_update_f:
            
            mock_get_forum.return_value.moderator_id = 999
            
            with patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
                # Run
                await scheduler._moderator_speak(mock_db, forum_id, mock_mod, "opening", [])
            
            # In our implementation for moderator:
            # if gen is None: logger.warning...
            # content remains ""
            # if content: create_message...
            # So create_message should NOT be called
            mock_create_msg.assert_not_called()

    async def test_agent_speak_exception_handling(self):
        """
        Test that _agent_speak handles generator exception gracefully.
        """
        scheduler = ForumScheduler()
        mock_db = MagicMock()
        forum_id = 1
        agent = ParticipantAgent("Test Agent", {"system_prompt": "test"}, 1, "test")
        agent.persona_id = 123
        
        # Mock generator that raises
        def faulty_generator(*args):
            # Create a mock chunk
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = "Hello"
            yield chunk
            raise ValueError("Stream broken")
            
        agent.speak = MagicMock(return_value=faulty_generator())
        
        with patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_log', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.update_forum_participant'), \
             patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
             
            await scheduler._agent_speak(forum_id, agent, {}, "context")
            
            # It should catch the exception inside the loop and proceed with partial content
            mock_create_msg.assert_called_once()
            msg_create = mock_create_msg.call_args[0][1]
            self.assertEqual(msg_create.content, "Hello")

if __name__ == '__main__':
    unittest.main()
