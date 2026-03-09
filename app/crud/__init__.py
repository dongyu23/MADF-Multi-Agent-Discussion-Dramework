from app.schemas import UserCreate, PersonaCreate, PersonaUpdate, ForumCreate, MessageCreate
from app.core.hashing import Hasher
from app.db.client import fetch_one, fetch_all, RowObject, db_transaction
import json
import logging
from typing import List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def get_user_by_username(db, username: str):
    rs = db.execute("SELECT * FROM users WHERE username = ?", [username])
    return fetch_one(rs)

def create_user(db: Any, user: UserCreate):
    # Bcrypt (used by passlib) has a 72-byte limit for passwords.
    # We truncate it here to avoid ValueError.
    # We use 71 bytes to be safe.
    password_bytes = user.password.encode('utf-8')
    if len(password_bytes) > 71:
        password_bytes = password_bytes[:71]
    safe_password = password_bytes.decode('utf-8', 'ignore')
    
    try:
        pwd_hash = Hasher.get_password_hash(safe_password)
        created_at = datetime.now()
        # In PG we rely on RETURNING * which is supported by execute wrapper now
        rs = db.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?) RETURNING *",
            [user.username, pwd_hash, user.role, created_at]
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise

def create_persona(db, persona: PersonaCreate, owner_id: int):
    try:
        theories_json = json.dumps(persona.theories)
        created_at = datetime.now()
        rs = db.execute(
            """
            INSERT INTO personas (owner_id, name, title, bio, theories, stance, system_prompt, is_public, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                owner_id,
                persona.name,
                persona.title,
                persona.bio,
                theories_json,
                persona.stance,
                persona.system_prompt,
                persona.is_public,
                created_at
            ]
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise

def get_persona(db, persona_id: int):
    rs = db.execute("SELECT * FROM personas WHERE id = ?", [persona_id])
    return fetch_one(rs)

def update_persona(db, persona_id: int, updates: PersonaUpdate):
    try:
        # Build dynamic update query
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return get_persona(db, persona_id)

        set_clauses = []
        values = []
        for key, value in update_data.items():
            set_clauses.append(f"{key} = ?")
            if key == "theories":
                values.append(json.dumps(value))
            else:
                values.append(value)
        
        values.append(persona_id)
        query = f"UPDATE personas SET {', '.join(set_clauses)} WHERE id = ? RETURNING *"
        
        rs = db.execute(query, values)
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        raise

def delete_persona(db, persona_id: int):
    try:
        rs = db.execute("DELETE FROM personas WHERE id = ?", [persona_id])
        return rs.rows_affected > 0 if hasattr(rs, 'rows_affected') else True
    except Exception as e:
        logger.error(f"Error deleting persona: {e}")
        raise

def create_forum(db, forum: ForumCreate, creator_id: int):
    try:
        with db_transaction(db) as tx:
            start_time = datetime.now()
            rs = tx.execute(
                """
                INSERT INTO forums (topic, creator_id, moderator_id, status, duration_minutes, start_time, summary_history)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                [
                    forum.topic,
                    creator_id,
                    forum.moderator_id,
                    "pending",
                    forum.duration_minutes,
                    start_time,
                    "[]"
                ]
            )
            db_forum = fetch_one(rs)

            tx.execute("DELETE FROM messages WHERE forum_id = ?", [db_forum.id])
            tx.execute("DELETE FROM forum_participants WHERE forum_id = ?", [db_forum.id])
            tx.execute("DELETE FROM system_logs WHERE forum_id = ?", [db_forum.id])

            if forum.participant_ids:
                unique_pids = list(dict.fromkeys(int(pid) for pid in forum.participant_ids))
                values = []
                placeholders = []
                for pid in unique_pids:
                    placeholders.append("(?, ?, ?)")
                    values.extend([db_forum.id, pid, "[]"])

                if values:
                    # SQLite 'INSERT OR IGNORE' -> PG 'INSERT ... ON CONFLICT DO NOTHING'
                    # But since we support both, we need to detect or use standard SQL if possible.
                    # 'INSERT OR IGNORE' is SQLite specific. PG uses 'ON CONFLICT DO NOTHING'.
                    # Let's check db type or use a try-catch for duplicates?
                    # Or use a compatible syntax? No standard syntax for this.
                    # We can use the db object to check type if we exposed it.
                    # Assuming PostgresClient handles this replacement? No, we only replaced ? with %s.
                    # Let's change to standard INSERT and catch error, or assume PG client will replace it?
                    # No, replace logic is simple string replace.
                    # Let's use ON CONFLICT if PG, but we are in shared code.
                    # Workaround: Use a helper or just try-except loop for now?
                    # Or simply change query based on db type? We don't have db type here easily.
                    # Actually, we can use "INSERT INTO ... VALUES ... ON CONFLICT DO NOTHING" for PG.
                    # But SQLite requires "ON CONFLICT" clause support (v3.24+).
                    # "INSERT OR IGNORE" is safer for SQLite.
                    # Let's try to detect via a hack or just use "INSERT INTO" and ignore errors?
                    # Better: "INSERT INTO ... VALUES ... ON CONFLICT (forum_id, persona_id) DO NOTHING"
                    # This works in SQLite 3.24+ and Postgres 9.5+.
                    # Let's use this modern syntax.
                    query = f"INSERT INTO forum_participants (forum_id, persona_id, thoughts_history) VALUES {', '.join(placeholders)} ON CONFLICT (forum_id, persona_id) DO NOTHING"
                    tx.execute(query, values)

        return get_forum(db, db_forum.id)
    except Exception as e:
        logger.error(f"Error creating forum: {e}")
        raise

