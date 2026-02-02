# Core Concepts

> Deep dive into the agent-contracts architecture

---

## Overview

`agent-contracts` is built around a simple principle: **declare what your node does, not how it connects**.

```
┌─────────────────────────────────────────────────────────────┐
│                        Registry                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │ NodeA     │  │ NodeB     │  │ NodeC     │  ...          │
│  │ CONTRACT  │  │ CONTRACT  │  │ CONTRACT  │               │
│  └───────────┘  └───────────┘  └───────────┘               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     GraphBuilder                             │
│  • Analyzes contracts                                        │
│  • Creates supervisors                                       │
│  • Wires LangGraph automatically                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph                               │
│  START → Supervisor ⟷ Nodes → END                           │
└─────────────────────────────────────────────────────────────┘
```

---

## NodeContract

The `NodeContract` is the heart of the library. It declares everything about a node:

```python
NodeContract(
    # === Identification ===
    name="my_node",                    # Unique identifier
    description="What this node does", # Human-readable description
    
    # === I/O Definition ===
    reads=["request", "context"],      # State slices this node reads
    writes=["response"],               # State slices this node writes
    
    # === Dependencies ===
    requires_llm=True,                 # Needs LLM?
    services=["db_service"],           # External services needed
    
    # === Routing ===
    supervisor="main",                 # Which supervisor manages this
    trigger_conditions=[...],          # When to activate this node
    is_terminal=False,                 # End flow after execution?
)
```

### Why Contracts?

| Without Contracts | With Contracts |
|-------------------|----------------|
| Manual graph wiring | Automatic graph construction |
| Hidden dependencies | Explicit I/O declaration |
| Runtime errors | Static validation |
| Hard to document | Auto-generated docs |

---

## State Slices

State in `agent-contracts` is organized into isolated **slices**:

```python
state = {
    "request": {           # Input from user
        "action": "search",
        "params": {"query": "laptop"}
    },
    "response": {          # Output to user
        "response_type": "results",
        "data": [...]
    },
    "context": {           # Shared context
        "user_preferences": {...}
    },
    "_internal": {         # Framework internal
        "decision": "search_node",
        "iteration": 1
    }
}
```

### Design Principles

1. **Separation of Concerns**: Each slice has a single purpose
2. **Explicit Access**: Nodes declare which slices they read/write
3. **Validation**: Unknown slice names and contract I/O violations can be detected as warnings/errors

**Contract I/O behavior (runtime)**:
- **Default**: Warn and continue (undeclared writes are dropped by default)
- **strict**: Raise `ContractViolationError`
- **Undeclared read**: Returns `{}` in default mode (raises in strict mode)
- **Undeclared write**: Dropped by default (raises in strict mode)

YAML example:
```yaml
io:
  strict: true                  # Stop with exception
  warn: true                    # Warning logs
  drop_undeclared_writes: true  # Drop undeclared writes
```

### Built-in Slices

| Slice | Purpose |
|-------|---------|
| `request` | User input (read-only recommended) |
| `response` | User output |
| `_internal` | Framework routing/iteration |

You can define custom slices:

```python
registry.add_valid_slice("orders")
registry.add_valid_slice("workflow")
```

---

## TriggerCondition

Trigger conditions control when a node should be selected:

```python
TriggerCondition(
    priority=10,                           # Higher = evaluated first
    when={"request.action": "search"},     # Match conditions
    when_not={"response.done": True},      # Negative match
    llm_hint="Use for product searches",   # LLM routing hint
)
```

### Priority Levels

| Range | Usage | Example |
|-------|-------|---------|
| 🔴 100+ | Critical/Immediate | Error handlers |
| 🟡 50-99 | Primary handlers | Main business logic |
| 🟢 1-49 | Fallbacks | Default handlers |
| ⚪ 0 | Always match | Catch-all |

### Condition Matching

```python
# Exact value match
when={"request.action": "search"}

# Boolean check
when={"context.authenticated": True}

# Nested path
when={"request.params.category": "electronics"}

# Multiple conditions (AND)
when={"request.action": "buy", "context.cart_ready": True}
```

