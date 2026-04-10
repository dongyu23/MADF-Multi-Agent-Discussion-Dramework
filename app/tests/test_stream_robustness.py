import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import json
from app.services.forum_scheduler import ForumScheduler
from app.agent.agent import ModeratorAgent

class TestStreamRobustness(unittest.IsolatedAsyncioTestCase):
    async def test_moderator_stream_fields(self):
        """
        Verify that moderator streaming broadcasts include stream_id and moderator_id.
        """
        scheduler = ForumScheduler()
        
        # Mock DB and objects
        mock_db = MagicMock()
        mock_forum = MagicMock()
        mock_forum.id = 1
        mock_forum.moderator_id = 99
        mock_forum.summary_history = []
        
        # Mock get_forum to return our mock forum
        # We need to patch 'app.services.forum_scheduler.get_forum'
        
        # Mock ModeratorAgent to return a generator
        mock_moderator = MagicMock(spec=ModeratorAgent)
        mock_moderator.name = "TestHost"
        
        # Create a mock generator for streaming
        async def mock_gen():
            # Mock OpenAI chunk structure
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta.content = "Hello"
            yield chunk1
            
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta.content = " World"
            yield chunk2

        # We need to patch asyncio.to_thread to return our async generator wrapper?
        # No, asyncio.to_thread runs a sync function in a thread. 
        # If the sync function returns a generator, to_thread returns the generator.
        # But _moderator_speak iterates over it synchronously? 
        # Code: `for chunk in gen:` -> This implies gen is an iterator.
        
        # Let's mock the sync function to return a list (which is iterable) 
        # but the code expects objects with `choices[0].delta.content`.
        class MockChunk:
            def __init__(self, text):
                self.choices = [MagicMock()]
                self.choices[0].delta.content = text

        def mock_opening(guests):
            yield MockChunk("Hello")
            yield MockChunk(" World")
            
        # Patch dependencies
        with patch('app.services.forum_scheduler.get_forum', return_value=mock_forum), \
             patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.update_forum'), \
             patch('app.services.forum_scheduler.manager') as mock_manager, \
             patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)) as mock_to_thread:
            
            # Make broadcast awaitable
            mock_manager.broadcast = AsyncMock()
            
            # Setup moderator mock methods
            mock_moderator.opening = mock_opening
            
            # Run _moderator_speak
            # We assume asyncio.to_thread executes the function immediately for this test
            await scheduler._moderator_speak(1, mock_moderator, "opening", guests=[])
            
            # Verify broadcasts
            # Expected: 2 chunks + 1 final message + 1 system log (speech)
            # Check calls to manager.broadcast
            self.assertEqual(mock_manager.broadcast.call_count, 4)

            # Check that stream_id and moderator_id are present in chunks
            # First call: Chunk 1
            call_args_1 = mock_manager.broadcast.call_args_list[0]
            payload_1 = call_args_1[0][1]
            self.assertEqual(payload_1['type'], 'message_chunk')
            self.assertIn('stream_id', payload_1['data'])
            self.assertEqual(payload_1['data']['moderator_id'], 99)

            # Last call: System Log (speech)
            call_args_last = mock_manager.broadcast.call_args_list[-1]
            payload_last = call_args_last[0][1]
            self.assertEqual(payload_last['type'], 'system_log')
            self.assertEqual(payload_last['data']['level'], 'speech')

            # Second to last: Final Message
            call_args_msg = mock_manager.broadcast.call_args_list[-2]
            payload_msg = call_args_msg[0][1]
            self.assertEqual(payload_msg['type'], 'new_message')
            self.assertIn('stream_id', payload_msg['data'])
            self.assertEqual(payload_msg['data']['moderator_id'], 99)

if __name__ == '__main__':
    unittest.main()
