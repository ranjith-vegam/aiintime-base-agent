import uuid
import time
import logging
import json
from typing import Any, Optional, Dict, List
import redis.asyncio as redis

from google.adk.sessions.base_session_service import BaseSessionService, ListSessionsResponse, GetSessionConfig
from google.adk.sessions.session import Session, Event
from google.adk.sessions.state import State

logger = logging.getLogger(__name__)

class RedisSessionService(BaseSessionService):
    """
    A custom session service implementation that uses Redis with RedisJSON for storage.
    Inherits from BaseSessionService and provides full implementation of required methods.
    """

    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6382, 
        password: str = "Pass@123", 
        db: int = 0
    ):
        super().__init__()
        self._redis = redis.Redis(
            host=host, 
            port=port, 
            password=password, 
            db=db, 
            decode_responses=True
        )

    def _session_key(self, app_name: str, user_id: str, session_id: str) -> str:
        return f"session:{app_name}:{user_id}:{session_id}"

    def _app_state_key(self, app_name: str) -> str:
        return f"state:app:{app_name}"

    def _user_state_key(self, app_name: str, user_id: str) -> str:
        return f"state:user:{app_name}:{user_id}"

    async def _get_state(self, key: str) -> Dict[str, Any]:
        state = await self._redis.json().get(key, "$.state")
        return state[0] if state else {}

    async def _merge_state(self, app_name: str, user_id: str, session: Session) -> Session:
        """
        Merges app-level and user-level states into the session state.
        """
        # Merge app state
        app_state = await self._get_state(self._app_state_key(app_name))
        for key, value in app_state.items():
            session.state[State.APP_PREFIX + key] = value

        # Merge user state
        user_state = await self._get_state(self._user_state_key(app_name, user_id))
        for key, value in user_state.items():
            session.state[State.USER_PREFIX + key] = value
        
        return session

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Creates a new session and stores it in Redis."""
        session_id = (
            session_id.strip()
            if session_id and session_id.strip()
            else str(uuid.uuid4())
        )
        
        last_update_time = time.time()
        session_data = {
            "id": session_id,
            "app_name": app_name,
            "user_id": user_id,
            "state": state or {},
            "events": [],
            "last_update_time": last_update_time,
        }

        key = self._session_key(app_name, user_id, session_id)
        await self._redis.json().set(key, "$", session_data)

        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {},
            last_update_time=last_update_time,
        )

        return await self._merge_state(app_name, user_id, session)

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """Retrieves a session from Redis."""
        key = self._session_key(app_name, user_id, session_id)
        doc = await self._redis.json().get(key)

        if not doc:
            return None

        session = Session(
            app_name=doc["app_name"],
            user_id=doc["user_id"],
            id=doc["id"],
            state=doc["state"],
            last_update_time=doc["last_update_time"],
        )
        
        events = []
        for e_dict in doc.get("events", []):
            events.append(Event(**e_dict))
        
        session.events = events

        # Apply config filtering if provided
        if config:
            if config.num_recent_events:
                session.events = session.events[-config.num_recent_events:]
            if config.after_timestamp:
                session.events = [
                    e for e in session.events 
                    if e.timestamp >= config.after_timestamp
                ]

        return await self._merge_state(app_name, user_id, session)

    async def list_sessions(
        self, *, app_name: str, user_id: str
    ) -> ListSessionsResponse:
        """Lists all sessions for a given app and user from Redis."""
        pattern = self._session_key(app_name, user_id, "*")
        keys = await self._redis.keys(pattern)
        
        sessions_list = []
        for key in keys:
            doc = await self._redis.json().get(key)
            if doc:
                session = Session(
                    app_name=doc["app_name"],
                    user_id=doc["user_id"],
                    id=doc["id"],
                    state=doc["state"],
                    last_update_time=doc["last_update_time"],
                    events=[]
                )
                sessions_list.append(await self._merge_state(app_name, user_id, session))
            
        return ListSessionsResponse(sessions=sessions_list)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """Deletes a session from Redis."""
        key = self._session_key(app_name, user_id, session_id)
        await self._redis.delete(key)

    async def append_event(self, session: Session, event: Event) -> Event:
        """Appends an event to a session and updates state deltas in Redis."""
        app_name = session.app_name
        user_id = session.user_id
        session_id = session.id
        key = self._session_key(app_name, user_id, session_id)

        # Update local session object
        session.last_update_time = event.timestamp
        session.events.append(event)

        # Convert event to dict
        if hasattr(event, "model_dump"):
            event_dict = event.model_dump(mode='json')
        else:
            event_dict = event.dict() if hasattr(event, "dict") else event.__dict__

        # Handle state deltas
        if event.actions and event.actions.state_delta:
            for delta_key, value in event.actions.state_delta.items():
                if delta_key.startswith(State.APP_PREFIX):
                    clean_key = delta_key.removeprefix(State.APP_PREFIX)
                    app_key = self._app_state_key(app_name)
                    if not await self._redis.exists(app_key):
                        await self._redis.json().set(app_key, "$", {"state": {}})
                    await self._redis.json().set(app_key, f"$.state.{clean_key}", value)
                    session.state[delta_key] = value
                elif delta_key.startswith(State.USER_PREFIX):
                    clean_key = delta_key.removeprefix(State.USER_PREFIX)
                    user_state_key = self._user_state_key(app_name, user_id)
                    if not await self._redis.exists(user_state_key):
                        await self._redis.json().set(user_state_key, "$", {"state": {}})
                    await self._redis.json().set(user_state_key, f"$.state.{clean_key}", value)
                    session.state[delta_key] = value
                else:
                    # Regular session state update
                    await self._redis.json().set(key, f"$.state.{delta_key}", value)
                    session.state[delta_key] = value

        # Update session in Redis
        await self._redis.json().set(key, "$.last_update_time", event.timestamp)
        await self._redis.json().arrappend(key, "$.events", event_dict)

        return event

    async def close(self):
        await self._redis.close()