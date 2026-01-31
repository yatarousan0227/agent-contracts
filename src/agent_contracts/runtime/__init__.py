"""Runtime package - Agent execution and session management.

This package provides:
- AgentRuntime: Unified execution engine for agent graphs
- StreamingRuntime: Node-by-node streaming execution
- RuntimeHooks: Customization points for app-specific logic
- SessionStore: Session persistence abstraction
- RequestContext / ExecutionResult: Typed I/O containers
- State operations: Helpers for immutable state manipulation
"""
from agent_contracts.runtime.context import RequestContext, ExecutionResult
from agent_contracts.runtime.hooks import RuntimeHooks, DefaultHooks
from agent_contracts.runtime.session import SessionStore, InMemorySessionStore
from agent_contracts.runtime.executor import AgentRuntime
from agent_contracts.runtime.hierarchy import Budgets, CallStackFrame, DecisionTraceItem
from agent_contracts.runtime.state_ops import (
    ensure_slices,
    merge_session,
    reset_internal_flags,
    create_base_state,
    copy_slice,
    update_slice,
    get_nested,
)
from agent_contracts.runtime.streaming import (
    StreamEvent,
    StreamEventType,
    NodeExecutor,
    StreamingRuntime,
    create_status_event,
    create_progress_event,
    create_data_event,
)

__all__ = [
    # Context
    "RequestContext",
    "ExecutionResult",
    # Hooks
    "RuntimeHooks",
    "DefaultHooks",
    # Session
    "SessionStore",
    "InMemorySessionStore",
    # Executor
    "AgentRuntime",
    # Hierarchy Types
    "Budgets",
    "CallStackFrame",
    "DecisionTraceItem",
    # Streaming
    "StreamEvent",
    "StreamEventType",
    "NodeExecutor",
    "StreamingRuntime",
    "create_status_event",
    "create_progress_event",
    "create_data_event",
    # State Operations
    "ensure_slices",
    "merge_session",
    "reset_internal_flags",
    "create_base_state",
    "copy_slice",
    "update_slice",
    "get_nested",
]
