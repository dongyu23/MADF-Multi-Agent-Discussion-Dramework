import asyncio
import logging
import time
import traceback
import uuid
from typing import Any, Optional
from app.db.session import db_manager
from app.crud import (
    get_forum, 
    get_forum_participants, 
    create_message, 
    get_forum_messages,
    update_forum,
    update_forum_participant,
    get_persona
)
from app.schemas import MessageCreate
from app.agent.agent import ModeratorAgent, ParticipantAgent
from app.agent.memory import SharedMemory
from app.core.websockets import manager
# Removed SQLAlchemy models import as we use schemas/dicts
from app.core.time_utils import get_beijing_time, get_beijing_time_iso
from app.core.async_utils import async_generator_wrapper
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ForumScheduler:
    def __init__(self):
        self.running_tasks = {}

    async def start_forum(self, forum_id: int, ablation_flags: dict = None):
        if forum_id in self.running_tasks:
            logger.warning(f"Forum {forum_id} is already running.")
            return

        task = asyncio.create_task(self._run_forum_loop(forum_id, ablation_flags))
        self.running_tasks[forum_id] = task
        
        # Remove task from dict when done
        task.add_done_callback(lambda t: self.running_tasks.pop(forum_id, None))

    async def stop_forum(self, forum_id: int):
        if forum_id in self.running_tasks:
            self.running_tasks[forum_id].cancel()
            try:
                await self.running_tasks[forum_id]
            except asyncio.CancelledError:
                pass
            logger.info(f"Forum {forum_id} stopped.")

    @contextmanager
    def _get_db(self):
        """Helper to get a fresh DB connection and ensure it closes"""
        db = db_manager.get_connection()
        try:
            yield db
        finally:
            try:
                db.close()
            except:
                pass

    async def _broadcast_system_log(self, forum_id: int, message: str, level: str = "info", source: str = "System", db: Any = None):
        """Broadcast system log to frontend for 'terminal-like' view and optionally persist"""
        
        # 1. Broadcast immediately (async) so frontend gets it ASAP
        try:
            await manager.broadcast(forum_id, {
                "type": "system_log",
                "data": {
                    "timestamp": get_beijing_time_iso(),
                    "level": level,
                    "content": message,
                    "source": source
                }
            })
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")

        # 2. Buffer to Redis for later batch persistence
        # Use cache_service wrapper instead of direct redis_client
        from app.core.cache import cache_service
        from app.schemas.system_log import SystemLogCreate
        import json
        
        try:
            log_entry = {
                "forum_id": forum_id,
                "level": level,
                "source": source,
                "content": message,
                "timestamp": get_beijing_time_iso()
            }
            # Push to a dedicated list for this forum (or global queue)
            # Using global queue for simpler batch worker
            if not cache_service.push_message("system_logs_buffer", log_entry):
                 # Fallback to direct DB write if Redis fails (handled below)
                 raise Exception("Redis push failed")
                 
        except Exception as e:
            logger.error(f"Redis buffering failed: {e}")
            # Fallback to direct DB persistence in thread if Redis not available
            # Use passed db or create new one
            from app.crud.crud_system_log import create_system_log
            
            def persist_log_sync():
                local_db = None
                should_close = False
                try:
                    if db:
                        local_db = db
                    else:
                        local_db = db_manager.get_connection()
                        should_close = True
                        
                    create_system_log(local_db, SystemLogCreate(
                        forum_id=forum_id,
                        level=level,
                        source=source,
                        content=message
                    ))
                except Exception as inner_e:
                    logger.error(f"Failed to persist system log (thread): {inner_e}")
                finally:
                    if should_close and local_db:
                        try:
                            local_db.close()
                        except:
                            pass

            # Schedule task
            asyncio.create_task(asyncio.to_thread(persist_log_sync))

    async def _flush_logs_to_db(self):
        """Batch flush logs from Redis buffer to DB"""
        from app.core.cache import cache_service
        from app.crud.crud_system_log import create_system_log
        from app.schemas.system_log import SystemLogCreate
        import json

        # Use cache_service wrapper
        # Pop up to 100 logs
        try:
            # cache_service.pop_messages returns a list of dicts (already json loaded)
            logs = cache_service.pop_messages("system_logs_buffer", count=100)
        except Exception as e:
            logger.error(f"Redis pop failed: {e}")
            return

        if not logs:
            return

        # Batch insert to DB
        # Since we use sync DB client, we should do this in a thread
        def batch_insert():
            local_db = None
            try:
                local_db = db_manager.get_connection()
                
                with local_db.transaction() as tx:
                    for data in logs:
                        try:
                            # data is already a dict
                            log_obj = SystemLogCreate(
                                forum_id=data["forum_id"],
                                level=data["level"],
                                source=data["source"],
                                content=data["content"]
                            )
                            create_system_log(tx, log_obj)
                        except Exception as inner_e:
                            logger.error(f"Failed to insert log item: {inner_e}")
                    
                    # FORCE COMMIT BATCH
                    if hasattr(tx, 'commit'):
                        tx.commit()
                    elif hasattr(local_db, 'commit'):
                        local_db.commit()
                        
            except Exception as e:
                logger.error(f"Batch log insert failed: {e}")
            finally:
                if local_db:
                    try:
                        local_db.close()
                    except:
                        pass

        await asyncio.to_thread(batch_insert)

    async def _mock_stream_generator(self, content: str):
        class MockChunk:
            def __init__(self, text):
                self.choices = [type('obj', (object,), {'delta': type('obj', (object,), {'content': text})})]

        # Simulate streaming
        chunk_size = 5
        for i in range(0, len(content), chunk_size):
            chunk_text = content[i:i+chunk_size]
            yield MockChunk(chunk_text)
            await asyncio.sleep(0.05)

    async def _run_forum_loop(self, forum_id: int, ablation_flags: dict = None):
        ablation_flags = ablation_flags or {}
        logger.info(f"Starting forum loop for {forum_id} with flags: {ablation_flags}")
        
        # NOTE: We DO NOT keep a long-lived DB connection here anymore to avoid locks.
        # We open/close DB connections for each operation or logical block.
        
        try:
            # Persist the start log
            await self._broadcast_system_log(forum_id, f"论坛主循环启动... (配置: {ablation_flags})")
            await self._flush_logs_to_db() # FLUSH 1
            
            # Initial setup
            with self._get_db() as db:
                forum = get_forum(db, forum_id)
                if not forum:
                    logger.error(f"Forum {forum_id} not found.")
                    return

                # Update status to Running
                update_forum(db, forum_id, status="running")
                
                # Initialize Agents
                participants_db = get_forum_participants(db, forum_id)
                
                moderator_db = forum.moderator
            
            # Setup Agents (in memory)
            participants = []
            n_participants = len(participants_db)
            
            for p_db in participants_db:
                persona = p_db.persona
                if not persona:
                    continue
                
                persona_dict = {
                    "name": persona.name,
                    "title": persona.title,
                    "bio": persona.bio,
                    "theories": persona.theories,
                    "stance": persona.stance,
                    "system_prompt": persona.system_prompt
                }
                
                agent = ParticipantAgent(
                    name=persona.name,
                    persona=persona_dict,
                    n_participants=n_participants,
                    theme=forum.topic,
                    ablation_flags=ablation_flags
                )
                
                # Restore memory
                if not ablation_flags.get("no_private_memory"):
                    if hasattr(p_db, 'thoughts_history') and p_db.thoughts_history:
                        import json
                        history = []
                        if isinstance(p_db.thoughts_history, str):
                            try:
                                history = json.loads(p_db.thoughts_history)
                            except:
                                history = []
                        elif isinstance(p_db.thoughts_history, list):
                            history = p_db.thoughts_history
                            
                        for t in history:
                            agent.private_memory.add_thought(t)
                
                participants.append(agent)

            if moderator_db:
                moderator = ModeratorAgent(
                    theme=forum.topic, 
                    name=moderator_db.name, 
                    system_prompt=moderator_db.system_prompt
                )
                await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 已就位")
            else:
                moderator = ModeratorAgent(theme=forum.topic)
                await self._broadcast_system_log(forum_id, "系统默认主持人已就位")
            
            # Speaker Queue for multi-speaker management
            speaker_queue = []
            # Track agents who have spoken in the current "batch" (until queue is cleared)
            batch_spoken_agents = set()
            
            # Opening
            await self._broadcast_system_message(forum_id, "论坛开始，主持人正在开场...")
            await self._broadcast_system_log(forum_id, "主持人正在进行开场白...")
            await self._flush_logs_to_db() # FLUSH 2
            
            await self._moderator_speak(forum_id, moderator, "opening", guests=participants, ablation_flags=ablation_flags)
            
            await self._broadcast_system_log(forum_id, "DEBUG: 主持人开场结束，进入主循环", "info")
            await self._flush_logs_to_db() # FLUSH 3
            
            # Main Loop
            start_time = time.time()
            duration_sec = (forum.duration_minutes or 30) * 60
            end_time = start_time + duration_sec
            
            turn_count = 0
            fallback_speaker_idx = 0
            
            while True:
                # Reload forum status
                with self._get_db() as db:
                    forum = get_forum(db, forum_id)
                
                if not forum:
                    logger.error(f"Forum {forum_id} disappeared during loop.")
                    break
                    
                if forum.status != "running":
                    logger.info(f"Forum {forum_id} status changed to {forum.status}, stopping loop.")
                    break
                
                current_time = time.time()
                
                # 1. Check Time -> Closing
                if current_time > end_time:
                    logger.info(f"Forum {forum_id} time up. Closing.")
                    await self._moderator_speak(forum_id, moderator, "closing", ablation_flags=ablation_flags)
                    with self._get_db() as db:
                        update_forum(db, forum_id, status="closed")
                    break

                # 2. Reconstruct Context (Shared Memory)
                # We need messages.
                with self._get_db() as db:
                    messages = get_forum_messages(db, forum_id)
                
                shared_memory = SharedMemory(n_participants)
                if forum.summary_history:
                    summaries = forum.summary_history
                    if isinstance(summaries, str):
                        import json
                        try:
                            summaries = json.loads(summaries)
                        except:
                            summaries = []
                    
                    for s in summaries:
                        shared_memory.add_summary(s)
                        
                for m in messages:
                    shared_memory.add_message(m.speaker_name, m.content)
                
                # Sync private memories
                if not ablation_flags.get("no_private_memory"):
                    for agent in participants:
                        agent.private_memory.speech_history = []
                        my_msgs = [m for m in messages if m.speaker_name == agent.name]
                        for m in my_msgs:
                            agent.private_memory.add_speech(m.content)

                # 3. Check Summary
                msg_count = len(messages)
                N_WINDOW = 20
                
                if not ablation_flags.get("no_summary"):
                    if msg_count > 0 and msg_count % N_WINDOW == 0:
                        last_msg = messages[-1]
                        if last_msg.speaker_name != moderator.name:
                            logger.info(f"Forum {forum_id} triggering summary (msg count {msg_count}).")
                            msgs_to_summarize = messages[-N_WINDOW:]
                            await self._moderator_speak(forum_id, moderator, "periodic_summary", messages=msgs_to_summarize, ablation_flags=ablation_flags)

                # 4. Select Speaker
                if ablation_flags.get("no_shared_memory"):
                    if messages:
                        last_m = messages[-1]
                        context_str = f"【最新发言】\n{last_m.speaker_name}: {last_m.content}"
                    else:
                        context_str = "(暂无发言)"
                else:
                    context_str = shared_memory.get_context_str()

                speaker = None
                thoughts_map = {}
                
                # Everyone thinks
                await self._broadcast_system_log(forum_id, "所有参与者正在思考中...", "info")
                logger.info(f"Forum {forum_id}: Agents start thinking...")
                
                async def agent_think(ag):
                    try:
                        await self._broadcast_system_log(forum_id, f"嘉宾 [{ag.name}] 正在思考...", "thought")
                        
                        if ablation_flags.get("mock_llm"):
                            await asyncio.sleep(1)
                            # Simple mock thought
                            thought = {
                                "action": "apply_to_speak", 
                                "mind": f"Mock thought from {ag.name}. I should speak."
                            }
                        else:
                            thought = await asyncio.to_thread(ag.think, context_str)
                        
                        if thought:
                            import json
                            display_thought = {
                                "decision": thought.get("action", "listen"),
                                "inner_monologue": thought.get("mind", "")
                            }
                            await self._broadcast_system_log(forum_id, json.dumps(display_thought, ensure_ascii=False), "thought", f"Agent:{ag.name}")
                            
                        return ag, thought
                    except Exception as e:
                        logger.error(f"Agent {ag.name} think failed: {e}")
                        await self._broadcast_system_log(forum_id, f"嘉宾 [{ag.name}] 思考失败: {str(e)}", "error")
                        return ag, None

                # Execute thinking in parallel - NO DB LOCK HELD HERE
                think_results = await asyncio.gather(*[agent_think(p) for p in participants])
                    
                logger.info(f"Forum {forum_id}: Agents finished thinking.")
                
                # Process thoughts (need DB to save thoughts)
                with self._get_db() as db:
                    # Refresh participants info to get latest thought history?
                    # Or just assume we have IDs correct. We have IDs from init.
                    # But we need to fetch current history to append.
                    # This is inefficient (read-modify-write).
                    # Better: update_forum_participant should append or we read first.
                    # Let's read first.
                    participants_db_fresh = get_forum_participants(db, forum_id)
                    
                    for agent, thought in think_results:
                        if thought:
                            thoughts_map[agent] = thought
                            if thought.get('action') == 'apply_to_speak':
                                if agent not in speaker_queue:
                                    if agent in batch_spoken_agents and speaker_queue:
                                        pass
                                    else:
                                        speaker_queue.append(agent)
                            
                            p_db = next((p for p in participants_db_fresh if p.persona.name == agent.name), None)
                            if p_db:
                                 current_hist = []
                                 if hasattr(p_db, 'thoughts_history'):
                                     if isinstance(p_db.thoughts_history, str):
                                         import json
                                         try:
                                             current_hist = json.loads(p_db.thoughts_history)
                                         except:
                                             pass
                                     elif isinstance(p_db.thoughts_history, list):
                                         current_hist = p_db.thoughts_history
                                         
                                 new_thoughts = current_hist + [thought]
                                 update_forum_participant(db, forum_id, p_db.persona_id, thoughts_history=new_thoughts)

                # --- Queue Logic Refinement ---
                queue_names = [a.name for a in speaker_queue]
                if queue_names:
                    await self._broadcast_system_log(forum_id, f"当前发言队列: {', '.join(queue_names)}", "info")
                else:
                    await self._broadcast_system_log(forum_id, "当前发言队列为空，准备进入随机指派模式...", "info")

                if speaker_queue:
                    speaker = speaker_queue.pop(0)
                    batch_spoken_agents.add(speaker)
                    await self._broadcast_system_log(forum_id, f"队列调度: [{speaker.name}] 获得发言权", "info")
                elif participants:
                    remaining = [p for p in participants if p not in batch_spoken_agents]
                    if remaining:
                        speaker = remaining[0]
                        await self._broadcast_system_log(forum_id, f"随机指派(优先未发言): [{speaker.name}]", "info")
                    else:
                        batch_spoken_agents.clear()
                        speaker = participants[fallback_speaker_idx % len(participants)]
                        fallback_speaker_idx += 1
                        await self._broadcast_system_log(forum_id, f"随机指派(轮询): [{speaker.name}]", "info")
                    
                    batch_spoken_agents.add(speaker)
                
                if not speaker_queue:
                    if len(batch_spoken_agents) >= len(participants):
                        batch_spoken_agents.clear()
                
                if speaker:
                    thought = thoughts_map.get(speaker)
                    if not thought:
                         thought = {
                            "focus": "系统指派", 
                            "attitude": "中立", 
                            "analysis": "无",
                            "action": "listen",
                            "previous": "无",
                            "mind": "无",
                            "benefit": "无"
                        }
                    
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{speaker.name}] 正在准备发言...", "info")
                    
                    await self._agent_speak(forum_id, speaker, thought, context_str, ablation_flags=ablation_flags)
                
                turn_count += 1
                
                # Periodic WAL checkpoint
                if turn_count % 10 == 0:
                    with self._get_db() as db:
                        try:
                            if not db_manager.is_postgres and not db_manager.is_remote:
                                 db.execute("PRAGMA wal_checkpoint(PASSIVE)")
                        except Exception as e:
                            logger.warning(f"WAL checkpoint failed: {e}")
                
                # Flush system logs
                await self._flush_logs_to_db()

        except Exception as e:
            logger.error(f"Forum loop crashed: {e}")
            logger.error(traceback.format_exc())
            try:
                await self._broadcast_system_log(forum_id, f"论坛异常终止: {str(e)}", "error")
            except:
                pass

    async def _moderator_speak(self, forum_id: int, moderator: ModeratorAgent, action: str, guests=None, messages=None, ablation_flags: dict = None):
        content = ""
        gen = None
        stream_id = str(uuid.uuid4())
        ablation_flags = ablation_flags or {}
        
        # Read data
        with self._get_db() as db:
            forum = get_forum(db, forum_id)
            moderator_id = forum.moderator_id
        
        await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 正在构思...", "info")
        try:
            if ablation_flags.get("mock_llm"):
                await asyncio.sleep(1)
                gen = self._mock_stream_generator(f"Mock moderator speech for {action} on topic {forum.topic}...")
            elif action == "opening":
                guest_list = [{"name": g.name, "title": g.title, "stance": g.stance} for g in guests]
                gen = await asyncio.to_thread(moderator.opening, guest_list)
            elif action == "closing":
                # Need summaries
                summaries = forum.summary_history or []
                if isinstance(summaries, str):
                    import json
                    try:
                        summaries = json.loads(summaries)
                    except:
                        summaries = []
                        
                gen = await asyncio.to_thread(moderator.closing, summaries)
            elif action == "periodic_summary":
                msgs_text = [{"speaker": m.speaker_name, "content": m.content} for m in messages[-20:]]
                gen = await asyncio.to_thread(moderator.periodic_summary, msgs_text)

            if gen:
                try:
                    await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 开始发言...", "info")
                    
                    async for chunk in async_generator_wrapper(gen):
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            token = chunk.choices[0].delta.content
                            content += token
                            await self._broadcast_chunk(forum_id, moderator.name, token, None, moderator_id, stream_id)
                except Exception as e:
                     logger.error(f"Error consuming generator: {e}")
            else:
                logger.warning("Moderator speak returned None generator")
                
        except Exception as e:
            logger.error(f"Moderator speak failed: {e}")
            await self._broadcast_system_log(forum_id, f"主持人发言生成失败: {str(e)}", "error")
            return

        if content:
            with self._get_db() as db:
                msg = create_message(db, MessageCreate(
                    forum_id=forum_id,
                    moderator_id=moderator_id,
                    speaker_name=moderator.name,
                    content=content,
                    turn_count=0 
                ))
                
                if action == "periodic_summary":
                    # Refresh forum
                    forum = get_forum(db, forum_id)
                    current = forum.summary_history or []
                    if isinstance(current, str):
                        import json
                        try:
                            current = json.loads(current)
                        except:
                            current = []
                    new_history = current + [content]
                    update_forum(db, forum_id, summary_history=new_history)

            await self._broadcast_message(forum_id, moderator.name, content, None, moderator_id, stream_id, msg.id)
            await self._broadcast_system_log(forum_id, content, "speech", moderator.name)

    async def _agent_speak(self, forum_id: int, agent: ParticipantAgent, thought: dict, context: str, ablation_flags: dict = None):
        content = ""
        stream_id = str(uuid.uuid4())
        ablation_flags = ablation_flags or {}
        
        with self._get_db() as db:
            participants = get_forum_participants(db, forum_id)
            p_db = next((p for p in participants if p.persona.name == agent.name), None)
            persona_id = p_db.persona_id if p_db else None

        await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 正在构思中...", "info")
        try:
            if ablation_flags.get("mock_llm"):
                await asyncio.sleep(1)
                gen = self._mock_stream_generator(f"Mock speech from {agent.name}. My thought was: {thought.get('mind')}")
            else:
                gen = await asyncio.to_thread(agent.speak, thought, context)
            
            if gen:
                try:
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 开始发言...", "info")
                    
                    first_token = True
                    start_speak_time = time.time()
                    thought_sent = False
                    thought_content = thought.get('mind') if thought else None
                    
                    async for chunk in async_generator_wrapper(gen):
                        if first_token:
                            ttft = time.time() - start_speak_time
                            logger.info(f"Agent {agent.name} TTFT: {ttft:.2f}s")
                            first_token = False
                            
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            token = chunk.choices[0].delta.content
                            content += token
                            
                            send_thought = None
                            if not thought_sent and thought_content:
                                send_thought = thought_content
                                thought_sent = True
                                
                            await self._broadcast_chunk(forum_id, agent.name, token, persona_id, None, stream_id, thought=send_thought)
                except Exception as e:
                    logger.error(f"Error consuming agent generator: {e}")
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 发言中断: {str(e)}", "error")
            else:
                logger.warning(f"Agent {agent.name} speak returned None")
                content = "(沉默)"
                await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 放弃发言 (API无响应或返回空)", "warning")
        except Exception as e:
            logger.error(f"Agent {agent.name} speak failed: {e}")
            await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 发言生成失败: {str(e)}", "error")
            return

        if content:
            thought_content = None
            if thought:
                thought_content = thought.get('mind')
                
            with self._get_db() as db:
                msg = create_message(db, MessageCreate(
                    forum_id=forum_id,
                    persona_id=persona_id,
                    speaker_name=agent.name,
                    content=content,
                    thought=thought_content,
                    turn_count=0
                ))
            
            await self._broadcast_message(forum_id, agent.name, content, persona_id, None, stream_id, msg.id, thought=thought_content)
            await self._broadcast_system_log(forum_id, content, "speech", agent.name)

    async def _broadcast_chunk(self, forum_id: int, speaker: str, chunk: str, persona_id: int = None, moderator_id: int = None, stream_id: str = None, thought: str = None):
        if not chunk:
            return
            
        data = {
            "speaker_name": speaker,
            "content": chunk,
            "persona_id": persona_id,
            "moderator_id": moderator_id,
            "stream_id": stream_id,
            "timestamp": get_beijing_time_iso()
        }
        
        if thought:
            data["thought"] = thought
            
        await manager.broadcast(forum_id, {
            "type": "message_chunk",
            "data": data
        })

    async def _broadcast_message(self, forum_id: int, speaker: str, content: str, persona_id: int = None, moderator_id: int = None, stream_id: str = None, msg_id: int = None, thought: str = None):
        await manager.broadcast(forum_id, {
            "type": "new_message",
            "data": {
                "id": msg_id,
                "forum_id": forum_id,
                "speaker_name": speaker,
                "content": content,
                "persona_id": persona_id,
                "moderator_id": moderator_id,
                "stream_id": stream_id,
                "thought": thought,
                "timestamp": get_beijing_time_iso()
            }
        })

    async def _broadcast_system_message(self, forum_id: int, content: str):
        await manager.broadcast(forum_id, {
            "type": "system",
            "content": content
        })

scheduler = ForumScheduler()