---

## GenericSupervisor

The supervisor orchestrates node selection using a multi-phase approach.

### Data Sanitization for LLM (v0.3.3+)

The Supervisor automatically sanitizes state data before sending it to the LLM for routing decisions:

**Automatic Handling**:
- **Image Data**: Base64-encoded images (detected via `data:image/` or `image` patterns) are replaced with `"[IMAGE_DATA]"`
- **Long Strings**: Strings exceeding `max_field_length` (default: 10000 chars) are truncated while preserving the beginning
  - Format: `data[:max_field_length] + "...[TRUNCATED:N_chars]"`
  - Example: A 15000-char string becomes: `"first 10000 chars...[TRUNCATED:5000_chars]"`

**Benefits**:
- **Token Efficiency**: Prevents massive token consumption from base64 image data
- **Context Preservation**: Maintains beginning of long fields for better routing decisions
- **Customizable**: Adjust via `max_field_length` parameter

**Configuration**:
```python
from agent_contracts import GenericSupervisor

supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_field_length=10000,  # Default: 10000 characters
)
```

### Decision Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Decision Flow                             │
├─────────────────────────────────────────────────────────────┤
│  1. Terminal State Check                                     │
│     └─ If response_type in terminal_states → done            │
│                                                              │
│  2. Explicit Routing (via handler)                            │
│     └─ custom routing via explicit_routing_handler             │
│                                                              │
│  3. Rule-Based Evaluation                                    │
│     └─ Evaluate all TriggerConditions, collect candidates    │
│                                                              │
│  4. LLM Decision (if available)                             │
│     └─ LLM chooses from candidates using llm_hints           │
│                                                              │
│  5. Fallback                                                 │
│     └─ Use highest priority rule match                       │
└─────────────────────────────────────────────────────────────┘
```

### With vs Without LLM

| Mode | Behavior |
|------|----------|
| **With LLM** | LLM makes final decision using rule hints |
| **Without LLM** | Pure rule-based, uses highest priority match |

---

## InteractiveNode

For conversational agents, use `InteractiveNode`:

```python
from agent_contracts import InteractiveNode, NodeContract, NodeOutputs, TriggerCondition


class QuestionerNode(InteractiveNode):
    CONTRACT = NodeContract(
        name="questioner",
        description="Asks questions and processes answers",
        reads=["request", "workflow"],
        writes=["response", "workflow", "_internal"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(priority=10, llm_hint="Use to ask the next question"),
        ],
    )
    
    def prepare_context(self, inputs):
        """Extract context from inputs."""
        return inputs.get_slice("workflow")
    
    def check_completion(self, context, inputs):
        """Check if questionnaire is complete."""
        return len(context.get("answers", [])) >= 5
    
    async def process_answer(self, context, inputs, config=None):
        """Process user's answer."""
        answer = inputs.get_slice("request").get("answer")
        # Store answer...
        return True
    
    async def generate_question(self, context, inputs, config=None):
        """Generate next question."""
        # Generate question with LLM...
        return NodeOutputs(
            response={
                "response_type": "question",
                "response_data": {"question": "What color?"},
            }
        )
```

### Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                  InteractiveNode Flow                        │
├─────────────────────────────────────────────────────────────┤
│  1. prepare_context()     → Extract needed data              │
│  2. check_completion()    → Already done?                    │
│       └─ Yes → create_completion_output()                    │
│       └─ No ↓                                               │
│  3. process_answer()      → Handle user's response           │
│  4. check_completion()    → Now done?                        │
│       └─ Yes → create_completion_output()                    │
│       └─ No → generate_question()                           │
└─────────────────────────────────────────────────────────────┘
```

---

## ContractValidator

Validate contracts before running:

```python
from agent_contracts import ContractValidator

validator = ContractValidator(
    registry,
    known_services={"db_service", "cache_service"},
)
result = validator.validate()

if result.has_errors:
    print(result)  # Show errors
    exit(1)
```

### Strict Mode (CI-friendly)

```python
validator = ContractValidator(
    registry,
    known_services={"db_service", "cache_service"},
    strict=True,  # Treat warnings as errors
)
result = validator.validate()
```

