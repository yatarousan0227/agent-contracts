# Hierarchical Supervisor Spec v0.6.0

Status: frozen for v0.6.0

## Goals
- Add hierarchical execution via subgraph calls (parent supervisor -> child subgraph -> return).
- Keep existing flat graphs working without changes (non-breaking, opt-in).
- Define state keys, stop semantics, safety budgets, and allowlist behavior in one place.

## Compatibility and Opt-in
- If no subgraph is registered, existing behavior of NodeRegistry, GraphBuilder, and GenericSupervisor stays unchanged.
- Supervisor output continues to accept `str` (legacy routing) as the default.
- Any new decision type for hierarchical execution must avoid the existing
  `agent_contracts.routing.RoutingDecision` name.

## Subgraph Invocation Model
- A subgraph is represented in LangGraph as a **CallSubgraph node**.
- The supervisor routes to the CallSubgraph node using the existing string-based
  routing mechanism. This preserves the current `_internal.decision` behavior.
- The CallSubgraph node is responsible for starting the child subgraph and
  returning to the parent when the child ends.
- Node names must not use the reserved `call_subgraph::` prefix.

## State Keys (all under `_internal`)
Additional data lives under `_internal` to avoid breaking state schemas.

- `_internal.call_stack`: list of call stack frames
- `_internal.budgets`: execution budgets
- `_internal.decision_trace`: list of decision trace items
- `_internal.visited_subgraphs`: `{subgraph_id: count}`
- `_internal.step_count`: integer incremented by node/supervisor wrappers

Suggested minimum fields:
- CallStackFrame: `subgraph_id`, `depth`, `entry_step`, `locals`
- Budgets: `max_depth`, `max_steps`, `max_reentry`
- DecisionTraceItem: `step`, `depth`, `supervisor`, `decision_kind`, `target`,
  `reason`, `termination_reason`

## Stop Semantics
- `STOP_LOCAL`: end the current subgraph and return to the parent CallSubgraph node.
  - Implementation mapping: child graph reaches `END`.
- `STOP_GLOBAL`: end the entire session.
  - Implementation mapping: use existing terminal response handling in the parent.

## Safety Budgets and Enforcement
Defaults (v0.6.0):
- `max_depth = 2`
- `max_steps = 40`
- `max_reentry = 2`

Enforcement (fixed behavior):
- `max_depth` exceeded: safe stop with `termination_reason="max_depth_exceeded"`
- `max_steps` exceeded: safe stop with `termination_reason="max_steps_exceeded"`
- `max_reentry` exceeded: safe stop with `termination_reason="cycle_detected"`

## Allowlist Violations
If a supervisor selects a node or subgraph not on its allowlist:
- Perform a safe terminal stop.
- Record `termination_reason="allowlist_violation"` in the decision trace.

## Naming Constraint
Because `agent_contracts.routing.RoutingDecision` already exists, any new
hierarchical decision type should use a distinct name (for example
`HierarchicalDecision` or `ExecutionDecision`).
