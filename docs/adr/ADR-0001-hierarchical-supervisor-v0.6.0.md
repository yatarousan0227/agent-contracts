# ADR-0001: Hierarchical Supervisor and Subgraph Calls (v0.6.0)

Date: 2026-01-31
Status: Accepted

## Context
We want to introduce hierarchical execution where a supervisor can call a
subgraph (which may itself call subgraphs) and then return to the parent flow.
This must be non-breaking for existing flat graphs and should integrate with the
current routing model and state layout.

The codebase already defines `agent_contracts.routing.RoutingDecision`, so any
new hierarchical decision type must avoid that name to prevent confusion and
collisions.

## Decision
1. Represent subgraph execution as a **CallSubgraph node** inside LangGraph.
   - This keeps the existing string-based routing mechanism intact.
2. Preserve backward compatibility:
   - If no subgraph is registered, behavior remains unchanged.
   - Supervisor output continues to accept `str` for routing.
3. Store new runtime metadata under `_internal` only:
   - `call_stack`, `budgets`, `decision_trace`, `visited_subgraphs`, `step_count`.
4. Define stop semantics:
   - `STOP_LOCAL` ends a child subgraph and returns to the parent.
   - `STOP_GLOBAL` ends the entire session using the existing terminal response
     flow.
5. Enforce recursion safety with default budgets:
   - `max_depth = 2`, `max_steps = 40`, `max_reentry = 2`.
   - Violations terminate safely with explicit `termination_reason` values.
6. Allowlist violations are handled as safe terminal stops with
   `termination_reason="allowlist_violation"` recorded in the decision trace.
7. New hierarchical decision types must use a distinct name such as
   `HierarchicalDecision` or `ExecutionDecision`.

## Consequences
- Existing graphs continue to run without changes.
- Subgraph support can be introduced incrementally without breaking callers.
- Runtime state remains compatible by isolating new keys under `_internal`.
- Clear safety and allowlist behaviors are fixed for future PRs.

## Alternatives Considered
- Use a new routing mechanism (rejected: would break compatibility).
- Require a new decision type everywhere (rejected: opt-in is required).
- Store new fields at the top level of state (rejected: would be breaking).
