# agent-contracts: Hierarchical / Recursive Supervisor (Subgraph Calls)
## Implementation Plan (Non-breaking, Opt-in) — v0.1

This document is an implementation plan to add **hierarchical + recursive supervisors** to **agent-contracts** by introducing **SubgraphContracts** and a **CallSubgraph** runtime mechanism, while keeping **backward compatibility** (non-breaking change) by default.

---

## 0) Goals and Non-Goals

### Goals
- Support **hierarchical supervisor pattern**: parent supervisor delegates to **subgraphs**; subgraph entrypoint is typically a supervisor.
- Support **recursion** (subgraph calling subgraph) with **safety guards**:
  - `max_depth`, `max_steps`, `max_reentry` / cycle detection
- Maintain **contract-driven boundaries**:
  - Subgraph-level `reads/writes` boundary
  - Supervisor-level allowlist (allowed nodes/subgraphs)
- Provide **observability**:
  - `DecisionTrace` persisted to state (auto-initialized if absent)
- Provide **visualization**:
  - Subgraph clusters + call edges

### Non-Goals (v0.1)
- Parallel/consensus supervision (multiple supervisors deciding simultaneously)
- Hard-require new state fields globally (trace/callstack/budgets remain optional via runtime injection)
- Forcing all existing routers/supervisors to return a new decision type (compat layer stays)

---

## 1) Compatibility Strategy (Must Follow)

To avoid breaking changes:
1. **Existing graphs keep working** with no subgraph registration.
2. Supervisor/router outputs accept **both**:
   - `str` (node_id) — legacy
   - `RoutingDecision` — new
3. `system.call_stack`, `system.decision_trace`, `system.budgets` are **optional** in state:
   - Runtime injects defaults if missing.
4. Validator strict checks are either:
   - enabled only when new features are used, or
   - enabled via `strict=True` (opt-in).

---

## 2) PR Plan (Incremental, Reviewable)

### PR0 — Repo Recon + ADR (No behavior change)
**Objective:** Identify insertion points in existing architecture and lock design decisions.

**Tasks**
- Locate current implementations of:
  - `NodeContract` (or equivalent)
  - `Registry`
  - `GraphBuilder`
  - `Validator`
  - `Visualizer`
  - `Executor/Runtime`
- Document current constraints and extension points.
- Add ADR + spec doc.

**Artifacts**
- `docs/adr/ADR-xxx-hierarchical-supervisor.md`
- `docs/spec/hierarchical-supervisor-v0.1.md`

**Acceptance**
- CI green
- Docs added with clear decisions and terminology

---

### PR1 — Core Type Definitions (No runtime behavior yet)
**Objective:** Introduce first-class types for subgraphs, decisions, tracing, budgets, call stack.

**Add**
- `SubgraphContract`
- `RoutingDecision`:
  - `NODE`, `SUBGRAPH`, `STOP_LOCAL`, `STOP_GLOBAL`, `ASK_CLARIFICATION`, `FALLBACK`
- `DecisionTraceItem`
- `Budgets`:
  - `max_depth`, `max_steps`, `max_reentry`
- `CallStackFrame`:
  - `subgraph_id`, `depth`, `locals`, `entry_step`

**Suggested Paths (adapt to repo conventions)**
- `agent_contracts/contracts/subgraph.py`
- `agent_contracts/runtime/decision.py`
- `agent_contracts/runtime/trace.py`
- `agent_contracts/runtime/budgets.py`
- `agent_contracts/runtime/callstack.py`

**Acceptance**
- Lint/type checks pass (as per repo)
- Unit tests cover:
  - object creation, validation, serialization (if repo uses pydantic/dataclasses)
- Public API exports consistent with existing patterns

---

### PR2 — Registry Extension (Register/Resolve Subgraphs)
**Objective:** Allow registry to store and resolve `SubgraphContract` + a subgraph definition.

**Add/Change**
- `Registry.register_subgraph(subgraph_contract, subgraph_def)`
- `Registry.get_subgraph(subgraph_id)`
- `Registry.list_subgraphs()`
- Guard against ID collisions with node IDs

