# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Runtime**: `StreamingRuntime.stream_with_graph()` now supports `include_subgraphs` parameter (default: `True`)
  - When enabled, streams events from subgraph nodes individually
  - Node names include subgraph path (e.g., `node::subgraph::nested`)

## [0.6.0] - 2026-01-21

### Added
- **Hierarchical Supervisor**: Opt-in subgraph calls via CallSubgraph nodes
- **Safety Budgets**: Max depth/steps/re-entry enforcement with decision traces
- **Allowlists**: Safe termination on allowlist violations for supervisors/subgraphs
- **Examples/Docs**: Minimal hierarchical supervisor example and new guides (EN/JA)

## [0.5.3] - 2026-01-20

### Added
- **Runtime I/O Enforcement**: Detect contract-undeclared slice reads/writes (warn by default, raise in strict mode)
- **Config**: New `io` config section (`strict`, `warn`, `drop_undeclared_writes`)
- **Errors**: `ContractViolationError` for strict enforcement

### Changed
- **ModularNode**: Undeclared slice writes are dropped by default (with warning)

## [0.5.2] - 2026-01-19

### Added
- **CLI**: `visualize --graph-module/--graph-func` to render `LangGraph Node Flow` from an app-provided graph

### Changed
- **Metadata**: Mark project as Beta (PyPI trove classifier)
- **CLI**: `--module` import now auto-calls `register_all_nodes(...)` when present and no nodes were registered on import

### Fixed
- **Visualizer**: Improved LangGraph Mermaid rendering compatibility (`get_graph/draw_mermaid/to_mermaid`)
- **CLI**: Best-effort LangGraph flow rendering now connects all supervisors via an entrypoint node

## [0.5.1] - 2026-01-18

### Added
- **Runtime**: `StreamingRuntime.stream_with_graph()` now accepts `initial_state` for custom slices

## [0.5.0] - 2026-01-17

### Added
- **CLI**: New `agent-contracts` CLI with `validate`, `visualize`, and `diff` subcommands
- **Validation**: `ContractValidator(strict=True)` to escalate warnings into CI-failing errors
- **Contract Diff**: `diff_contracts()` and `NodeRegistry.export_contracts()` for stable contract comparisons
- **Examples**: New backend-oriented runtime example (`examples/05_backend_runtime.py`)
- **Docs**: New CLI docs and official Skills packs for building agents with `agent-contracts`

## [0.4.0] - 2026-01-14

