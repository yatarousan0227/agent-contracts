"""BaseActionRouter - Action-based routing.

Parses action parameters and routes to appropriate subgraphs.
Uses rule-based decisions, no LLM.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent_contracts.utils.logging import get_logger

logger = get_logger("agent_contracts.router")


class BaseActionRouter(ABC):
    """Define action-based routing without LLMs.

    Args:
        - None.
    Returns:
        - BaseActionRouter instance.
    """
    
    @abstractmethod
    def route(self, action: str, state: dict[str, Any] | None = None) -> str:
        """Determine the routing target based on action.

        Args:
            - action: Request action string.
            - state: Optional agent state.
        Returns:
            - Routing target node name.
        Raises:
            - ValueError: For unknown actions.
        """
        ...
    
    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run routing as a LangGraph node.

        Args:
            - state: Agent state.
        Returns:
            - State updates including _internal.next_node.
        """
        request = state.get("request", {})
        action = request.get("action", "")
        
        try:
            next_node = self.route(action, state)
            logger.info(f"Routed: action={action} -> {next_node}")
            # LangGraph reducer merges this into existing _internal slice
            return {"_internal": {"next_node": next_node}}
        except ValueError as e:
            logger.error(f"Routing failed: {e}")
            # LangGraph reducer merges these updates into existing slices
            return {
                "_internal": {"next_node": None, "error": str(e)},
                "response": {
                    "response_type": "error",
                    "response_data": {"code": "UNKNOWN_ACTION", "message": str(e)},
                },
            }
