# API Reference (Public)

This document organizes the public API of `agent_contracts` using the template:
Purpose → Signature → Minimal Example → Key Arguments/Returns → Notes.

---

## Core Types

### __version__
- **Purpose**: Get the library version string.
- **Signature**: `__version__: str`
- **Minimal Example**:
  ```python
  import agent_contracts as ac
  print(ac.__version__)
  ```
- **Key Arguments/Returns**: Returns the version string.
- **Notes**: Useful for compatibility checks, but independent of implementation details.

### NodeContract
- **Purpose**: Contract object that declares a node's I/O, dependencies, and triggers.
- **Signature**: `NodeContract(name: str, description: str, reads: list[str], writes: list[str], requires_llm: bool = False, services: list[str] = [], supervisor: str, trigger_conditions: list[TriggerCondition] = [], is_terminal: bool = False, icon: str | None = None)`
- **Minimal Example**:
  ```python
  from agent_contracts import NodeContract, TriggerCondition

  CONTRACT = NodeContract(
      name="search",
      description="Search knowledge base",
      reads=["request"],
      writes=["response"],
      supervisor="main",
      trigger_conditions=[TriggerCondition(when={"request.action": "search"})],
  )
  ```
- **Key Arguments/Returns**: `reads/writes` are the slices read/updated; `trigger_conditions` define activation.
- **Notes**: When `requires_llm=True`, inject an LLM when initializing the node.

### TriggerCondition
- **Purpose**: Express conditions (rules/LLM hints) for activating a node.
- **Signature**: `TriggerCondition(priority: int = 0, when: dict[str, Any] | None = None, when_not: dict[str, Any] | None = None, llm_hint: str | None = None)`
- **Minimal Example**:
  ```python
  from agent_contracts import TriggerCondition

  condition = TriggerCondition(
      priority=100,
      when={"request.action": "search"},
      llm_hint="Search when action is search",
  )
  ```
- **Key Arguments/Returns**: `when`/`when_not` are state matchers; `priority` orders rules.
- **Notes**: You can specify both `when` and `when_not` (both must be satisfied).

### NodeInputs
- **Purpose**: Input container holding slices a node reads.
- **Signature**: `NodeInputs(**slices)`
- **Minimal Example**:
  ```python
  async def execute(self, inputs):
      req = inputs.get_slice("request")
  ```
- **Key Arguments/Returns**: `get_slice(name)` returns the slice dict.
- **Notes**: Accessing undeclared slices may warn or raise depending on configuration.

### NodeOutputs
- **Purpose**: Output container holding slices a node updates.
- **Signature**: `NodeOutputs(**slices)`
- **Minimal Example**:
  ```python
  from agent_contracts import NodeOutputs

  return NodeOutputs(response={"response_type": "done"})
  ```
- **Key Arguments/Returns**: `to_state_updates()` returns LangGraph update dict.
- **Notes**: `None` values are removed from the update dict.

### ModularNode
- **Purpose**: Base class for all nodes. Provides contract-based I/O validation and execution flow.
- **Signature**: `class ModularNode(ABC)` / `__init__(llm: BaseChatModel | None = None, **services)` / `execute(inputs: NodeInputs, config: RunnableConfig | None = None) -> NodeOutputs`
- **Minimal Example**:
  ```python
  from agent_contracts import ModularNode, NodeOutputs

  class MyNode(ModularNode):
      CONTRACT = ...
      async def execute(self, inputs, config=None):
          return NodeOutputs(response={"response_type": "done"})
  ```
- **Key Arguments/Returns**: `execute` performs work; `__call__` is the LangGraph-compatible entry.
- **Notes**: Provide `llm` if `CONTRACT.requires_llm=True`.

