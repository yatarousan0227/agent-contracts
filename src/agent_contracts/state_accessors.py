"""State Accessors - Type-safe state access pattern.

Provides immutable, type-safe access to state fields following
the Redux selector pattern. All state modifications return new
state dictionaries rather than mutating in place.

Example:
    >>> state = {"_internal": {"turn_count": 5}}
    >>> count = Internal.turn_count.get(state)  # 5
    >>> new_state = Internal.turn_count.set(state, 10)
    >>> Internal.turn_count.get(new_state)  # 10
    >>> Internal.turn_count.get(state)  # 5 (original unchanged)
"""
from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from agent_contracts.runtime.hierarchy import Budgets, CallStackFrame, DecisionTraceItem

T = TypeVar("T")


class StateAccessor(Generic[T]):
    """Provide immutable access to a state field.

    Args:
        - slice_name: State slice name (e.g., "_internal", "request").
        - field_name: Field name within the slice.
        - default: Default value if the field is missing.
    Returns:
        - StateAccessor instance.
    """
    
    __slots__ = ("slice_name", "field_name", "default")
    
    def __init__(self, slice_name: str, field_name: str, default: T) -> None:
        """Initialize the accessor.

        Args:
            - slice_name: Name of the state slice.
            - field_name: Name of the field within the slice.
            - default: Default value to return if field is absent.
        Returns:
            - None.
        """
        self.slice_name = slice_name
        self.field_name = field_name
        self.default = default
    
    def get(self, state: dict[str, Any]) -> T:
        """Get the field value from state.

        Args:
            - state: State dictionary.
        Returns:
            - Field value or default if missing.
        """
        slice_data = state.get(self.slice_name)
        if not isinstance(slice_data, dict):
            return self.default
        return slice_data.get(self.field_name, self.default)
    
    def set(self, state: dict[str, Any], value: T) -> dict[str, Any]:
        """Set the field value and return a new state.

        Args:
            - state: Current state dictionary.
            - value: Value to set.
        Returns:
            - New state dictionary with the updated value.
        """
        current_slice = state.get(self.slice_name, {})
        if not isinstance(current_slice, dict):
            current_slice = {}
        new_slice = {**current_slice, self.field_name: value}
        return {**state, self.slice_name: new_slice}
    
    def update(self, state: dict[str, Any], func: Callable[[T], T]) -> dict[str, Any]:
        """Update the field using a transformation function.

        Args:
            - state: Current state dictionary.
            - func: Function that maps current value to new value.
        Returns:
            - New state dictionary with the updated value.
        """
        current_value = self.get(state)
        new_value = func(current_value)
        return self.set(state, new_value)
    
    def __repr__(self) -> str:
        return f"StateAccessor({self.slice_name!r}, {self.field_name!r}, default={self.default!r})"


# =============================================================================
# Standard Accessors: _internal slice
# =============================================================================

class Internal:
    """Expose accessors for _internal slice fields.

    Args:
        - None.
    Returns:
        - Internal accessor namespace.
    """
    
    # Core control fields
    turn_count: StateAccessor[int] = StateAccessor("_internal", "turn_count", 0)
    is_first_turn: StateAccessor[bool] = StateAccessor("_internal", "is_first_turn", True)
    active_mode: StateAccessor[str | None] = StateAccessor("_internal", "active_mode", None)
    next_node: StateAccessor[str | None] = StateAccessor("_internal", "next_node", None)
    decision: StateAccessor[str | None] = StateAccessor("_internal", "decision", None)
    error: StateAccessor[str | None] = StateAccessor("_internal", "error", None)
    call_stack: StateAccessor[list[CallStackFrame]] = StateAccessor("_internal", "call_stack", [])
    budgets: StateAccessor[Budgets | None] = StateAccessor("_internal", "budgets", None)
    decision_trace: StateAccessor[list[DecisionTraceItem]] = StateAccessor("_internal", "decision_trace", [])
    visited_subgraphs: StateAccessor[dict] = StateAccessor("_internal", "visited_subgraphs", {})
    step_count: StateAccessor[int] = StateAccessor("_internal", "step_count", 0)


# =============================================================================
# Standard Accessors: request slice
# =============================================================================

class Request:
    """Expose accessors for request slice fields.

    Args:
        - None.
    Returns:
        - Request accessor namespace.
    """
    
    session_id: StateAccessor[str] = StateAccessor("request", "session_id", "")
    action: StateAccessor[str] = StateAccessor("request", "action", "")
    params: StateAccessor[dict | None] = StateAccessor("request", "params", None)
    message: StateAccessor[str | None] = StateAccessor("request", "message", None)
    image: StateAccessor[str | None] = StateAccessor("request", "image", None)


# =============================================================================
# Standard Accessors: response slice
# =============================================================================

class Response:
    """Expose accessors for response slice fields.

    Args:
        - None.
    Returns:
        - Response accessor namespace.
    """
    
    response_type: StateAccessor[str | None] = StateAccessor("response", "response_type", None)
    response_data: StateAccessor[dict | None] = StateAccessor("response", "response_data", None)
    response_message: StateAccessor[str | None] = StateAccessor("response", "response_message", None)


# =============================================================================
# Convenience Functions
# =============================================================================

def reset_response(state: dict[str, Any]) -> dict[str, Any]:
    """Reset the response slice to empty values.

    Args:
        - state: Current state.
    Returns:
        - New state with response slice cleared.
    """
    state = Response.response_type.set(state, None)
    state = Response.response_data.set(state, None)
    state = Response.response_message.set(state, None)
    return state


def increment_turn(state: dict[str, Any]) -> dict[str, Any]:
    """Increment turn count and mark as not the first turn.

    Args:
        - state: Current state.
    Returns:
        - New state with updated turn counters.
    """
    state = Internal.turn_count.update(state, lambda x: x + 1)
    state = Internal.is_first_turn.set(state, False)
    return state


def set_error(state: dict[str, Any], error: str) -> dict[str, Any]:
    """Set the error message in state.

    Args:
        - state: Current state.
        - error: Error message.
    Returns:
        - New state with error set.
    """
    return Internal.error.set(state, error)


def clear_error(state: dict[str, Any]) -> dict[str, Any]:
    """Clear the error message in state.

    Args:
        - state: Current state.
    Returns:
        - New state with error cleared.
    """
    return Internal.error.set(state, None)
