from __future__ import annotations
import re
import logging
import json
from typing import TYPE_CHECKING, Optional, Dict, List, Set, Any
import redis.asyncio as redis

from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.memory import _utils

if TYPE_CHECKING:
    from google.adk.events.event import Event
    from google.adk.sessions.session import Session

logger = logging.getLogger(__name__)

def _user_key(app_name: str, user_id: str):
    return f"memory:{app_name}:{user_id}"

def _extract_words_lower(text: str) -> Set[str]:
    """Extracts words from a string and converts them to lowercase."""
    return set([word.lower() for word in re.findall(r"[A-Za-z]+", text)])

class RedisMemoryService(BaseMemoryService):
    """
    A Redis-backed memory service implementation using RedisJSON.
    Uses keyword matching for search.
    """

    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6382, 
        password: str = "Pass@123", 
        db: int = 0
    ):
        self._redis = redis.Redis(
            host=host, 
            port=port, 
            password=password, 
            db=db, 
            decode_responses=True
        )

    async def add_session_to_memory(self, session: Session):
        """Adds a session to the memory service in Redis."""
        user_key = _user_key(session.app_name, session.user_id)
        
        # Filter events that have content and parts
        events_to_store = []
        for event in session.events:
            if event.content and event.content.parts:
                if hasattr(event, "model_dump"):
                    event_dict = event.model_dump(mode='json')
                else:
                    event_dict = event.dict() if hasattr(event, "dict") else event.__dict__
                events_to_store.append(event_dict)

        if not events_to_store:
            return

        # Using RedisJSON SET
        # We store it as a dict under the user_key, where session_id is the key
        # memory:{app_name}:{user_id} -> { "session_id": [event, event, ...] }
        
        # Check if key exists
        exists = await self._redis.exists(user_key)
        if not exists:
            await self._redis.json().set(user_key, "$", {})
        
        await self._redis.json().set(user_key, f"$.{session.id}", events_to_store)
        
        logger.info(f"Added session {session.id} to RedisMemoryService for user {session.user_id}")

    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        """Searches for sessions that match the query using keyword matching from Redis."""
        user_key = _user_key(app_name, user_id)
        
        # Retrieve all session events for this user
        session_data = await self._redis.json().get(user_key)
        if not session_data:
            return SearchMemoryResponse()

        words_in_query = _extract_words_lower(query)
        response = SearchMemoryResponse()

        for session_id, events in session_data.items():
            for event_dict in events:
                # Basic check for content and parts in the stored dict
                content = event_dict.get("content")
                if not content or not content.get("parts"):
                    continue
                
                texts = [part.get("text") for part in content["parts"] if part.get("text")]
                if not texts:
                    continue
                
                words_in_event = _extract_words_lower(" ".join(texts))
                if not words_in_event:
                    continue

                if any(query_word in words_in_event for query_word in words_in_query):
                    # We need to reconstruct MemoryEntry. 
                    # Assuming Event has author and timestamp (which are in event_dict)
                    # We might need to import Event/Content to reconstruct properly if needed, 
                    # but MemoryEntry takes content, author, timestamp.
                    
                    # MemoryEntry expects content as a Content object or dict depending on ADK version.
                    # Based on custom_memory_service.py, it seems it handles content as event.content.
                    
                    # Reconstruct Content object if possible, or pass dict if ADK allows.
                    # Let's try to match what CustomMemoryService does.
                    from google.adk.runners import types
                    
                    content_obj = types.Content(
                        role=content.get("role", "user"),
                        parts=[types.Part.from_text(text=p.get("text")) for p in content["parts"] if p.get("text")]
                    )

                    response.memories.append(
                        MemoryEntry(
                            content=content_obj,
                            author=event_dict.get("author"),
                            timestamp=_utils.format_timestamp(event_dict.get("timestamp")),
                        )
                    )

        return response

    async def close(self):
        await self._redis.close()