### InteractiveNode
- **Purpose**: Provide standard interactive flow steps (prepare → process answer → completion check → next question).
- **Signature**: `class InteractiveNode(ModularNode)` / `prepare_context(...)` / `process_answer(...)` / `check_completion(...)` / `generate_question(...)`
- **Minimal Example**:
  ```python
  class InterviewNode(InteractiveNode):
      CONTRACT = ...
      def prepare_context(self, inputs):
          return {}
      def check_completion(self, context, inputs):
          return False
      async def process_answer(self, context, inputs, config=None):
          return False
      async def generate_question(self, context, inputs, config=None):
          return NodeOutputs(response={"response_type": "question"})
  ```
- **Key Arguments/Returns**: `execute` calls the abstract steps in order.
- **Notes**: `process_answer` returns a `bool`, but state updates are handled by you.

### BaseRequestSlice / BaseResponseSlice / BaseInternalSlice
- **Purpose**: TypedDict templates for canonical slices.
- **Signature**:
  - `class BaseRequestSlice(TypedDict, total=False)`
  - `class BaseResponseSlice(TypedDict, total=False)`
  - `class BaseInternalSlice(TypedDict, total=False)`
- **Minimal Example**:
  ```python
  from agent_contracts import BaseRequestSlice

  req: BaseRequestSlice = {"session_id": "s1", "action": "ask"}
  ```
- **Key Arguments/Returns**: For typing only.
- **Notes**: Extend these for project-specific slices.

### BaseAgentState
- **Purpose**: Minimal state TypedDict containing `request/response/_internal`.
- **Signature**: `class BaseAgentState(TypedDict, total=False)`
- **Minimal Example**:
  ```python
  class MyState(BaseAgentState):
      user: dict
  ```
- **Key Arguments/Returns**: For typing only.
- **Notes**: Add slices via inheritance.

### get_slice
- **Purpose**: Safely retrieve a slice dict from state.
- **Signature**: `get_slice(state: dict, slice_name: str) -> dict`
- **Minimal Example**:
  ```python
  from agent_contracts import get_slice

  request = get_slice(state, "request")
  ```
- **Key Arguments/Returns**: Returns a dict (empty if missing).
- **Notes**: Does not guarantee type safety.

### merge_slice_updates
- **Purpose**: Merge slice updates for LangGraph.
- **Signature**: `merge_slice_updates(state: dict, updates: dict[str, Any] | None) -> dict[str, Any]`
- **Minimal Example**:
  ```python
  updates = merge_slice_updates(state, {"response": {"response_type": "done"}})
  ```
- **Key Arguments/Returns**: Returns merged updates with existing slices.
- **Notes**: Returns an empty dict when `updates` is `None`.

### StateAccessor
- **Purpose**: Provide type-safe get/set for state fields.
- **Signature**: `StateAccessor(slice_name: str, field_name: str, default: T)`
- **Minimal Example**:
  ```python
  from agent_contracts import StateAccessor

  count = StateAccessor("_internal", "turn_count", 0)
  value = count.get(state)
  state = count.set(state, value + 1)
  ```
- **Key Arguments/Returns**: `get(state) -> T` / `set(state, value) -> dict`.
- **Notes**: Always returns a new dict (immutable update).

### Internal / Request / Response
- **Purpose**: Accessor collections for standard slices.
- **Signature**:
  - `class Internal`
  - `class Request`
  - `class Response`
- **Minimal Example**:
  ```python
  from agent_contracts import Internal, Request

  turn = Internal.turn_count.get(state)
  action = Request.action.get(state)
  ```
- **Key Arguments/Returns**: Each field is a `StateAccessor`.
- **Notes**: Avoid mutating `Internal` directly in nodes when possible.

### reset_response / increment_turn / set_error / clear_error
- **Purpose**: Convenience helpers for state slices.
- **Signature**:
  - `reset_response(state: dict) -> dict`
  - `increment_turn(state: dict) -> dict`
  - `set_error(state: dict, error: str) -> dict`
  - `clear_error(state: dict) -> dict`
- **Minimal Example**:
  ```python
  state = increment_turn(state)
  state = set_error(state, "invalid")
  ```
- **Key Arguments/Returns**: Each returns a new state dict.
- **Notes**: All operations are immutable.

