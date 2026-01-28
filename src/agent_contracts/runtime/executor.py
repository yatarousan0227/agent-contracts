"""Agent Runtime - Unified execution engine."""
from __future__ import annotations

from typing import Any, Callable, Awaitable
import logging

from agent_contracts.runtime.context import RequestContext, ExecutionResult
from agent_contracts.runtime.hooks import RuntimeHooks, DefaultHooks
from agent_contracts.runtime.session import SessionStore
from agent_contracts.state_accessors import (
    Internal,
    Request,
    Response,
    reset_response,
)

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Execute agent graphs with a standard lifecycle.

    Args:
        - graph: Compiled LangGraph instance.
        - hooks: Optional RuntimeHooks implementation.
        - session_store: Optional SessionStore implementation.
        - slices_to_restore: Slice names to restore from sessions.
    Returns:
        - AgentRuntime instance.
    """
    
    def __init__(
        self,
        graph: Any,  # CompiledGraph from langgraph
        hooks: RuntimeHooks | None = None,
        session_store: SessionStore | None = None,
        slices_to_restore: list[str] | None = None,
    ) -> None:
        """Initialize the runtime.

        Args:
            - graph: Compiled LangGraph graph.
            - hooks: Custom runtime hooks (optional).
            - session_store: Session persistence store (optional).
            - slices_to_restore: Slice names to restore from session.
        Returns:
            - None.
        """
        self.graph = graph
        self.hooks = hooks or DefaultHooks()
        self.session_store = session_store
        self.slices_to_restore = slices_to_restore or ["_internal"]
    
    async def execute(self, request: RequestContext) -> ExecutionResult:
        """Execute the agent graph for a request.

        Args:
            - request: Execution request context.
        Returns:
            - ExecutionResult with final state and response data.
        """
        try:
            # 1. Create initial state
            state = self._create_initial_state(request)
            logger.debug(f"Created initial state for session {request.session_id}")
            
            # 2. Restore session if resuming
            if request.resume_session and self.session_store:
                session_data = await self.session_store.load(request.session_id)
                if session_data:
                    state = self._merge_session(state, session_data)
                    logger.debug(f"Restored session {request.session_id}")
            
            # 3. Apply prepare_state hook
            state = await self.hooks.prepare_state(state, request)
            
            # 4. Execute graph
            logger.debug(f"Executing graph for action: {request.action}")
            result_state = await self.graph.ainvoke(state)
            
            # 5. Build result
            result = ExecutionResult.from_state(result_state)
            
            # 6. Apply after_execution hook
            await self.hooks.after_execution(result_state, result)
            
            logger.debug(f"Execution complete: {result.response_type}")
            return result
            
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            return ExecutionResult.error_result(str(e))
    
    def _create_initial_state(self, request: RequestContext) -> dict[str, Any]:
        """Create the initial state from a request context.

        Args:
            - request: Request context.
        Returns:
            - Initial state dictionary.
        """
        state: dict[str, Any] = {}
        
        # Build request slice
        state = Request.session_id.set(state, request.session_id)
        state = Request.action.set(state, request.action)
        state = Request.params.set(state, request.params)
        state = Request.message.set(state, request.message)
        state = Request.image.set(state, request.image)
        
        # Initialize response slice (empty)
        state = reset_response(state)
        
        # Initialize internal slice
        state = Internal.turn_count.set(state, 0)
        state = Internal.is_first_turn.set(state, True)
        state = Internal.active_mode.set(state, None)
        state = Internal.next_node.set(state, None)
        state = Internal.decision.set(state, None)
        state = Internal.error.set(state, None)
        
        return state
    
    def _merge_session(
        self, 
        state: dict[str, Any], 
        session_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge session data into the current state.

        Args:
            - state: Current state.
            - session_data: Session data to merge.
        Returns:
            - Merged state dictionary.
        """
        result = dict(state)
        
        for slice_name in self.slices_to_restore:
            if slice_name in session_data:
                current_slice = result.get(slice_name, {})
                if not isinstance(current_slice, dict):
                    current_slice = {}
                result[slice_name] = {**current_slice, **session_data[slice_name]}
        
        return result
