"""State Operations - Higher-level state manipulation helpers.

Provides immutable helper functions for common state operations like
merging sessions, resetting flags, and creating initial state.

All functions follow immutable patterns - they return new state dictionaries
rather than mutating the input.
"""
from __future__ import annotations

from typing import Any

from agent_contracts.state_accessors import (
    StateAccessor,
    Internal,
    Request,
    Response,
    reset_response,
)


def ensure_slices(state: dict[str, Any], slice_names: list[str]) -> dict[str, Any]:
    """Ensure specified slices exist in the state.

    Args:
        - state: Current state dictionary.
        - slice_names: Slice names to ensure exist.
    Returns:
        - New state with all specified slices present.
    """
    result = dict(state)
    for name in slice_names:
        if name not in result or not isinstance(result.get(name), dict):
            result[name] = {}
    return result


def merge_session(
    state: dict[str, Any],
    session_data: dict[str, Any],
    slices: list[str] | None = None,
) -> dict[str, Any]:
    """Merge session data into the state.

    Args:
        - state: Current state dictionary.
        - session_data: Session data to merge.
        - slices: Slice names to merge (default: ["_internal"]).
    Returns:
        - New state with session data merged.
    """
    if slices is None:
        slices = ["_internal"]
    
    result = dict(state)
    for slice_name in slices:
        if slice_name in session_data:
            current_slice = result.get(slice_name, {})
            if not isinstance(current_slice, dict):
                current_slice = {}
            session_slice = session_data[slice_name]
            if isinstance(session_slice, dict):
                result[slice_name] = {**current_slice, **session_slice}
    
    return result


def reset_internal_flags(
    state: dict[str, Any],
    flags: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Reset internal flags to specified values.

    Args:
        - state: Current state dictionary.
        - flags: Mapping of flag_name to value.
        - **kwargs: Alternative way to specify flags.
    Returns:
        - New state with flags reset.
    """
    all_flags = {**(flags or {}), **kwargs}
    result = state
    
    for flag_name, value in all_flags.items():
        accessor = getattr(Internal, flag_name, None)
        if accessor is not None and isinstance(accessor, StateAccessor):
            result = accessor.set(result, value)
    
    return result


def create_base_state(
    session_id: str = "",
    action: str = "",
    params: dict[str, Any] | None = None,
    message: str | None = None,
    image: str | None = None,
    active_mode: str | None = None,
) -> dict[str, Any]:
    """Create a base state with request and internal slices.

    Args:
        - session_id: Session identifier.
        - action: Action to perform.
        - params: Optional action parameters.
        - message: Optional user message.
        - image: Optional base64-encoded image.
        - active_mode: Optional initial mode.
    Returns:
        - New state with request, response, and _internal slices.
    """
    state: dict[str, Any] = {}
    
    # Request slice
    state = Request.session_id.set(state, session_id)
    state = Request.action.set(state, action)
    state = Request.params.set(state, params)
    state = Request.message.set(state, message)
    state = Request.image.set(state, image)
    
    # Response slice (empty)
    state = reset_response(state)
    
    # Internal slice
    state = Internal.turn_count.set(state, 0)
    state = Internal.is_first_turn.set(state, True)
    state = Internal.active_mode.set(state, active_mode)
    state = Internal.next_node.set(state, None)
    state = Internal.decision.set(state, None)
    state = Internal.error.set(state, None)
    
    return state


def copy_slice(state: dict[str, Any], slice_name: str) -> dict[str, Any]:
    """Return a shallow copy of a slice from state.

    Args:
        - state: Current state dictionary.
        - slice_name: Slice name to copy.
    Returns:
        - Copy of the slice dict, or empty dict if not present.
    """
    slice_data = state.get(slice_name, {})
    if isinstance(slice_data, dict):
        return dict(slice_data)
    return {}


def update_slice(state: dict[str, Any], slice_name: str, **updates: Any) -> dict[str, Any]:
    """Update multiple fields in a slice at once.

    Args:
        - state: Current state dictionary.
        - slice_name: Slice name to update.
        - **updates: Field updates as keyword arguments.
    Returns:
        - New state with slice updated.
    """
    current_slice = state.get(slice_name, {})
    if not isinstance(current_slice, dict):
        current_slice = {}
    new_slice = {**current_slice, **updates}
    return {**state, slice_name: new_slice}


def get_nested(state: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return a nested value from state using a key path.

    Args:
        - state: Current state dictionary.
        - *keys: Path of keys to traverse.
        - default: Default value if the path is not found.
    Returns:
        - Value at the path, or default.
    """
    current = state
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current