### RoutingDecision / RoutingReason / MatchedRule
- **Purpose**: Structured types capturing routing rationale.
- **Signature**:
  - `RoutingDecision(selected_node: str, reason: RoutingReason)`
  - `RoutingReason(decision_type: str, matched_rules: list[MatchedRule] = [], llm_used: bool = False, llm_reasoning: str | None = None)`
  - `MatchedRule(node: str, condition: str, priority: int)`
- **Minimal Example**:
  ```python
  decision = await supervisor.decide_with_trace(state)
  print(decision.selected_node)
  ```
- **Key Arguments/Returns**: `RoutingDecision.to_supervisor_decision()` converts to a simplified form.
- **Notes**: `decision_type` expects values like `terminal_state/rule_match/llm_decision`.

### SupervisorDecision
- **Purpose**: Lightweight type for a supervisor's final decision.
- **Signature**: `SupervisorDecision(next_node: str, reasoning: str = "")`
- **Minimal Example**:
  ```python
  decision = await supervisor.decide(state)
  print(decision.next_node)
  ```
- **Key Arguments/Returns**: `next_node` is the next node name to run.
- **Notes**: Use `decide_with_trace` when you need detailed reasoning.

### BaseActionRouter
- **Purpose**: Abstract base for action-based routing.
- **Signature**: `class BaseActionRouter(ABC)` / `route(action: str, state: dict | None = None) -> str`
- **Minimal Example**:
  ```python
  class MyRouter(BaseActionRouter):
      def route(self, action, state=None):
          return "default_supervisor"
  ```
- **Key Arguments/Returns**: `__call__(state)` enables use as a LangGraph node.
- **Notes**: If `route` raises `ValueError`, an error response is generated.

### ContractValidator / ValidationResult
- **Purpose**: Perform static validation of registered contracts.
- **Signature**:
  - `ContractValidator(registry: NodeRegistry, known_services: set[str] | None = None, strict: bool = False)`
  - `ValidationResult(errors: list[str] = [], warnings: list[str] = [], info: list[str] = [])`
- **Minimal Example**:
  ```python
  validator = ContractValidator(get_node_registry())
  result = validator.validate()
  print(result)
  ```
- **Key Arguments/Returns**: `validate() -> ValidationResult`.
- **Notes**: `strict=True` treats warnings as errors.

### ContractVisualizer
- **Purpose**: Generate architecture docs from a NodeRegistry.
- **Signature**: `ContractVisualizer(registry: NodeRegistry, graph: CompiledStateGraph | None = None)`
- **Minimal Example**:
  ```python
  visualizer = ContractVisualizer(get_node_registry())
  markdown = visualizer.generate_architecture_doc()
  ```
- **Key Arguments/Returns**: `generate_architecture_doc() -> str`.
- **Notes**: Provide `graph` to include LangGraph Mermaid flow.

### ContractDiffReport / NodeChange / diff_contracts
- **Purpose**: Get structured diffs between two contract sets.
- **Signature**:
  - `ContractDiffReport(added: list[str], removed: list[str], changes: list[NodeChange])`
  - `NodeChange(node: str, severity: str, details: list[str] = [])`
  - `diff_contracts(before: dict[str, dict], after: dict[str, dict]) -> ContractDiffReport`
- **Minimal Example**:
  ```python
  before = registry.export_contracts()
  # ... registry update ...
  after = registry.export_contracts()
  report = diff_contracts(before, after)
  print(report.to_text())
  ```
- **Key Arguments/Returns**: `ContractDiffReport.has_breaking()` checks for breaking changes.
- **Notes**: `before/after` are expected to be `NodeContract.model_dump()` format.

### ContractViolationError
- **Purpose**: Exception representing contract violations (undeclared I/O, etc.).
- **Signature**: `class ContractViolationError(RuntimeError)`
- **Minimal Example**:
  ```python
  try:
      outputs = await node(state)
  except ContractViolationError:
      ...
  ```
- **Key Arguments/Returns**: Exception class.
- **Notes**: In strict mode, I/O violations raise exceptions.

---

## Registry & Build

