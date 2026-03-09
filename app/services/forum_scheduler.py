import asyncio
import logging
import time
import traceback
import uuid
from typing import Any
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
        from app.core.redis import get_redis
        from app.schemas.system_log import SystemLogCreate
        import json
        
        redis_client = get_redis()
        if redis_client:
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
                redis_client.rpush("system_logs_buffer", json.dumps(log_entry))
            except Exception as e:
                logger.error(f"Redis buffering failed: {e}")
                # Fallback to direct DB write if Redis fails? 
                # Maybe not, to avoid blocking. Just log error.
        else:
            # Fallback to direct DB persistence in thread if Redis not available
            if db: 
                from app.crud.crud_system_log import create_system_log
                
                def persist_log_sync():
                    local_db = None
                    try:
                        # Create a FRESH connection for this thread
                        local_db = db_manager.get_connection()
                        create_system_log(local_db, SystemLogCreate(
                            forum_id=forum_id,
                            level=level,
                            source=source,
                            content=message
                        ))
                    except Exception as e:
                        logger.error(f"Failed to persist system log (thread): {e}")
                    finally:
                        if local_db:
                            try:
                                local_db.close()
                            except:
                                pass

                # Schedule task
                asyncio.create_task(asyncio.to_thread(persist_log_sync))

    async def _flush_logs_to_db(self):
        """Batch flush logs from Redis buffer to DB"""
        from app.core.redis import get_redis
        from app.crud.crud_system_log import create_system_log
        from app.schemas.system_log import SystemLogCreate
        import json

        redis_client = get_redis()
        if not redis_client:
            return

        # Pop up to 100 logs
        logs = []
        try:
            # Pipeline for atomic pop? 
            # lpop with count supported in Redis 6.2+
            # Let's assume standard lpop loop or lrange+ltrim
            # Simple approach: lpop in loop
            for _ in range(100):
                item = redis_client.lpop("system_logs_buffer")
                if not item:
                    break
                logs.append(item)
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
                # Group by forum? Or just insert one by one?
                # create_system_log takes one item.
                # Batch insert would be better but requires new CRUD method.
                # Let's stick to loop for now, but use transaction.
                
                with local_db.transaction() as tx:
                    for log_json in logs:
                        try:
                            data = json.loads(log_json)
                            # Convert dict to schema
                            # Note: create_system_log expects db session, not tx wrapper usually?
                            # Our db client 'transaction' returns a tx object that has execute.
                            # We can manually execute INSERT for speed.
                            
                            # Using manual SQL for batch speed
                            # Assuming PG or SQLite
                            # Wait, db client abstracts this.
                            # Let's just call create_system_log with local_db (autocommit each? No, slow).
                            # If we use transaction context, can we pass tx to CRUD?
                            # CRUD expects 'db' which has .execute. 'tx' also has .execute.
                            # So yes, we can pass tx.
                            
                            log_obj = SystemLogCreate(
                                forum_id=data["forum_id"],
                                level=data["level"],
                                source=data["source"],
                                content=data["content"]
                            )
                            # We need to respect the original timestamp if possible, 
                            # but SystemLogCreate doesn't have timestamp field (it's auto-generated in DB schema).
                            # If we want accurate timestamp, we should add it to schema or modify SQL.
                            # For now, let's accept slight delay (DB time vs Redis time).
                            
                            create_system_log(tx, log_obj)
                        except Exception as inner_e:
                            logger.error(f"Failed to insert log item: {inner_e}")
            except Exception as e:
                logger.error(f"Batch log insert failed: {e}")
                # Ideally push back to Redis? Or DLQ?
                # For now, logs are lost if DB fails.
            finally:
                if local_db:
                    try:
                        local_db.close()
                    except:
                        pass

        await asyncio.to_thread(batch_insert)

    async def _run_forum_loop(self, forum_id: int, ablation_flags: dict = None):
        ablation_flags = ablation_flags or {}
        logger.info(f"Starting forum loop for {forum_id} with flags: {ablation_flags}")
        
        # Use new DB client
        db = db_manager.get_connection()
        try:
            # Persist the start log
            await self._broadcast_system_log(forum_id, f"论坛主循环启动... (配置: {ablation_flags})", db=db)
            
            forum = get_forum(db, forum_id)
            if not forum:
                logger.error(f"Forum {forum_id} not found.")
                return

            # Update status to Running
            update_forum(db, forum_id, status="running")
            
            # Initialize Agents
            participants_db = get_forum_participants(db, forum_id)
            participants = []
            n_participants = len(participants_db)
            
            for p_db in participants_db:
                persona = p_db.persona
                if not persona:
                    continue
                
                # Convert persona model to dict
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
                
                # Restore memory only if private memory is NOT ablated
                if not ablation_flags.get("no_private_memory"):
                    if hasattr(p_db, 'thoughts_history') and p_db.thoughts_history:
                        # thoughts_history is a JSON string from DB (via RowObject)
                        # Wait, CRUD handles JSON dumping, but fetching?
                        # RowObject just has the raw value. 
                        # In crud.__init__.py: get_forum_participants doesn't decode JSON.
                        # Wait, I missed decoding JSON in get_forum_participants!
                        # I should fix that in crud. Or handle it here.
                        # Let's check crud.
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

            moderator_db = forum.moderator
            if moderator_db:
                moderator = ModeratorAgent(
                    theme=forum.topic, 
                    name=moderator_db.name, 
                    system_prompt=moderator_db.system_prompt
                )
                await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 已就位", db=db)
            else:
                moderator = ModeratorAgent(theme=forum.topic)
                await self._broadcast_system_log(forum_id, "系统默认主持人已就位", db=db)
            
            # Speaker Queue for multi-speaker management
            speaker_queue = []
            # Track agents who have spoken in the current "batch" (until queue is cleared)
            batch_spoken_agents = set()
            
            # Opening
            await self._broadcast_system_message(forum_id, "论坛开始，主持人正在开场...")
            await self._broadcast_system_log(forum_id, "主持人正在进行开场白...", db=db)
            await self._moderator_speak(db, forum_id, moderator, "opening", participants)

            # Main Loop
            start_time = time.time()
            duration_sec = (forum.duration_minutes or 30) * 60
            end_time = start_time + duration_sec
            
            turn_count = 0
            fallback_speaker_idx = 0
            
            while True:
                # Reload forum to check for external stop signals or status changes
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
                    await self._moderator_speak(db, forum_id, moderator, "closing")
                    update_forum(db, forum_id, status="closed")
                    break

                # 2. Reconstruct Context (Shared Memory)
                messages = get_forum_messages(db, forum_id)
                shared_memory = SharedMemory(n_participants)
                if forum.summary_history:
                    # Parse summary history if string
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
                
                # Sync private memories with recent speeches (if allowed)
                if not ablation_flags.get("no_private_memory"):
                    for agent in participants:
                        agent.private_memory.speech_history = []
                        my_msgs = [m for m in messages if m.speaker_name == agent.name]
                        for m in my_msgs:
                            agent.private_memory.add_speech(m.content)

                # 3. Check Summary (If not ablated)
                msg_count = len(messages)
                N_WINDOW = 20 # Configurable default
                
                if not ablation_flags.get("no_summary"):
                    if msg_count > 0 and msg_count % N_WINDOW == 0:
                        last_msg = messages[-1]
                        if last_msg.speaker_name != moderator.name:
                            logger.info(f"Forum {forum_id} triggering summary (msg count {msg_count}).")
                            # Summarize the last N messages
                            msgs_to_summarize = messages[-N_WINDOW:]
                            await self._moderator_speak(db, forum_id, moderator, "periodic_summary", messages=msgs_to_summarize)

                # 4. Select Speaker (Queue Based)
                if ablation_flags.get("no_shared_memory"):
                    # Ablation: Minimal context (only last message)
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
                await self._broadcast_system_log(forum_id, "所有参与者正在思考中...", "info", db=db)
                logger.info(f"Forum {forum_id}: Agents start thinking...")
                
                async def agent_think(ag):
                    try:
                        # Log individual agent thinking
                        await self._broadcast_system_log(forum_id, f"嘉宾 [{ag.name}] 正在思考...", "thought", db=db)
                        
                        # Define callback for API error logging
                        def log_api_error(error_msg):
                            # This will be called from sync context inside to_thread, 
                            # so we can't await. But we can use run_coroutine_threadsafe if we had loop access.
                            # Or we just rely on the return value being None.
                            pass

                        # We can't easily pass async callback to sync function running in thread
                        # So we rely on standard logging in utils.py and maybe return error info?
                        # Let's modify agent.think to accept forum_id/callback? No, too invasive.
                        
                        # Better approach: Catch specific exceptions here if possible? 
                        # But to_thread wraps it.
                        
                        thought = await asyncio.to_thread(ag.think, context_str)
                        
                        # Log thought result to system log as structured JSON
                        if thought:
                            import json
                            # Create a clean version for display
                            display_thought = {
                                "decision": thought.get("action", "listen"),
                                "inner_monologue": thought.get("mind", "")
                            }
                            # Ensure JSON is compact or pretty? SystemLogConsole handles formatting.
                            # Just dump it.
                            await self._broadcast_system_log(forum_id, json.dumps(display_thought, ensure_ascii=False), "thought", f"Agent:{ag.name}", db=db)
                            
                        return ag, thought
                    except Exception as e:
                        logger.error(f"Agent {ag.name} think failed: {e}")
                        await self._broadcast_system_log(forum_id, f"嘉宾 [{ag.name}] 思考失败: {str(e)}", "error", db=db)
                        return ag, None

                # Execute thinking in parallel
                think_results = await asyncio.gather(*[agent_think(p) for p in participants])
                    
                logger.info(f"Forum {forum_id}: Agents finished thinking.")
                
                for agent, thought in think_results:
                    if thought:
                        thoughts_map[agent] = thought
                        if thought.get('action') == 'apply_to_speak':
                            # Add to queue if not already there AND hasn't spoken in current batch
                            if agent not in speaker_queue:
                                if agent in batch_spoken_agents and speaker_queue:
                                    pass
                                else:
                                    speaker_queue.append(agent)
                        
                        # Save thought to DB (Private History)
                        p_db = next((p for p in participants_db if p.persona.name == agent.name), None)
                        if p_db:
                             # Need to parse current history if string
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
                
                # Log current queue status for debugging
                queue_names = [a.name for a in speaker_queue]
                if queue_names:
                    await self._broadcast_system_log(forum_id, f"当前发言队列: {', '.join(queue_names)}", "info", db=db)
                else:
                    await self._broadcast_system_log(forum_id, "当前发言队列为空，准备进入随机指派模式...", "info", db=db)

                # Pop from queue
                if speaker_queue:
                    speaker = speaker_queue.pop(0)
                    batch_spoken_agents.add(speaker)
                    await self._broadcast_system_log(forum_id, f"队列调度: [{speaker.name}] 获得发言权", "info", db=db)
                elif participants:
                    # Fallback Mechanism
                    # 1. Try to pick someone who hasn't spoken in this batch first (if any)
                    remaining = [p for p in participants if p not in batch_spoken_agents]
                    if remaining:
                        speaker = remaining[0]
                        await self._broadcast_system_log(forum_id, f"随机指派(优先未发言): [{speaker.name}]", "info", db=db)
                    else:
                        # 2. If everyone spoke, clear batch and pick round-robin
                        batch_spoken_agents.clear()
                        speaker = participants[fallback_speaker_idx % len(participants)]
                        fallback_speaker_idx += 1
                        await self._broadcast_system_log(forum_id, f"随机指派(轮询): [{speaker.name}]", "info", db=db)
                    
                    batch_spoken_agents.add(speaker)
                
                # Check if queue is now empty
                if not speaker_queue:
                    if len(batch_spoken_agents) >= len(participants):
                        logger.info(f"Batch completed. Clearing batch history.")
                        batch_spoken_agents.clear()
                
                if speaker:
                    thought = thoughts_map.get(speaker)
                    if not thought:
                         thought = {
                            "focus": "系统指派", 
                            "attitude": "中立", 
                            "analysis": "无（思考过程解析失败或被系统强制发言）",
                            "action": "listen",
                            "previous": "无",
                            "mind": "无",
                            "benefit": "无"
                        }
                    
                    # Notify frontend immediately that this agent is preparing to speak
                    # This fills the gap between "Thinking Finished" and "Start Speaking" (TTFT)
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{speaker.name}] 正在准备发言...", "info", db=db)
                    
                    await self._agent_speak(db, forum_id, speaker, thought, context_str)
                
                turn_count += 1
                # Reduced delay to keep momentum - removed fixed sleep
                # await asyncio.sleep(0.5)

                # Periodic WAL checkpoint to prevent log file growth
                if turn_count % 10 == 0:
                    try:
                        # Checkpoint only if SQLite
                        if not db_manager.is_postgres and not db_manager.is_remote:
                             db.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    except Exception as e:
                        logger.warning(f"WAL checkpoint failed: {e}")
                
                # Flush system logs from Redis buffer
                await self._flush_logs_to_db()

        except Exception as e:
            logger.error(f"Forum loop crashed: {e}")
            logger.error(traceback.format_exc())
            # Broadcast the error to the system log so user can see it
            try:
                await self._broadcast_system_log(forum_id, f"论坛异常终止: {str(e)}", "error")
            except:
                pass
        finally:
            db.close()

    async def _moderator_speak(self, db: Any, forum_id: int, moderator: ModeratorAgent, action: str, guests=None, messages=None):
        content = ""
        gen = None
        stream_id = str(uuid.uuid4())
        
        forum = get_forum(db, forum_id)
        moderator_id = forum.moderator_id
        
        await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 正在构思...", "info", db=db)
        try:
            if action == "opening":
                guest_list = [{"name": g.name, "title": g.title, "stance": g.stance} for g in guests]
                gen = await asyncio.to_thread(moderator.opening, guest_list)
            elif action == "closing":
                forum = get_forum(db, forum_id)
                # Parse summary history
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
                    # Mark that streaming started
                    await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 开始发言...", "info", db=db)
                    
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
            logger.error(traceback.format_exc())
            await self._broadcast_system_log(forum_id, f"主持人发言生成失败: {str(e)}", "error")
            return

        if content:
            msg = create_message(db, MessageCreate(
                forum_id=forum_id,
                moderator_id=moderator_id,
                speaker_name=moderator.name,
                content=content,
                turn_count=0 
            ))
            
            if action == "periodic_summary":
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
            
            # Log full speech
            await self._broadcast_system_log(forum_id, content, "speech", moderator.name, db=db)

    async def _agent_speak(self, db: Any, forum_id: int, agent: ParticipantAgent, thought: dict, context: str):
        content = ""
        stream_id = str(uuid.uuid4())
        participants = get_forum_participants(db, forum_id)
        p_db = next((p for p in participants if p.persona.name == agent.name), None)
        persona_id = p_db.persona_id if p_db else None

        await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 正在构思中...", "info", db=db)
        try:
            gen = await asyncio.to_thread(agent.speak, thought, context)
            if gen:
                try:
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 开始发言...", "info", db=db)
                    
                    # Track Time to First Token (TTFT)
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
                            
                            # Send thought with the first chunk
                            send_thought = None
                            if not thought_sent and thought_content:
                                send_thought = thought_content
                                thought_sent = True
                                
                            await self._broadcast_chunk(forum_id, agent.name, token, persona_id, None, stream_id, thought=send_thought)
                except Exception as e:
                    logger.error(f"Error consuming agent generator: {e}")
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 发言中断: {str(e)}", "error", db=db)
            else:
                logger.warning(f"Agent {agent.name} speak returned None")
                content = "(沉默)"
                await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 放弃发言 (API无响应或返回空)", "warning", db=db)
        except Exception as e:
            logger.error(f"Agent {agent.name} speak failed: {e}")
            await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 发言生成失败: {str(e)}", "error", db=db)
            return

        if content:
            # Try to extract thought from inner_monologue if it was passed or stored
            # Actually, the 'thought' dict is available in _agent_speak scope
            # Let's save the thought content (inner_monologue) to the message
            
            thought_content = None
            if thought:
                thought_content = thought.get('mind')
                
            msg = create_message(db, MessageCreate(
                forum_id=forum_id,
                persona_id=persona_id,
                speaker_name=agent.name,
                content=content,
                thought=thought_content,
                turn_count=0
            ))
            
            await self._broadcast_message(forum_id, agent.name, content, persona_id, None, stream_id, msg.id, thought=thought_content)
            
            # Log full speech to system log
            await self._broadcast_system_log(forum_id, content, "speech", agent.name, db=db)

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
