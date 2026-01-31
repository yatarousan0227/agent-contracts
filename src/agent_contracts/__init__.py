"""agent_contracts - Modular node architecture for LangGraph agents.

This package provides:
- NodeContract: Declarative I/O contracts for nodes
- ModularNode: Base class for LangGraph nodes
- InteractiveNode: Base class for conversational nodes
- NodeRegistry: Registration and routing
- GenericSupervisor: LLM-driven routing with rule hints
- GraphBuilder: Automatic LangGraph construction
"""

from agent_contracts.contracts import (
    NodeContract,
    TriggerCondition,
    NodeInputs,
    NodeOutputs,
)
from agent_contracts.node import ModularNode, InteractiveNode
from agent_contracts.registry import NodeRegistry, TriggerMatch, get_node_registry, reset_registry
from agent_contracts.supervisor import (
    GenericSupervisor,
    SupervisorDecision,
)
from agent_contracts.routing import (
    RoutingDecision,
    RoutingReason,
    MatchedRule,
)
from agent_contracts.subgraph import (
    SubgraphContract,
    SubgraphDefinition,
)
from agent_contracts.graph_builder import GraphBuilder, build_graph_from_registry
from agent_contracts.state import (
    BaseAgentState,
    BaseRequestSlice,
    BaseResponseSlice,
    BaseInternalSlice,
    get_slice,
    merge_slice_updates,
)
from agent_contracts.state_accessors import (
    StateAccessor,
    Internal,
    Request,
    Response,
    reset_response,
    increment_turn,
    set_error,
    clear_error,
)
from agent_contracts.router import BaseActionRouter
from agent_contracts.visualizer import ContractVisualizer
from agent_contracts.validator import ContractValidator, ValidationResult
from agent_contracts.contract_diff import ContractDiffReport, NodeChange, diff_contracts
from agent_contracts.errors import ContractViolationError
from agent_contracts.runtime import (
    RequestContext,
    ExecutionResult,
    RuntimeHooks,
    DefaultHooks,
    SessionStore,
    InMemorySessionStore,
    AgentRuntime,
    Budgets,
    CallStackFrame,
    DecisionTraceItem,
)

__version__ = "0.6.0"

__all__ = [
    # Version
    "__version__",
    # Contracts
    "NodeContract",
    "TriggerCondition",
    "NodeInputs",
    "NodeOutputs",
    # Nodes
    "ModularNode",
    "InteractiveNode",
    # Registry
    "NodeRegistry",
    "TriggerMatch",
    "get_node_registry",
    "reset_registry",
    # Supervisor
    "GenericSupervisor",
    "SupervisorDecision",
    # Routing (Traceable)
    "RoutingDecision",
    "RoutingReason",
    "MatchedRule",
    # Subgraphs
    "SubgraphContract",
    "SubgraphDefinition",
    # Graph
    "GraphBuilder",
    "build_graph_from_registry",
    # State
    "BaseAgentState",
    "BaseRequestSlice",
    "BaseResponseSlice",
    "BaseInternalSlice",
    "get_slice",
    "merge_slice_updates",
    # State Accessors
    "StateAccessor",
    "Internal",
    "Request",
    "Response",
    "reset_response",
    "increment_turn",
    "set_error",
    "clear_error",
    # Router
    "BaseActionRouter",
    # Visualizer
    "ContractVisualizer",
    # Validator
    "ContractValidator",
    "ValidationResult",
    # Contract Diff
    "ContractDiffReport",
    "NodeChange",
    "diff_contracts",
    # Errors
    "ContractViolationError",
    # Runtime
    "RequestContext",
    "ExecutionResult",
    "RuntimeHooks",
    "DefaultHooks",
    "SessionStore",
    "InMemorySessionStore",
    "AgentRuntime",
    # Hierarchical Runtime Types
    "Budgets",
    "CallStackFrame",
    "DecisionTraceItem",
]