### NodeRegistry
- **Purpose**: Registry that handles node registration, contract management, and trigger evaluation.
- **Signature**: `NodeRegistry(valid_slices: set[str] | None = None)`
- **Minimal Example**:
  ```python
  registry = NodeRegistry()
  registry.register(MyNode)
  matches = registry.evaluate_triggers("main", state)
  ```
- **Key Arguments/Returns**: `register(node_class)` / `evaluate_triggers(supervisor, state)`.
- **Notes**: Slice names not in `valid_slices` are warned.

### TriggerMatch
- **Purpose**: Data type representing a matched trigger condition.
- **Signature**: `TriggerMatch(priority: int, node_name: str, condition_index: int)`
- **Minimal Example**:
  ```python
  matches = registry.evaluate_triggers("main", state)
  top = matches[0]
  ```
- **Key Arguments/Returns**: Sorted by `priority` descending.
- **Notes**: `condition_index` is the index in the `trigger_conditions` array.

### get_node_registry / reset_registry
- **Purpose**: Get/reset the global NodeRegistry.
- **Signature**:
  - `get_node_registry() -> NodeRegistry`
  - `reset_registry() -> None`
- **Minimal Example**:
  ```python
  registry = get_node_registry()
  reset_registry()
  ```
- **Key Arguments/Returns**: None.
- **Notes**: Use `reset_registry` for safe test isolation.

### GenericSupervisor
- **Purpose**: Generic supervisor that decides the next node using trigger rules + LLM.
- **Signature**: `GenericSupervisor(supervisor_name: str, llm: BaseChatModel | None = None, registry: NodeRegistry | None = None, max_iterations: int | None = None, terminal_response_types: set[str] | None = None, context_builder: ContextBuilder | None = None, max_field_length: int | None = None, explicit_routing_handler: ExplicitRoutingHandler | None = None)`
- **Minimal Example**:
  ```python
  supervisor = GenericSupervisor("main", llm=llm)
  decision = await supervisor.decide(state)
  ```
- **Key Arguments/Returns**: `decide(state)` / `decide_with_trace(state)` / `run(state)`.
- **Notes**: `decide_with_trace` returns `RoutingDecision`.

### GraphBuilder
- **Purpose**: Builder that constructs a LangGraph from a NodeRegistry.
- **Signature**: `GraphBuilder(registry: NodeRegistry | None = None, state_class: type | None = None, llm_provider: Callable[[], Any] | None = None, dependency_provider: Callable[[NodeContract], dict] | None = None, supervisor_factory: Callable[[str, Any], GenericSupervisor] | None = None)`
- **Minimal Example**:
  ```python
  builder = GraphBuilder(get_node_registry())
  builder.add_supervisor("main", llm=llm)
  # Use builder.create_node_wrapper(...) etc. to assemble a StateGraph
  ```
- **Key Arguments/Returns**: `add_supervisor(name, llm, **services)` / `create_node_wrapper(...)` / `create_supervisor_wrapper(...)`.
- **Notes**: `llm_provider` lets you create per-node LLM instances.

### build_graph_from_registry
- **Purpose**: Utility to build a LangGraph from the registry in one step.
- **Signature**: `build_graph_from_registry(registry: NodeRegistry | None = None, llm=None, llm_provider: Callable[[], Any] | None = None, dependency_provider: Callable[[NodeContract], dict] | None = None, supervisor_factory: Callable[[str, Any], GenericSupervisor] | None = None, entrypoint: tuple[str, Callable, Callable] | None = None, supervisors: list[str] | None = None, state_class: type | None = None, **services) -> StateGraph`
- **Minimal Example**:
  ```python
  graph = build_graph_from_registry(get_node_registry(), llm=llm, supervisors=["main"])
  compiled = graph.compile()
  ```
- **Key Arguments/Returns**: Returns the pre-compiled `StateGraph`.
- **Notes**: Provide `entrypoint` to start from an external router.

---

## Runtime