**Acceptance**
- Unit tests:
  - register/get/list
  - collision errors

---

### PR3 — GraphBuilder Support for Subgraphs (Static composition)
**Objective:** Build and store subgraph boundary metadata (cluster definition) without running them yet.

**Add/Change**
- GraphBuilder constructs:
  - `subgraph_id -> {entrypoint, exitpoints, nodes, edges, reads/writes boundary}`
- Ensure subgraphs can be visualized/validated later.

**Acceptance**
- Unit tests:
  - entrypoint reachability produces stable node set
  - exitpoints (if provided) validated
- Backward compatible: existing flat graphs unchanged

---

### PR4 — Validator Enhancements (Boundary + Allowlist + Safety defaults)
**Objective:** Add static verification without breaking existing graphs.

**New validations**
1. **Subgraph boundary**
   - internal node `reads/writes` must be subset of `SubgraphContract.reads/writes`
2. **Supervisor allowlist presence**
   - if a supervisor policy is used, it must define allowed node/subgraph IDs
3. **Recursion safety defaults**
   - runtime defaults exist (or validator warns if strict)
4. **DecisionTrace schema**
   - optional in non-strict; required or warning in strict mode (pick a policy)

**Design note**
- Boundary checks apply only if subgraphs are present.
- Strict checks should be `strict=True` only, or “warn” by default.

**Acceptance**
- Unit tests:
  - boundary violation errors
  - allowlist missing errors (only when policy used)
  - strict/non-strict behavior verified

---

### PR5 — Runtime / Executor: CallSubgraph + Budgets + Cycle Detection (Core feature)
**Objective:** Enable `RoutingDecision(type=SUBGRAPH)` and safe recursion.

**Behavior**
- When decision is `SUBGRAPH`:
  1. `push_frame(subgraph_id, depth+1)`
  2. validate `SubgraphInput` (schema) and store in `frame.locals`
  3. jump to subgraph `entrypoint` execution loop
- Subgraph completion:
  - subgraph returns `STOP_LOCAL` with output
  - validate `SubgraphOutput` (schema)
  - `pop_frame()`
  - map output into parent-visible state (recommended: dedicated slice like `domain_result`)
- Enforce budgets:
  - if `depth > max_depth`: stop with `termination_reason="max_depth_exceeded"`
  - if `steps > max_steps`: stop with `termination_reason="max_steps_exceeded"`
- Cycle detection / reentry:
  - maintain `visited[subgraph_id]`
  - if exceeds `max_reentry`: stop with `termination_reason="cycle_detected"`
- Allowlist enforcement at runtime:
  - if decision target not in allowlist:
    - convert to `FALLBACK` or safe `STOP_LOCAL` with reason (decide and document)

**Compatibility requirement**
- If a supervisor returns `str`, treat as `NODE` decision.

**Acceptance**
- Integration tests:
  - Parent -> SUBGRAPH -> child supervisor -> node -> STOP_LOCAL -> parent resumes
  - max_depth stops safely + trace reason recorded
  - cycle detection works
  - allowlist violation is handled per spec

---

### PR6 — DecisionTrace Standardization (Observability)
**Objective:** Ensure every supervisor decision is traceable, especially across recursion.

**Add**
- `trace.append_decision(...)` utility
- Executor auto-appends minimal trace entries per step if missing
  - (supervisor implementations can provide richer candidates/rationale)

**Acceptance**
- Trace always exists after execution
- `step`, `depth`, `supervisor_id`, `choice`, and `termination_reason` (on stop) are recorded

---

### PR7 — Visualize: Subgraph Clusters + Call Edges
**Objective:** Make hierarchy explicit in exported graphs.

**Add/Change**
- Render subgraphs as clusters (`subgraph` / `cluster` blocks)
- Render call edges:
  - `Supervisor -> Subgraph(entrypoint)` as dotted/annotated edge when possible

