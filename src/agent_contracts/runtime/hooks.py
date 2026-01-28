"""Runtime hooks for customization."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from agent_contracts.runtime.context import RequestContext, ExecutionResult


@runtime_checkable
class RuntimeHooks(Protocol):
    """Define customization hooks for runtime execution.

    Args:
        - None.
    Returns:
        - RuntimeHooks protocol implementation.
    """
    
    async def prepare_state(
        self, 
        state: dict[str, Any],
        request: RequestContext,
    ) -> dict[str, Any]:
        """Prepare state before graph execution.

        Args:
            - state: Initial state (may include restored session data).
            - request: Execution request context.
        Returns:
            - Modified state dictionary.
        """
        ...
    
    async def after_execution(
        self, 
        state: dict[str, Any],
        result: ExecutionResult,
    ) -> None:
        """Handle post-execution tasks.

        Args:
            - state: Final state after graph execution.
            - result: Execution result.
        Returns:
            - None.
        """
        ...


class DefaultHooks:
    """Provide a no-op RuntimeHooks implementation.

    Args:
        - None.
    Returns:
        - DefaultHooks instance.
    """
    
    async def prepare_state(
        self, 
        state: dict[str, Any],
        request: RequestContext,
    ) -> dict[str, Any]:
        """Return state unchanged.

        Args:
            - state: Initial state.
            - request: Execution request context.
        Returns:
            - Unmodified state dictionary.
        """
        return state
    
    async def after_execution(
        self, 
        state: dict[str, Any],
        result: ExecutionResult,
    ) -> None:
        """Perform no post-execution work.

        Args:
            - state: Final state after graph execution.
            - result: Execution result.
        Returns:
            - None.
        """
        pass