### Breaking Changes
- **Registry**: `evaluate_triggers()` now returns `list[TriggerMatch]` instead of `list[tuple[int, str]]` ([#XXX])
  - `TriggerMatch` dataclass tracks which specific condition matched
  - Enables accurate condition explanation in supervisor routing
  - Migration: Update code using `evaluate_triggers()` directly (see docs)

- **Supervisor**: Explicit routing handler refactoring ([#XXX])
  - Removed hardcoded `if action == "answer"` logic from `GenericSupervisor._decide_with_trace()`
  - New `explicit_routing_handler` parameter for pluggable routing logic
  - Migration: Pass custom handler to `GenericSupervisor`:
    ```python
    def my_router(state: dict) -> str | None:
        if state.get("request", {}).get("action") == "answer":
            return state.get("interview", {}).get("last_question", {}).get("node_id")
        return None
    
    supervisor = GenericSupervisor(
        supervisor_name="main",
        llm=llm,
        explicit_routing_handler=my_router,
    )
    ```

- **Runtime**: Default `slices_to_restore` changed ([#XXX])
  - Before: `["_internal", "interview", "shopping"]`
  - After: `["_internal"]` only
  - Migration: Explicitly specify slices when creating runtime:
    ```python
    runtime = AgentRuntime(
        graph=graph,
        slices_to_restore=["_internal", "interview", "shopping"],
    )
    ```

- **Config**: `InterviewConfig` renamed to `FeatureConfig` ([#XXX])
  - `interview:` key in YAML changed to `features:`
  - `max_questions` field changed to `max_items`
  - Migration: Update YAML config and imports

### Added
- **Registry**: New `TriggerMatch` dataclass with `priority`, `node_name`, and `condition_index` fields
- **Supervisor**: New `ContextBuilderResult` TypedDict for better type safety
- **Supervisor**: New `ExplicitRoutingHandler` Protocol for custom routing logic
- **Contracts**: New `icon` field in `NodeContract` for custom visualization icons

### Fixed
- **Supervisor**: Fixed dead code issue - `_collect_context_slices()` is now properly used ([#XXX])
- **Supervisor**: Fixed type inconsistencies in `ContextBuilder` Protocol ([#XXX])
  - Added normalization to convert list to set for slices
  - Documented str/dict support for summary field
- **Supervisor**: Fixed incorrect condition explanation when multiple conditions have same priority ([#XXX])
  - Now uses actual matched condition instead of first found condition

### Changed
- **Visualizer**: Removed domain-specific icon patterns (`interview`, `like`, `card`)
  - Uses `NodeContract.icon` field for custom icons
  - Generic fallback patterns: `search`, `process`, `validate`, `notify`
- **Docs**: Updated all examples to use generic terminology
  - `interview` → `workflow`, `shopping` → `orders`, `card` → `notifications`

### Improved
- **Type Safety**: Better type hints and IDE support for ContextBuilder
- **Maintainability**: Eliminated code duplication in context collection
- **Accuracy**: More accurate routing explanations for LLM decision making
- **OSS Ready**: Library now domain-agnostic, ready for general use

### Documentation
- Added migration guide for v0.4.0 breaking changes
- Added implementation summary: `docs/supervisor_code_review_implementation.md`
- Updated `core_concepts.md`, `best_practices.md`, `troubleshooting.md` with generic examples

## [0.3.3] - 2026-01-14

### Added
- Added `max_field_length` parameter to `GenericSupervisor` for customizable field length limits in LLM prompts

### Changed
- Changed default string length limit in `GenericSupervisor._sanitize_for_llm()` from 1000 to 10000 characters
- Improved long string handling: preserves beginning instead of complete replacement, then trims remainder (e.g., `data[:10000] + "...[TRUNCATED:5000_chars]"`)
- Extended image data detection patterns: now also detects `image` format

### Fixed
- Fixed issue where base64 image data in `request` slice was included in Supervisor's LLM prompt, causing rapid token consumption increase
- Fixed issue where long text fields were completely lost (preserving beginning maintains Supervisor's decision accuracy)

## [0.3.2] - 2026-01-12

### Fixed

- **ContractVisualizer: Multiple trigger conditions support**
  - Fixed issue where nodes with multiple `TriggerCondition` entries only displayed the highest priority condition
  - `generate_trigger_hierarchy()` now displays all trigger conditions in priority order
  - First condition shows the node name, additional conditions use continuation symbol `↳`
  - Each condition displays its own priority, condition details, and LLM hint
  - Example output:
    ```markdown
    | Priority | Node | Condition | Hint |
    |:--------:|:-----|:----------|:-----|
    | 🔴 **100** | `action_handler` | `action=like` | Handle LIKE action |
    | 🟡 **90** | ↳ | `action=dislike` | Handle DISLIKE action |
    | 🟡 **80** | ↳ | `action=skip` | Handle SKIP action |
    ```

- **Mermaid diagram: Multiple trigger conditions visualization**
  - Updated priority chain diagrams to show all conditions as separate nodes
  - Each condition node displays: priority icon, priority value, node name, condition count (e.g., `[1/3]`), and condition details
  - Conditions are connected with "not matched" edges to show evaluation flow
  - Provides clear visualization of multi-condition routing logic

### Added

- **New helper method: `_format_single_condition()`**
  - Formats a single trigger condition for display
  - Supports both `when` and `when_not` conditions
  - Automatically truncates long conditions (shows first 3 items + count)
  - Handles edge cases: empty conditions display as `_(always)_`

### Improved

- **Test coverage**
  - Added 6 new test cases in `TestMultipleTriggerConditions` class
  - Tests cover: multiple conditions display, Mermaid diagram generation, single condition behavior, truncation, edge cases
  - All 292 tests pass

### Notes

- No breaking changes - fully backward compatible
- Existing architecture documents automatically benefit from enhanced detail
- `_summarize_conditions()` method is deprecated but still functional for backward compatibility

## [0.3.1] - 2026-01-12

### Added

- **Supervisor Factory Support in GraphBuilder**
  - New `supervisor_factory` parameter in `GraphBuilder.__init__()` and `build_graph_from_registry()`
  - Allows custom supervisor instance creation when using `llm_provider` for dynamic LLM injection
  - Enables `context_builder` to work with registry-based automatic graph generation
  - Signature: `supervisor_factory(name: str, llm: Any) -> GenericSupervisor`
  - Fully backward compatible - optional parameter with default None

### Improved

- **GenericSupervisor context_builder optimization**
  - Eliminated duplicate `context_builder` calls in `_decide_with_llm()`
  - Previously called twice: once in `_collect_context_slices()` and again for `summary`
  - Now calls once and reuses the result
  - Better performance and cleaner code structure

- **Flexible summary format support**
  - `context_builder` can now return `summary` as either `dict` or `str`
  - String format: Directly included in LLM prompt (ideal for formatted text)
  - Dict format: JSON-serialized before inclusion (preserves structure)
  - Prevents double-encoding of string summaries
  - Improves LLM readability for conversation history and formatted context

### Fixed

- **Registry-based graph generation with context_builder**
  - Fixed issue where `context_builder` was ignored when using `llm_provider` with `build_graph_from_registry()`
  - GraphBuilder was creating default GenericSupervisor instances without custom configurations
  - Now uses `supervisor_factory` to inject properly configured supervisors at runtime
  - Enables conversation-aware routing in production deployments using dependency injection

### Use Case

```python
from agent_contracts import build_graph_from_registry, GenericSupervisor

def my_context_builder(state, candidates):
    return {
        "slices": {"request", "response", "conversation"},
        "summary": f"Recent conversation:\n{format_messages(state)}"  # String format
    }

def supervisor_factory(name: str, llm):
    return GenericSupervisor(
        supervisor_name=name,
        llm=llm,
        context_builder=my_context_builder,  # Custom context now preserved!
    )

graph = build_graph_from_registry(
    llm_provider=get_llm,
    supervisor_factory=supervisor_factory,  # Inject custom supervisors
    supervisors=["card", "shopping"],
)
```

### Notes

- No breaking changes - fully backward compatible
- Fixes limitation where dynamic LLM injection prevented context_builder usage
- Essential for production scenarios using dependency injection patterns
- All existing tests pass

## [0.3.0] - 2026-01-12

### Added

- **Custom Context Builder for GenericSupervisor**
  - New `ContextBuilder` Protocol for type-safe context customization
  - `context_builder` parameter in `GenericSupervisor.__init__()`
  - Allows customization of which state slices and additional context are passed to LLM for routing decisions
  - Enables conversation-aware routing, business logic integration, and domain-specific decisions
  - Fully backward compatible - defaults to existing behavior when not provided

- **Enhanced LLM Context**
  - LLM can now receive additional context beyond base slices (request, response, _internal)
  - Support for "summary" dict to provide aggregated information (e.g., turn counts, readiness scores)
  - Better routing decisions for complex multi-agent scenarios

### Use Cases

- **E-commerce agents**: Include cart and inventory data for purchase-aware routing
- **Customer support**: Include ticket history and sentiment analysis
- **Education platforms**: Include learning progress and pace
- **Conversation agents**: Include chat history and turn counts for context-aware decisions

### Example

```python
def my_context_builder(state: dict, candidates: list[str]) -> dict:
    return {
        "slices": {"request", "response", "_internal", "conversation"},
        "summary": {
            "total_turns": len(state.get("conversation", {}).get("messages", [])),
            "readiness": 0.67
        }
    }

supervisor = GenericSupervisor(
    supervisor_name="shopping",
    llm=llm,
    context_builder=my_context_builder,
)
```

### Notes

- No breaking changes - fully backward compatible
- Default behavior unchanged when `context_builder` is not provided
- Comprehensive test coverage added (5 new tests in `test_supervisor_context_builder.py`)
- All existing tests pass (11 tests in `test_supervisor.py`)

## [0.2.3] - 2026-01-11

### Changed

- **GenericSupervisor context optimization** (BREAKING BEHAVIOR CHANGE)
  - `_collect_context_slices()` now returns minimal context: `{"request", "response", "_internal"}`
  - Previously included all candidate nodes' `reads` slices
  - **Rationale**: Candidate slices are already evaluated in trigger conditions, passing them to LLM is redundant
  - **Benefits**:
    - Significant token reduction (fewer slices sent to LLM)
    - Clearer responsibility separation: Triggers = rule-based filtering, LLM = final selection
    - Better performance (less data to summarize and transmit)
    - Maintains conversation context via `response` for better LLM understanding
  - **Impact**: LLM routing decisions based on user request, previous response, and internal state
  - Updated 2 test cases to reflect new minimal context behavior
  - No API changes - internal implementation optimization

### Removed

- **StateSummarizer completely removed** (BREAKING API CHANGE)
  - Removed `agent_contracts.utils.summarizer` module entirely
  - Removed `StateSummarizer` class and `summarize_state_slice()` function
  - Removed 22 test cases in `test_summarizer.py`
  - Removed from `agent_contracts.utils.__all__` exports
  - **Rationale**: Not used anywhere in the codebase after supervisor optimization
  - **Migration**: If you were using StateSummarizer, use `json.dumps()` instead:
    ```python
    # Before
    from agent_contracts.utils import StateSummarizer
    summarizer = StateSummarizer()
    summary = summarizer.summarize(data)
    
    # After
    import json
    summary = json.dumps(data, ensure_ascii=False, default=str)
    ```

- **StateSummarizer removed from GenericSupervisor**
  - Removed `_summarize_slice()` method - now uses direct JSON serialization
  - Removed `summarizer` parameter from `__init__()`
  - **Rationale**: `request`, `response`, `_internal` are small slices that don't need summarization
  - **Benefits**:
    - Simpler implementation (no summarization overhead)
    - No information loss (full data preserved)
    - Faster execution (direct JSON serialization)
    - Easier debugging (actual data visible in prompts)
  - Uses `json.dumps()` with `ensure_ascii=False` and `default=str` for robust serialization

### Notes

- This change clarifies the supervisor's role: making routing decisions based on:
  - User intent (`request`)
  - Conversation flow (`response`)
  - Execution state (`_internal`)
- Other state slices (e.g., `interview`, `profile_card`) are already evaluated in trigger conditions and don't need to be re-evaluated by LLM
- If specific state is needed for routing, it should be added to trigger conditions, not passed to LLM

## [0.2.2] - 2026-01-11

### Added

- **StateSummarizer utility class**
  - New `agent_contracts.utils.summarizer` module for intelligent state slice summarization
  - Recursive summarization preserves nested structure while limiting size
  - Configurable depth limiting (default: 2 levels)
  - Configurable item count limiting for dicts and lists
  - Handles complex nested structures (dicts in lists, lists in dicts, etc.)
  - **Cycle detection**: Prevents infinite recursion on circular references using `id()`-based tracking
  - Convenience function `summarize_state_slice()` for quick usage
  - Comprehensive test suite with 22 test cases (including 7 cycle detection tests)

### Improved

- **GenericSupervisor context enrichment**
  - LLM now receives richer context based on candidate nodes' contracts
  - Automatically includes base slices (`request`, `response`, `_internal`)
  - Dynamically adds slices that candidate nodes read from (via `NodeContract.reads`)
  - Improves routing accuracy by providing relevant state information
  - New methods: `_collect_context_slices()`, `_summarize_slice()`
  - **Flexible summarizer configuration**: Accept `StateSummarizer` instance via constructor
  - No breaking changes - internal implementation only
  - Added 5 new test cases for context building verification

- **GenericSupervisor context summarization**
  - Now uses `StateSummarizer` for recursive state slice summarization
  - Better preservation of nested data structure information
  - Previously, nested lists and dicts lost all detail beyond first level
  - Now shows hierarchical structure with controlled depth and item counts
  - Improves LLM context quality without breaking existing functionality
  - No API changes - internal implementation enhancement only

- **Prompt structure improvement**
  - `NodeRegistry.build_llm_prompt()` now accepts optional `context` parameter
  - When context is provided, it's automatically integrated into the prompt template
  - Cleaner separation of concerns: registry handles prompt structure, supervisor provides context
  - Backward compatible: `context=None` by default
  - Simplifies supervisor code by delegating prompt+context merging to registry

- **Flexible StateSummarizer configuration**
  - `GenericSupervisor.__init__()` now accepts optional `summarizer` parameter
  - Pass a custom `StateSummarizer` instance for full control over summarization behavior
  - If omitted, creates a default instance with sensible defaults
  - Most flexible approach: allows complete customization while maintaining simplicity
  - Backward compatible: `summarizer=None` by default

## [0.2.1] - 2026-01-09

### Improved

- **GenericSupervisor match reason display**
  - LLM context now includes WHY each rule candidate matched
  - Format: `- node_name (P95): matched because request.field=value`
  - Enables LLM to make more informed routing decisions
  - No API changes required

## [0.2.0] - 2026-01-08

### Added

- **StateAccessor pattern** for type-safe, immutable state access
  - `StateAccessor[T]` generic class with `get()`, `set()`, and `update()` methods
  - Standard accessors: `Internal`, `Request`, `Response`
  - Convenience functions: `reset_response()`, `increment_turn()`, `set_error()`, `clear_error()`
  - All operations are immutable (return new state, never mutate)
  - Full test coverage (26 tests)

- **Runtime layer** for agent execution
  - `AgentRuntime`: Unified execution engine with lifecycle hooks
  - `RequestContext` / `ExecutionResult`: Typed I/O containers
  - `RuntimeHooks` Protocol: Customization points for app-specific logic
  - `SessionStore` Protocol + `InMemorySessionStore`: Session persistence abstraction
  - Full test coverage (23 tests)

- **State operations helpers**
  - `ensure_slices()`: Ensure slices exist in state
  - `merge_session()`: Merge session data into state
  - `reset_internal_flags()`: Reset internal flags with keyword args
  - `create_base_state()`: Create minimal initial state
  - `update_slice()`, `copy_slice()`, `get_nested()`: Utility functions
  - Full test coverage (28 tests)

- **Streaming execution**
  - `StreamingRuntime`: Node-by-node streaming execution for SSE
  - `StreamEvent` / `StreamEventType`: Typed streaming events
  - `NodeExecutor`: Node wrapper for streaming pipelines
  - LangGraph `astream()` integration via `stream_with_graph()`
  - Helper functions: `create_status_event()`, `create_progress_event()`, `create_data_event()`
  - Full test coverage (16 tests)

### Migration Guide (Phase 5)

Applications can adopt the new runtime layer by:

1. Implement `SessionStore` protocol for your database (e.g., `PostgresSessionStore`)
2. Implement `RuntimeHooks` protocol for app-specific state processing
3. Use `AgentRuntime` or `StreamingRuntime` instead of direct graph execution
4. Replace direct state manipulation with `StateAccessor` pattern

## [0.1.0] - 2026-01-06

### Added

- Initial release
- `NodeContract` for declarative node I/O contracts
- `ModularNode` and `InteractiveNode` base classes
- `NodeRegistry` for node registration and discovery
- `GenericSupervisor` for LLM-driven routing with rule hints
- `GraphBuilder` for automatic LangGraph construction
- `BaseAgentState` and slice definitions
- `ContractVisualizer` for architecture documentation
- `ContractValidator` for static contract validation
- LangSmith observability integration