### RequestContext
- **Purpose**: Data class holding execution request information.
- **Signature**: `RequestContext(session_id: str, action: str, params: dict[str, Any] | None = None, message: str | None = None, image: str | None = None, resume_session: bool = False, metadata: dict[str, Any] = {})`
- **Minimal Example**:
  ```python
  from agent_contracts import RequestContext

  ctx = RequestContext(session_id="s1", action="answer", message="hi")
  ```
- **Key Arguments/Returns**: `get_param(key, default)` retrieves params.
- **Notes**: `resume_session=True` attempts to restore session state.

### ExecutionResult
- **Purpose**: Data class for execution results (final state and response).
- **Signature**: `ExecutionResult(state: dict[str, Any], response_type: str | None = None, response_data: dict[str, Any] | None = None, response_message: str | None = None, success: bool = True, error: str | None = None)`
- **Minimal Example**:
  ```python
  result = await runtime.execute(ctx)
  print(result.response_type)
  ```
- **Key Arguments/Returns**: `from_state(state)` / `error_result(error, state=None)` / `to_response_dict()`.
- **Notes**: `to_response_dict()` prioritizes `response_type` into `type`.

### RuntimeHooks / DefaultHooks
- **Purpose**: Protocol and default implementation for execution lifecycle hooks.
- **Signature**:
  - `RuntimeHooks.prepare_state(state: dict, request: RequestContext) -> dict`
  - `RuntimeHooks.after_execution(state: dict, result: ExecutionResult) -> None`
  - `class DefaultHooks`
- **Minimal Example**:
  ```python
  class MyHooks:
      async def prepare_state(self, state, request):
          return state
      async def after_execution(self, state, result):
          pass
  ```
- **Key Arguments/Returns**: `prepare_state` returns the state dict.
- **Notes**: Apply changes immutably.

### SessionStore / InMemorySessionStore
- **Purpose**: Abstract session persistence.
- **Signature**:
  - `SessionStore.load(session_id: str) -> dict | None`
  - `SessionStore.save(session_id: str, data: dict, ttl_seconds: int = 3600) -> None`
  - `SessionStore.delete(session_id: str) -> None`
  - `InMemorySessionStore()`
- **Minimal Example**:
  ```python
  store = InMemorySessionStore()
  await store.save("s1", {"_internal": {"turn_count": 1}})
  ```
- **Key Arguments/Returns**: `load` returns the session dict or `None`.
- **Notes**: `InMemorySessionStore` is for development/testing only.

### AgentRuntime
- **Purpose**: Runtime that integrates graph execution, state initialization, session restore, and hooks.
- **Signature**: `AgentRuntime(graph: Any, hooks: RuntimeHooks | None = None, session_store: SessionStore | None = None, slices_to_restore: list[str] | None = None)`
- **Minimal Example**:
  ```python
  runtime = AgentRuntime(compiled_graph, session_store=InMemorySessionStore())
  result = await runtime.execute(RequestContext(session_id="s1", action="ask"))
  ```
- **Key Arguments/Returns**: `execute(request: RequestContext) -> ExecutionResult`.
- **Notes**: Exceptions are converted to `ExecutionResult.error_result(...)`.
# Public API List

This list fixes the public classes/functions that appear in the README and Getting Started guide.

## Nodes and Contracts
- `ModularNode`
- `InteractiveNode`
- `NodeContract`
- `TriggerCondition`
- `NodeInputs`
- `NodeOutputs`
- `StateAccessor`
- `Internal`
- `reset_response`

## Registry and Graph
- `NodeRegistry`
- `GraphBuilder`
- `get_node_registry`
- `build_graph_from_registry`
- `BaseAgentState`

## Supervisor and Context
- `GenericSupervisor`
- `ContextBuilder` (protocol)

## Runtime
- `AgentRuntime`
- `StreamingRuntime`
- `RequestContext`
- `ExecutionResult`
- `RuntimeHooks`
- `SessionStore`
- `InMemorySessionStore`

## Validation, Visualization, and Config
- `ContractValidator`
- `ContractVisualizer`
- `load_config`
