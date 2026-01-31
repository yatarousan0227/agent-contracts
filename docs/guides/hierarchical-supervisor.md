# Hierarchical Supervisor Guide (v0.6.0)

This guide explains how to call subgraphs from a parent supervisor, return to the parent, and enforce safety budgets.

## Overview

Hierarchical execution is opt-in. When enabled, a supervisor can route to a **CallSubgraph** node by returning a decision string:

```
call_subgraph::<subgraph_id>
```

The CallSubgraph node runs the child graph and returns to the parent supervisor when the child reaches `END`.

Node names must not use the reserved `call_subgraph::` prefix.

## Minimal Setup

1) Define a child node and register it.
2) Register a subgraph contract/definition.
3) Build a graph with `enable_subgraphs=True`.
4) Route to the subgraph from the parent supervisor (explicit handler or custom supervisor).

```python
from agent_contracts import (
    GenericSupervisor,
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    NodeRegistry,
    SubgraphContract,
    SubgraphDefinition,
    TriggerCondition,
    build_graph_from_registry,
)

class TrendNode(ModularNode):
    CONTRACT = NodeContract(
        name="trend_node",
        description="Return a fashion trend",
        reads=["request"],
        writes=["response"],
        supervisor="fashion",
        is_terminal=True,
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={"response_type": "fashion_trend", "response_message": "..."}
        )

registry = NodeRegistry()
registry.register(TrendNode)

registry.register_subgraph(
    SubgraphContract(
        subgraph_id="fashion",
        description="Fashion trend subgraph",
        reads=["request"],
        writes=["response"],
        entrypoint="fashion",
    ),
    SubgraphDefinition(
        subgraph_id="fashion",
        supervisors=["fashion"],
        nodes=["trend_node"],
    ),
)


def route_domain(state: dict) -> str | None:
    return "call_subgraph::fashion"


def supervisor_factory(name: str, llm):
    if name == "domain":
        return GenericSupervisor(
            supervisor_name=name,
            llm=None,
            registry=registry,
            explicit_routing_handler=route_domain,
        )
    return GenericSupervisor(supervisor_name=name, llm=None, registry=registry)


graph = build_graph_from_registry(
    registry=registry,
    supervisors=["domain"],
    llm_provider=lambda: None,
    supervisor_factory=supervisor_factory,
    enable_subgraphs=True,
)
```

A runnable minimal example is included at:

- `examples/hierarchical_supervisor_minimal/`

## Stop Semantics

- **STOP_LOCAL**: End the current subgraph and return to the parent.
  - In practice, when a child graph reaches `END`, the CallSubgraph wrapper returns to the parent supervisor.
- **STOP_GLOBAL**: End the entire session.
  - Triggered by terminal response types or by safety/allowlist violations.

## Budgets and Cycle Detection

The CallSubgraph wrapper enforces budgets stored under `_internal.budgets`:

- `max_depth` (default: 2)
- `max_steps` (default: 40)
- `max_reentry` (default: 2)

Example:

```python
state = {
    "request": {"action": "fashion"},
    "response": {},
    "_internal": {
        "budgets": {"max_depth": 1, "max_steps": 20, "max_reentry": 1}
    },
}
```

When a budget is exceeded, the runtime stops safely and records a termination reason:

- `max_depth_exceeded`
- `max_steps_exceeded`
- `cycle_detected`

## Allowlist Behavior

You can restrict routing targets per supervisor:

```python
supervisor_allowlists = {"domain": {"fashion", "done"}}
```

Notes:
- Use the **subgraph id** (`fashion`) in the allowlist, not the `call_subgraph::` prefix.
- When a decision violates the allowlist, execution ends with `response_type="terminal"` and
  `termination_reason="allowlist_violation"` in the decision trace.

## Decision Trace

When `enable_subgraphs=True`, the graph wrapper records routing decisions in
`_internal.decision_trace`.

Each entry includes:
- `step`: global step counter
- `depth`: call stack depth
- `supervisor`: supervisor name
- `decision_kind`: `NODE`, `SUBGRAPH`, `STOP_LOCAL`, `STOP_GLOBAL`, `FALLBACK`
- `target`: selected node or subgraph id
- `termination_reason`: only for safe stops

## Legacy Compatibility

Hierarchical routing is non-breaking and opt-in. The supervisor still writes a string to
`_internal.decision`, and existing flat graphs run unchanged.