**Strict mode** turns warnings (unknown services, unreachable nodes, writing to `request`, etc.)
into errors so you can fail fast in CI.

### Validation Levels

| Level | Example |
|-------|---------|
| **ERROR** | Unknown slice in reads/writes |
| **WARNING** | Unknown service, unreachable node |
| **INFO** | Shared writers (multiple nodes write same slice) |


---

## Traceable Routing

For debugging, use `decide_with_trace()`:

```python
decision = await supervisor.decide_with_trace(state)

print(f"Selected: {decision.selected_node}")
print(f"Type: {decision.reason.decision_type}")

for rule in decision.reason.matched_rules:
    print(f"  {rule.node} (P{rule.priority}): {rule.condition}")
```

### Decision Types

| Type | Meaning |
|------|---------|
| `terminal_state` | Response type triggered exit |
| `explicit_routing` | Answer routed to question owner |
| `rule_match` | TriggerCondition matched |
| `llm_decision` | LLM made the choice |
| `fallback` | No match, using default |

### TriggerMatch Structure (v0.4.0+)

Starting from v0.4.0, `evaluate_triggers()` returns `TriggerMatch` objects:

```python
from agent_contracts import TriggerMatch

# evaluate_triggers() return value
matches: list[TriggerMatch] = registry.evaluate_triggers("supervisor_name", state)

for match in matches:
    print(f"Node: {match.node_name}")
    print(f"Priority: {match.priority}")
    print(f"Condition Index: {match.condition_index}")  # The actual matched condition
```

**Benefits:**
- Accurately identifies which condition matched, even with multiple conditions at the same priority
- Provides more precise explanations for LLM routing
- Improves debugging and traceability

**Migration (v0.3.x → v0.4.0):**

```python
# v0.3.x - tuple format
matches: list[tuple[int, str]] = registry.evaluate_triggers("main", state)
for priority, node_name in matches:
    print(f"{node_name}: P{priority}")

# v0.4.0 - TriggerMatch format
matches: list[TriggerMatch] = registry.evaluate_triggers("main", state)
for match in matches:
    print(f"{match.node_name}: P{match.priority}")
```

**Note:** If you're using `GenericSupervisor` or `decide()`/`decide_with_trace()`, no changes are required.


## Supervisor Context Building

The `GenericSupervisor` automatically builds context for LLM-based routing decisions.

### Default Context Building (v0.2.3+)

By default, the Supervisor provides **minimal context** to the LLM:

1. **Base Slices Only**: Always includes `request`, `response`, `_internal`
2. **Rationale**:
   - Candidate slices are already evaluated in trigger conditions
   - Passing them to LLM is redundant and wastes tokens
   - Clear separation: Triggers = rule-based filtering, LLM = final selection
3. **Benefits**:
   - Significant token reduction
   - Better performance (less data to serialize and transmit)
   - Maintains conversation context via `response` for LLM understanding

### Custom Context Builder (v0.3.0+)

For complex scenarios requiring additional context, you can provide a custom `context_builder` function:

```python
from agent_contracts import GenericSupervisor

def my_context_builder(state: dict, candidates: list[str]) -> dict:
    """Build custom context for routing decisions."""
    return {
        "slices": {"request", "response", "_internal", "conversation"},
        "summary": {
            "total_turns": len(state.get("conversation", {}).get("messages", [])),
            "readiness_score": calculate_readiness(state),
        }
    }

supervisor = GenericSupervisor(
    supervisor_name="orders",
    llm=llm,
    context_builder=my_context_builder,
)
```

### Summary Format (v0.3.1+)

The `summary` field in `context_builder` return value supports both `dict` and `str` formats:

```python
# String format - directly included in prompt (ideal for formatted text)
def context_builder(state, candidates):
    return {
        "slices": {"request", "response", "conversation"},
        "summary": f"Recent conversation:\n{format_messages(state)}"
    }

# Dict format - JSON-serialized before inclusion (preserves structure)
def context_builder(state, candidates):
    return {
        "slices": {"request", "response", "conversation"},
        "summary": {
            "turn_count": 5,
            "topics": ["orders", "preferences"]
        }
    }
```

