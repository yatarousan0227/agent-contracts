"""State Slices - Domain-separated State.

Following LangGraph best practices, State is separated by domain.
Each node declares and accesses only the slices it needs via Contract.
"""
from __future__ import annotations

from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from agent_contracts.runtime.hierarchy import Budgets, CallStackFrame, DecisionTraceItem


# =============================================================================
# Base Slices (Generic - Extend in your project)
# =============================================================================

class BaseRequestSlice(TypedDict, total=False):
    """Define the base request slice structure.

    Args:
        - session_id: Session identifier.
        - action: Requested action name.
        - params: Optional request parameters.
        - message: Optional user message.
        - image: Optional base64-encoded image.
    Returns:
        - BaseRequestSlice mapping.
    """
    session_id: str
    action: str
    params: dict | None
    message: str | None
    image: str | None


class BaseResponseSlice(TypedDict, total=False):
    """Define the base response slice structure.

    Args:
        - response_type: Response type string.
        - response_data: Response payload.
        - response_message: Optional response message.
    Returns:
        - BaseResponseSlice mapping.
    """
    response_type: str | None
    response_data: dict | None
    response_message: str | None


class BaseInternalSlice(TypedDict, total=False):
    """Define the base internal slice structure.

    Args:
        - active_mode: Current active mode name.
        - turn_count: Turn counter.
        - is_first_turn: Whether this is the first turn.
        - next_node: Next node to execute.
        - decision: Supervisor decision name.
        - error: Error message if present.
        - call_stack: Call stack frames for hierarchical execution.
        - budgets: Execution budgets for hierarchical execution.
        - decision_trace: Decision trace entries.
        - visited_subgraphs: Subgraph visit counts.
        - step_count: Global step counter for wrappers.
    Returns:
        - BaseInternalSlice mapping.
    """
    active_mode: str | None
    turn_count: int
    is_first_turn: bool
    next_node: str | None
    decision: str | None
    error: str | None
    call_stack: list["CallStackFrame"]
    budgets: "Budgets"
    decision_trace: list["DecisionTraceItem"]
    visited_subgraphs: dict[str, int]
    step_count: int


# =============================================================================
# Base Agent State
# =============================================================================

class BaseAgentState(TypedDict, total=False):
    """Define the base agent state structure.

    Args:
        - request: Request slice data.
        - response: Response slice data.
        - _internal: Internal control slice data.
    Returns:
        - BaseAgentState mapping.
    """
    request: BaseRequestSlice
    response: BaseResponseSlice
    _internal: BaseInternalSlice


# =============================================================================
# Helper Functions
# =============================================================================

def get_slice(state: dict[str, Any], slice_name: str) -> dict[str, Any]:
    """Return a slice dictionary from state.

    Args:
        - state: Agent state dictionary.
        - slice_name: Slice name (request, response, _internal, etc.).
    Returns:
        - Slice dict (empty if missing).
    """
    return state.get(slice_name, {})


def merge_slice_updates(
    state: dict[str, Any],
    updates: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge slice-level updates into full slices.

    Args:
        - state: Current state.
        - updates: Mapping of slice updates.
    Returns:
        - Merged updates with full slice dictionaries.
    """
    if not updates:
        return {}

    merged: dict[str, Any] = {}
    for slice_name, slice_updates in updates.items():
        current_slice = state.get(slice_name, {})
        if isinstance(current_slice, dict) and isinstance(slice_updates, dict):
            merged[slice_name] = {**current_slice, **slice_updates}
        else:
            merged[slice_name] = slice_updates
    return merged


def apply_slice_updates(state: dict, updates: dict[str, Any] | None) -> dict:
    """Apply updates to state and return new state."""
    merged_updates = merge_slice_updates(state, updates)
    if not merged_updates:
        return dict(state)
    new_state = dict(state)
    new_state.update(merged_updates)
    return new_state
