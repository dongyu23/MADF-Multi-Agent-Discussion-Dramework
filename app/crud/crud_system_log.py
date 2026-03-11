from app.schemas.system_log import SystemLogCreate
from app.db.client import fetch_one, fetch_all, db_execute_commit

def create_system_log(db, log: SystemLogCreate):
    rs = db_execute_commit(
        db,
        """
        INSERT INTO system_logs (forum_id, level, source, content)
        VALUES (?, ?, ?, ?)
        RETURNING *
        """,
        [log.forum_id, log.level, log.source, log.content]
    )
    return fetch_one(rs)

def get_system_logs(db, forum_id: int, limit: int = 100):
    rs = db.execute(
        "SELECT * FROM system_logs WHERE forum_id = ? ORDER BY timestamp ASC LIMIT ?",
        [forum_id, limit]
    )
    return fetch_all(rs)