def delete_forum(db, forum_id: int):
    try:
        with db_transaction(db) as tx:
            tx.execute("DELETE FROM messages WHERE forum_id = ?", [forum_id])
            tx.execute("DELETE FROM forum_participants WHERE forum_id = ?", [forum_id])
            tx.execute("DELETE FROM system_logs WHERE forum_id = ?", [forum_id])
            rs = tx.execute("DELETE FROM forums WHERE id = ?", [forum_id])
            return rs.rows_affected > 0 if hasattr(rs, 'rows_affected') else True
    except Exception as e:
        logger.error(f"Error deleting forum: {e}")
        raise

def get_forum(db, forum_id: int):
    # Fetch forum
    rs = db.execute("SELECT * FROM forums WHERE id = ?", [forum_id])
    forum = fetch_one(rs)
    if not forum:
        return None
        
    # Fetch participants with persona details
    # We can join here or do separate query. Join is better.
    # But for simplicity and matching old structure, separate queries are fine too.
    # Let's do a separate call to populate participants if needed, but get_forum usually needs them.
    # The Pydantic model `ForumResponse` expects `participants`.
    
    participants = get_forum_participants(db, forum_id)
    
    # We need to attach participants to the forum object for Pydantic to serialize it
    # RowObject is a wrapper, so we can set attributes.
    # But RowObject uses __dict__.
    setattr(forum, "participants", participants)
    
    # Fetch moderator if exists
    if forum.moderator_id:
        mod_rs = db.execute("SELECT * FROM moderators WHERE id = ?", [forum.moderator_id])
        setattr(forum, "moderator", fetch_one(mod_rs))
    else:
        setattr(forum, "moderator", None)
        
    return forum

def update_forum(db, forum_id: int, summary_history: list = None, status: str = None):
    try:
        set_clauses = []
        values = []
        
        if summary_history is not None:
            set_clauses.append("summary_history = ?")
            values.append(json.dumps(summary_history))
            
        if status is not None:
            set_clauses.append("status = ?")
            values.append(status)
            
        if not set_clauses:
            return get_forum(db, forum_id)
            
        values.append(forum_id)
        query = f"UPDATE forums SET {', '.join(set_clauses)} WHERE id = ? RETURNING *"
        rs = db.execute(query, values)
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error updating forum: {e}")
        raise

def get_forum_participants(db, forum_id: int):
    # Join with personas to get details
    query = """
    SELECT fp.*, p.name as persona_name, p.title as persona_title, p.bio as persona_bio, 
           p.theories as persona_theories, p.stance as persona_stance, 
           p.system_prompt as persona_system_prompt, p.owner_id as persona_owner_id,
           p.created_at as persona_created_at
    FROM forum_participants fp
    JOIN personas p ON fp.persona_id = p.id
    WHERE fp.forum_id = ?
    """
    rs = db.execute(query, [forum_id])
    rows = fetch_all(rs)
    
    results = []
    for row in rows:
        # Construct nested persona object
        persona_data = {
            "id": row.persona_id,
            "name": row.persona_name,
            "title": row.persona_title,
            "bio": row.persona_bio,
            "theories": row.persona_theories,
            "stance": row.persona_stance,
            "system_prompt": row.persona_system_prompt,
            "owner_id": row.persona_owner_id,
            "created_at": row.persona_created_at
        }
        # row is a RowObject, so we can set 'persona' attribute
        setattr(row, "persona", RowObject(persona_data))
        results.append(row)
    return results

def update_forum_participant(db, forum_id: int, persona_id: int, thoughts_history: list = None):
    try:
        if thoughts_history is None:
            return None
            
        query = "UPDATE forum_participants SET thoughts_history = ? WHERE forum_id = ? AND persona_id = ? RETURNING *"
        rs = db.execute(query, [json.dumps(thoughts_history), forum_id, persona_id])
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error updating participant: {e}")
        raise

def create_message(db, message: MessageCreate):
    try:
        timestamp = datetime.now()
        rs = db.execute(
            """
            INSERT INTO messages (forum_id, persona_id, moderator_id, speaker_name, content, turn_count, thought, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                message.forum_id,
                message.persona_id,
                message.moderator_id,
                message.speaker_name,
                message.content,
                message.turn_count,
                message.thought,
                timestamp
            ]
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise

def get_forum_messages(db, forum_id: int):
    rs = db.execute("SELECT * FROM messages WHERE forum_id = ? ORDER BY timestamp ASC", [forum_id])
    return fetch_all(rs)