### Using with Registry-Based Graph (v0.3.1+)

When using `build_graph_from_registry()` with `llm_provider`, use `supervisor_factory` to inject custom supervisors:

```python
from agent_contracts import build_graph_from_registry, GenericSupervisor

def my_context_builder(state, candidates):
    return {
        "slices": {"request", "response", "conversation"},
        "summary": f"Conversation history:\n{format_history(state)}"
    }

def supervisor_factory(name: str, llm):
    return GenericSupervisor(
        supervisor_name=name,
        llm=llm,
        context_builder=my_context_builder,  # Custom context preserved!
    )

graph = build_graph_from_registry(
    llm_provider=get_llm,
    supervisor_factory=supervisor_factory,  # Inject custom supervisors
    supervisors=["orders", "notifications"],
)
```

### Context Builder Protocol

```python
from typing import Protocol

class ContextBuilder(Protocol):
    def __call__(self, state: dict, candidates: list[str]) -> dict:
        """
        Build context for LLM routing decisions.
        
        Args:
            state: Current agent state
            candidates: List of candidate node names
            
        Returns:
            Dictionary with:
            - slices (set[str]): Set of slice names to include
            - summary (dict | str | None): Optional additional context
              - str: Directly included in prompt (formatted text)
              - dict: JSON-serialized before inclusion
        """
        ...
```

### Use Cases

| Scenario | Custom Context |
|----------|---------------|
| **E-commerce** | Include `cart`, `inventory` for purchase-aware routing |
| **Customer Support** | Include `ticket_history`, `sentiment` for context-aware responses |
| **Education** | Include `learning_progress`, `pace` for adaptive tutoring |
| **Workflow** | Include `conversation` with turn counts and history |

### Example: Conversation-Aware Routing

```python
def conversation_context_builder(state: dict, candidates: list[str]) -> dict:
    """Include conversation history for better routing."""
    messages = state.get("conversation", {}).get("messages", [])
    
    # Format as string for better LLM readability
    formatted = "\n".join([
        f"{m['role']}: {m['content']}"
        for m in messages[-5:]  # Last 5 messages
    ])
    
    return {
        "slices": {"request", "response", "_internal", "conversation"},
        "summary": f"Recent conversation ({len(messages)} turns):\n{formatted}"
    }
```

### Benefits

- **Flexible**: Customize context per application domain
- **Backward Compatible**: Defaults to minimal context when not provided
- **Type-Safe**: Protocol ensures correct implementation
- **Efficient**: Control exactly what context is sent to LLM
- **Format Support**: String for formatted text, dict for structured data

### Migration Notes

- **v0.2.x → v0.3.0**: No migration needed, fully backward compatible
- **v0.3.0 → v0.3.1**: If using `llm_provider` with `build_graph_from_registry()`, use `supervisor_factory` to preserve `context_builder`

---

## StateAccessor Pattern

Type-safe, immutable access to state fields:

```python
from agent_contracts import Internal, Request, Response, reset_response

# Read state
count = Internal.turn_count.get(state)
action = Request.action.get(state)

# Write state (immutable - returns new state)
state = Internal.turn_count.set(state, 5)
state = reset_response(state)
```

### Available Accessors

| Class | Fields |
|-------|--------|
| `Internal` | `turn_count`, `is_first_turn`, `active_mode`, `next_node`, `error` |
| `Request` | `session_id`, `action`, `params`, `message`, `image` |
| `Response` | `response_type`, `response_data`, `response_message` |

### Convenience Functions

```python
from agent_contracts import increment_turn, set_error, clear_error

state = increment_turn(state)  # turn_count++, is_first_turn=False
state = set_error(state, "Something failed")
state = clear_error(state)
```

---

## Runtime Layer

For production applications, use the Runtime Layer for unified execution:

### AgentRuntime

```python
from agent_contracts import AgentRuntime, RequestContext, InMemorySessionStore

runtime = AgentRuntime(
    graph=compiled_graph,
    session_store=InMemorySessionStore(),
)

result = await runtime.execute(RequestContext(
    session_id="abc123",
    action="answer",
    message="I like casual",
    resume_session=True,
))
```

