from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Annotated, Any

from app.db.session import get_db
from app.schemas import (
    ForumCreate, 
    ForumResponse, 
    MessageCreate, 
    MessageResponse,
    SystemLogResponse,
    ForumStartRequest
)
from app.crud import get_forum, get_forum_messages
from app.crud.crud_system_log import get_system_logs
from app.api.deps import get_current_user
from app.core.websockets import manager
from app.services.forum_service import ForumService
from app.db.client import fetch_all

router = APIRouter()

def get_forum_service(db: Any = Depends(get_db)) -> ForumService:
    return ForumService(db)

@router.post("/", response_model=ForumResponse)
def create_new_forum(
    forum: ForumCreate, 
    current_user: Annotated[Any, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service)
):
    return service.create_new_forum(forum, current_user.id)

@router.get("/", response_model=List[ForumResponse])
def list_forums(
    db: Any = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Annotated[Any, Depends(get_current_user)] = None
):
    rs = db.execute(
        "SELECT * FROM forums WHERE creator_id = ? ORDER BY start_time DESC LIMIT ? OFFSET ?",
        [current_user.id, limit, skip]
    )
    # Note: forums list usually doesn't need full participant details, 
    # but the ForumResponse model might require it. 
    # If ForumResponse has `participants` field, we need to populate it.
    # Let's check ForumResponse in schemas. Assuming it allows optional or we need to fetch.
    # For now, let's just return the forums. If schema validation fails, we need to fetch participants.
    # The `get_forum` in CRUD does fetch participants.
    # A simple SELECT * won't include participants relation.
    # I should update `fetch_all` to support relations? No.
    # I should probably iterate and fetch participants or adjust the query.
    # Or simply let Pydantic handle missing fields if they are optional.
    # But usually API returns full objects.
    # Let's iterate and populate.
    
    forums = fetch_all(rs)
    for forum in forums:
        # Populate participants
        from app.crud import get_forum_participants
        participants = get_forum_participants(db, forum.id)
        setattr(forum, "participants", participants)
        
        # Populate moderator
        if forum.moderator_id:
             # Fetch moderator
             rs_mod = db.execute("SELECT * FROM moderators WHERE id = ?", [forum.moderator_id])
             from app.db.client import fetch_one
             mod = fetch_one(rs_mod)
             setattr(forum, "moderator", mod)
        else:
             setattr(forum, "moderator", None)
             
    return forums

@router.get("/{forum_id}", response_model=ForumResponse)
def read_forum(forum_id: int, db: Any = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if db_forum is None:
        raise HTTPException(status_code=404, detail="Forum not found")
    return db_forum

@router.delete("/{forum_id}")
async def delete_forum_endpoint(
    forum_id: int,
    current_user: Annotated[Any, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service)
):
    is_admin = current_user.role == 'admin'
    success = await service.delete_forum(forum_id, current_user.id, is_admin)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete forum")
    return {"message": "Forum deleted successfully"}

@router.post("/{forum_id}/start")
async def start_forum_endpoint(
    forum_id: int,
    request: ForumStartRequest = None,
    current_user: Annotated[Any, Depends(get_current_user)] = None,
    service: ForumService = Depends(get_forum_service)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    is_admin = current_user.role == 'admin'
    ablation_flags = request.ablation_flags if request else None
    return await service.start_forum(forum_id, current_user.id, is_admin, ablation_flags)

@router.post("/{forum_id}/messages", response_model=MessageResponse)
async def post_message(
    forum_id: int, 
    message: MessageCreate, 
    service: ForumService = Depends(get_forum_service)
):
    return await service.post_message(forum_id, message)

@router.get("/{forum_id}/messages", response_model=List[MessageResponse])
def get_messages(forum_id: int, db: Any = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if not db_forum:
        raise HTTPException(status_code=404, detail="Forum not found")
    return get_forum_messages(db, forum_id=forum_id)

@router.get("/{forum_id}/logs", response_model=List[SystemLogResponse])
def get_forum_logs(forum_id: int, db: Any = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if not db_forum:
        raise HTTPException(status_code=404, detail="Forum not found")
    return get_system_logs(db, forum_id=forum_id)

@router.websocket("/{forum_id}/ws")
async def websocket_endpoint(websocket: WebSocket, forum_id: int):
    print(f"WS: Received connection request for forum {forum_id}")
    try:
        await manager.connect(websocket, forum_id)
        print(f"WS: Connection accepted for forum {forum_id}")
    except Exception as e:
        print(f"WS: Connection failed for forum {forum_id}: {e}")
        return

    try:
        while True:
            # Keep the connection alive
            try:
                data = await websocket.receive_text()
                # Handle ping/pong if needed, or just ignore incoming messages
                if data == "ping":
                    await websocket.send_text("pong")
            except RuntimeError as e:
                # WebSocket disconnect usually raises RuntimeError in starlette
                print(f"WS: RuntimeError in loop for forum {forum_id}: {e}")
                break
            except WebSocketDisconnect:
                print(f"WS: Client disconnected for forum {forum_id}")
                break
    except Exception as e:
        # Log unexpected errors
        print(f"WS: Unexpected error for forum {forum_id}: {e}")
    finally:
        print(f"WS: Cleaning up connection for forum {forum_id}")
        await manager.disconnect(websocket, forum_id)
