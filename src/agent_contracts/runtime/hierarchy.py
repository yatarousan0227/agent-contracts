"""Runtime types for hierarchical supervisor execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


DecisionKind = Literal["NODE", "SUBGRAPH", "STOP_LOCAL", "STOP_GLOBAL", "FALLBACK"]


@dataclass
class Budgets:
    """Execution budget limits for hierarchical graphs.

    Args:
        - max_depth: Maximum allowed call depth.
        - max_steps: Maximum allowed total steps.
        - max_reentry: Maximum allowed re-entries per subgraph.
    Returns:
        - Budgets instance.
    """
    max_depth: int = 2
    max_steps: int = 40
    max_reentry: int = 2


@dataclass
class CallStackFrame:
    """Call stack frame for an active subgraph invocation.

    Args:
        - subgraph_id: Identifier of the subgraph.
        - depth: Depth within the call stack.
        - entry_step: Step counter when entered.
        - locals: Per-subgraph local data (e.g., input payload).
    Returns:
        - CallStackFrame instance.
    """
    subgraph_id: str
    depth: int
    entry_step: int
    locals: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionTraceItem:
    """Trace a routing decision during hierarchical execution.

    Args:
        - step: Global step count.
        - depth: Call stack depth at decision time.
        - supervisor: Supervisor name if applicable.
        - decision_kind: Decision category (NODE/SUBGRAPH/STOP_*).
        - target: Target node or subgraph identifier.
        - reason: Human-readable reason for the decision.
        - termination_reason: Optional termination reason when stopping.
    Returns:
        - DecisionTraceItem instance.
    """
    step: int
    depth: int
    supervisor: str | None
    decision_kind: DecisionKind
    target: str | None = None
    reason: str | None = None
    termination_reason: str | None = None