### Execution Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                  AgentRuntime Lifecycle                      │
├─────────────────────────────────────────────────────────────┤
│  1. Create initial state                                     │
│  2. Restore session (if resume_session=True)                 │
│  3. hooks.prepare_state() → Pre-execution customization      │
│  4. graph.ainvoke() → Execute LangGraph                      │
│  5. Build ExecutionResult                                    │
│  6. hooks.after_execution() → Persistence, cleanup           │
└─────────────────────────────────────────────────────────────┘
```

### Custom Hooks

```python
from agent_contracts import RuntimeHooks

class MyHooks(RuntimeHooks):
    async def prepare_state(self, state, request):
        # Normalize state, load resources
        return state
    
    async def after_execution(self, state, result):
        # Save session, log, etc.
        await self.session_store.save(...)
```

### StreamingRuntime (SSE)

```python
from agent_contracts.runtime import StreamingRuntime, StreamEventType

runtime = (
    StreamingRuntime()
    .add_node("search", search_node, "Searching...")
    .add_node("stylist", stylist_node, "Generating...")
)

async for event in runtime.stream(request):
    if event.type == StreamEventType.NODE_END:
        print(f"Node {event.node_name} complete")
    yield event.to_sse()
```

---

## Hierarchical Supervisor (v0.6.0)

Starting from v0.6.0, parent supervisors can invoke child subgraphs and return to the parent after the child graph completes.

### Overview

Hierarchical execution is **opt-in**. A parent supervisor invokes a subgraph by returning:

```
call_subgraph::<subgraph_id>
```

```
┌─────────────────────────────────────────────────────────────┐
│                     Domain Supervisor                        │
│                                                              │
│  decision = "call_subgraph::fashion"                        │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              CallSubgraph (fashion)                  │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │        Fashion Supervisor                    │    │    │
│  │  │             │                                │    │    │
│  │  │             ▼                                │    │    │
│  │  │        TrendNode → END                       │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │                    │                                 │    │
│  └────────────────────┼─────────────────────────────────┘    │
│                       ▼                                      │
│              Back to Domain Supervisor                       │
└─────────────────────────────────────────────────────────────┘
```

### SubgraphContract and SubgraphDefinition

```python
from agent_contracts import SubgraphContract, SubgraphDefinition

# Define subgraph contract
contract = SubgraphContract(
    subgraph_id="fashion",
    description="Fashion trend subgraph",
    reads=["request"],
    writes=["response"],
    entrypoint="fashion_supervisor",
)

# Define subgraph composition
definition = SubgraphDefinition(
    subgraph_id="fashion",
    supervisors=["fashion_supervisor"],
    nodes=["trend_node"],
)

# Register with registry
registry.register_subgraph(contract, definition)
```

### Safety Budgets

Hierarchical execution enforces the following limits:

| Limit | Default | Description |
|-------|---------|-------------|
| `max_depth` | 2 | Maximum call stack depth |
| `max_steps` | 40 | Maximum total steps |
| `max_reentry` | 2 | Maximum re-entries per subgraph |

```python
state = {
    "_internal": {
        "budgets": {"max_depth": 3, "max_steps": 50, "max_reentry": 2}
    }
}
```

Exceeding a limit triggers safe termination with a recorded `termination_reason`.

### DecisionTrace

When `enable_subgraphs=True`, routing history is recorded in `_internal.decision_trace`:

- `step`: Global step count
- `depth`: Call stack depth
- `supervisor`: Supervisor name
- `decision_kind`: `NODE`, `SUBGRAPH`, `STOP_LOCAL`, `STOP_GLOBAL`, `FALLBACK`
- `target`: Selected node name or subgraph ID

See the [Hierarchical Supervisor Guide](guides/hierarchical-supervisor.md) for details.

---

## Next Steps

- 🎯 [Best Practices](best_practices.md) - Design patterns
- 🐛 [Troubleshooting](troubleshooting.md) - Common issues