**Acceptance**
- Snapshot tests on visualize output (if supported)
- Existing visualize output remains stable when no subgraphs are used

---

### PR8 — Examples + Documentation (User Adoption)
**Objective:** Provide minimal working example and best practices.

**Add**
- `examples/hierarchical_supervisor_minimal/`
  - `DomainSupervisor` -> `fashion` subgraph -> `FashionSupervisor` -> `TrendNode` -> return
- Docs:
  - `docs/guides/hierarchical-supervisor.md`:
    - STOP_LOCAL vs STOP_GLOBAL
    - state slice scoping and boundaries
    - budgets + cycle detection configuration
    - reading DecisionTrace
    - migration guidance (legacy str decisions supported)

**Acceptance**
- Example runs as documented
- Example included in CI (lightweight)

---

## 3) Core Decisions to Freeze (to avoid ambiguity)

1. **STOP_LOCAL**: ends the *current subgraph* and returns output to parent
2. **STOP_GLOBAL**: ends the *entire workflow/session* (typically only top-level supervisor emits)
3. Child subgraph can request global end via:
   - `STOP_LOCAL` + output flag `should_end=true` (end proposal)
4. Defaults injected by runtime when absent:
   - `max_depth=2`, `max_steps=40`, `max_reentry=2`
5. Allowlist violations:
   - runtime converts to safe fallback (document exact fallback)

---

## 4) Minimal Acceptance Scenario (End-to-End)

A. Normal path
- `DomainSupervisor` chooses `SUBGRAPH:fashion`
- runtime pushes call stack frame and starts `FashionSupervisor`
- `FashionSupervisor` chooses `NODE:trend_node`
- `trend_node` writes within fashion boundary
- `FashionSupervisor` emits `STOP_LOCAL` with output
- runtime pops frame, maps output to parent state
- `DomainSupervisor` emits `STOP_GLOBAL` or continues

B. Safety path
- `max_depth` exceeded -> safe stop with `termination_reason`
- cycle detected -> safe stop with `termination_reason`

C. Observability
- DecisionTrace has entries with `(step, depth, supervisor_id, choice, reason)`

---

## 5) Codex Task Prompts (Copy/Paste)

### PR1 — Types only
You are working in the agent-contracts repo.
1) Read the existing architecture: NodeContract, Registry, GraphBuilder, Validator, Visualizer, Runtime/Executor.
2) Add new core types for hierarchical supervisors:
   - SubgraphContract (input/output schema + reads/writes boundary + entrypoint/exitpoints)
   - RoutingDecision (NODE/SUBGRAPH/STOP_LOCAL/STOP_GLOBAL/ASK_CLARIFICATION/FALLBACK)
   - DecisionTraceItem, Budgets, CallStackFrame
3) Place them into the most appropriate existing modules (follow current code style and patterns).
4) Export public APIs consistently with existing __init__.py style.
5) Add unit tests matching repo conventions.
Do not implement runtime behavior yet.

### PR5 — CallSubgraph runtime
Implement runtime support for hierarchical subgraphs in agent-contracts.
Requirements:
- Executor supports RoutingDecision type SUBGRAPH:
  - push CallStackFrame(subgraph_id, depth+1)
  - validate SubgraphInput schema, store in frame.locals
  - jump execution to subgraph entrypoint node
- Subgraph completes via STOP_LOCAL: validate output schema, pop frame, map output into parent-visible state.
- Enforce budgets (max_depth, max_steps) and cycle detection (max_reentry/visited) with termination_reason recorded in DecisionTrace.
- Enforce allowlist at runtime: if decision target not allowed, fallback to a safe STOP_LOCAL or configured fallback node (document behavior).
Add integration tests with a minimal graph demonstrating parent->subgraph->node->return and safety limits.

---

## 6) Release Guidance

- Ship as **minor** release when:
  - feature is opt-in, defaults injected, legacy outputs supported.
- Consider **major** release only if:
  - you remove legacy `str` decisions, or
  - you make trace/budgets/state fields mandatory, or
  - you enable strict validation by default.

---

End of plan.
