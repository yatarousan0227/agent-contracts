"""Session storage abstraction."""
from __future__ import annotations

from typing import Protocol, runtime_checkable, Any
import time


@runtime_checkable
class SessionStore(Protocol):
    """Define the session persistence interface.

    Args:
        - None.
    Returns:
        - SessionStore protocol implementation.
    """
    
    async def load(self, session_id: str) -> dict[str, Any] | None:
        """Load session data for a session ID.

        Args:
            - session_id: Session identifier.
        Returns:
            - Session data dict or None if not found.
        """
        ...
    
    async def save(
        self, 
        session_id: str, 
        data: dict[str, Any], 
        ttl_seconds: int = 3600,
    ) -> None:
        """Save session data with a TTL.

        Args:
            - session_id: Session identifier.
            - data: Session data to persist.
            - ttl_seconds: Time-to-live in seconds.
        Returns:
            - None.
        """
        ...
    
    async def delete(self, session_id: str) -> None:
        """Delete session data by session ID.

        Args:
            - session_id: Session identifier.
        Returns:
            - None.
        """
        ...


class InMemorySessionStore:
    """Provide an in-memory session store for development.

    Args:
        - None.
    Returns:
        - InMemorySessionStore instance.
    """
    
    def __init__(self) -> None:
        """Initialize the in-memory store.

        Args:
            - None.
        Returns:
            - None.
        """
        self._store: dict[str, tuple[dict[str, Any], float]] = {}
    
    async def load(self, session_id: str) -> dict[str, Any] | None:
        """Load session data if present and not expired.

        Args:
            - session_id: Session identifier.
        Returns:
            - Session data dict or None if missing/expired.
        """
        entry = self._store.get(session_id)
        if entry is None:
            return None
        
        data, expires_at = entry
        if time.time() > expires_at:
            # Expired - clean up and return None
            del self._store[session_id]
            return None
        
        return data
    
    async def save(
        self, 
        session_id: str, 
        data: dict[str, Any], 
        ttl_seconds: int = 3600,
    ) -> None:
        """Save session data with TTL.

        Args:
            - session_id: Session identifier.
            - data: Session data to persist.
            - ttl_seconds: Time-to-live in seconds.
        Returns:
            - None.
        """
        expires_at = time.time() + ttl_seconds
        self._store[session_id] = (data, expires_at)
    
    async def delete(self, session_id: str) -> None:
        """Delete session data.

        Args:
            - session_id: Session identifier.
        Returns:
            - None.
        """
        self._store.pop(session_id, None)
    
    def clear(self) -> None:
        """Clear all sessions.

        Args:
            - None.
        Returns:
            - None.
        """
        self._store.clear()
    
    def __len__(self) -> int:
        """Return the number of stored sessions.

        Args:
            - None.
        Returns:
            - Session count.
        """
        return len(self._store)
