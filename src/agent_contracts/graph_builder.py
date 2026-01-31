"""GraphBuilder - Registry-based graph construction.

Reads registered nodes from NodeRegistry and
automatically builds LangGraph StateGraph.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Optional
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, END

from agent_contracts.registry import NodeRegistry, get_node_registry
from agent_contracts.supervisor import GenericSupervisor
from agent_contracts.state import apply_slice_updates, merge_slice_updates
from agent_contracts.contracts import NodeContract
from agent_contracts.config import get_config
from agent_contracts.runtime.hierarchy import Budgets, DecisionTraceItem
from agent_contracts.utils.logging import get_logger

logger = get_logger("agent_contracts.graph_builder")


class GraphBuilder:
    """Build LangGraph graphs from a NodeRegistry.

    Args:
        - registry: Optional NodeRegistry to use.
        - state_class: Optional state type for the graph.
        - llm_provider: Callable providing LLM instances.
        - dependency_provider: Callable returning services for a NodeContract.
        - supervisor_factory: Callable creating supervisors for name/llm.
        - llm: Optional default LLM for pre-instantiated nodes/supervisors.
        - enable_subgraphs: Whether to include CallSubgraph nodes.
        - supervisor_allowlists: Optional per-supervisor allowlists.
        - node_allowlist: Optional node allowlist (primarily for subgraphs).
        - services: Default services injected into nodes.
    Returns:
        - GraphBuilder instance.
    """

    def _return_state(self, state: dict, updates: dict[str, Any] | None) -> dict:
        """Return a LangGraph-compatible state update.

        LangGraph's behavior differs depending on the `StateGraph` schema:
        - For `StateGraph(dict)`, a node return value is treated as the *full* state.
        - For typed state schemas (e.g., TypedDict), node returns are treated as *partial* updates.

        agent-contracts wrappers internally operate on slice-level updates. This helper
        adapts return semantics so examples and apps work in both modes.
        """
        if self.state_class is None or self.state_class is dict:
            return apply_slice_updates(state, updates)
        return merge_slice_updates(state, updates)
    
    def __init__(
        self,
        registry: NodeRegistry | None = None,
        state_class: type | None = None,
        llm_provider: Callable[[], Any] | None = None,
        dependency_provider: Callable[[NodeContract], dict] | None = None,
        supervisor_factory: Callable[[str, Any], GenericSupervisor] | None = None,
        llm: Any | None = None,
        enable_subgraphs: bool = False,
        supervisor_allowlists: dict[str, set[str]] | None = None,
        node_allowlist: set[str] | None = None,
        services: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the graph builder.

        Args:
            - registry: Node registry.
            - state_class: State type (uses dict if not provided).
            - llm_provider: Function that provides LLM instances.
            - dependency_provider: Function that provides dependencies for nodes.
            - supervisor_factory: Function that creates supervisor instances.
            - llm: Default LLM instance for pre-instantiated nodes/supervisors.
            - enable_subgraphs: Whether to include CallSubgraph nodes.
            - supervisor_allowlists: Optional per-supervisor allowlists.
            - node_allowlist: Optional node allowlist for filtering nodes.
            - services: Default services injected into nodes.
        Returns:
            - None.
        """
        self.registry = registry or get_node_registry()
        self.state_class = state_class
        self.supervisor_names: set[str] = set()
        self.supervisor_instances: dict[str, GenericSupervisor] = {}
        self.node_classes: dict[str, type] = {}
        self.node_instances: dict[str, Any] = {}
        self.llm_provider = llm_provider
        self.dependency_provider = dependency_provider
        self.supervisor_factory = supervisor_factory
        self.default_llm = llm
        self.enable_subgraphs = enable_subgraphs
        self.supervisor_allowlists = supervisor_allowlists or {}
        self.node_allowlist = node_allowlist
        self.services = services or {}
        self.subgraph_cache: dict[str, Any] = {}
        self.subgraph_decision_prefix = "call_subgraph::"
        self.subgraph_node_prefix = "call_subgraph__"
        self.logger = logger
    
    def add_supervisor(
        self,
        name: str,
        llm: Any | None = None,
        **services: Any,
    ) -> "GraphBuilder":
        """Add a supervisor and its related nodes.

        Args:
            - name: Supervisor name.
            - llm: Optional LLM instance for node creation.
            - **services: Services to inject into node instances.
        Returns:
            - Self for fluent chaining.
        """
        if llm is None:
            llm = self.default_llm
        self.supervisor_names.add(name)
        if self.llm_provider is None:
            supervisor = GenericSupervisor(
                supervisor_name=name,
                llm=llm,
                registry=self.registry,
            )
            self.supervisor_instances[name] = supervisor
        
        combined_services = {**self.services, **services}

        # Create related node instances
        for node_name in self.registry.get_supervisor_nodes(name):
            if self.node_allowlist is not None and node_name not in self.node_allowlist:
                continue
            node_cls = self.registry.get_node_class(node_name)
            if node_cls is None:
                continue
            self.node_classes[node_name] = node_cls
            if self.dependency_provider is None and self.llm_provider is None:
                instance = node_cls(llm=llm, **combined_services)
                self.node_instances[node_name] = instance
        
        self.logger.info(
            f"Added supervisor: {name} ({len(self.registry.get_supervisor_nodes(name))} nodes)"
        )
        
        return self
    
    def build_routing_map(self, supervisor_name: str) -> dict[str, str]:
        """Generate a routing map for a supervisor.

        Args:
            - supervisor_name: Supervisor name.
        Returns:
            - Mapping of node names and "done" to routing targets.
        """
        routing = {
            name: name
            for name, node_cls in self.node_classes.items()
            if node_cls.CONTRACT.supervisor == supervisor_name
        }
        if self.enable_subgraphs:
            for subgraph_id in self.registry.list_subgraphs():
                decision = self._call_subgraph_decision_name(subgraph_id)
                node_name = self._call_subgraph_node_name(subgraph_id)
                routing[decision] = node_name
        routing["done"] = END  # LangGraph END constant
        return routing

    def _call_subgraph_decision_name(self, subgraph_id: str) -> str:
        return f"{self.subgraph_decision_prefix}{subgraph_id}"

    def _call_subgraph_node_name(self, subgraph_id: str) -> str:
        return f"{self.subgraph_node_prefix}{subgraph_id}"

    def _list_call_subgraph_nodes(self) -> list[str]:
        return [
            self._call_subgraph_node_name(subgraph_id)
            for subgraph_id in self.registry.list_subgraphs()
        ]

    def _list_call_subgraph_decisions(self) -> list[str]:
        return [
            self._call_subgraph_decision_name(subgraph_id)
            for subgraph_id in self.registry.list_subgraphs()
        ]

    def _get_internal(self, state: dict) -> dict:
        internal = state.get("_internal", {})
        if not isinstance(internal, dict):
            return {}
        return internal

    def _increment_step(self, internal: dict) -> tuple[dict, int]:
        step_count = internal.get("step_count", 0)
        try:
            step_count = int(step_count)
        except (TypeError, ValueError):
            step_count = 0
        step_count += 1
        return {**internal, "step_count": step_count}, step_count

    def _normalize_budgets(self, internal: dict) -> tuple[dict, Budgets]:
        raw = internal.get("budgets")
        if isinstance(raw, Budgets):
            budgets = raw
        elif isinstance(raw, dict):
            budgets = Budgets(
                max_depth=int(raw.get("max_depth", Budgets().max_depth)),
                max_steps=int(raw.get("max_steps", Budgets().max_steps)),
                max_reentry=int(raw.get("max_reentry", Budgets().max_reentry)),
            )
        else:
            budgets = Budgets()
        internal = {**internal, "budgets": asdict(budgets)}
        return internal, budgets

    def _current_depth(self, internal: dict) -> int:
        call_stack = internal.get("call_stack")
        if not isinstance(call_stack, list):
            return 0
        return len(call_stack)

    def _append_decision_trace(
        self,
        internal: dict,
        *,
        step: int,
        depth: int,
        supervisor: str | None,
        decision_kind: str,
        target: str | None,
        reason: str | None = None,
        termination_reason: str | None = None,
    ) -> dict:
        trace = internal.get("decision_trace")
        if not isinstance(trace, list):
            trace = []
        item = DecisionTraceItem(
            step=step,
            depth=depth,
            supervisor=supervisor,
            decision_kind=decision_kind,
            target=target,
            reason=reason,
            termination_reason=termination_reason,
        )
        trace = [*trace, asdict(item)]
        return {**internal, "decision_trace": trace}

    def _decision_kind_for_supervisor(
        self,
        decision: str | None,
        depth: int,
        response_type: str | None,
    ) -> str:
        config = get_config()
        terminal_types = set(config.supervisor.terminal_response_types)
        if response_type in terminal_types:
            return "STOP_GLOBAL"
        if decision == "done":
            return "STOP_LOCAL" if depth > 0 else "STOP_GLOBAL"
        if isinstance(decision, str) and decision.startswith(self.subgraph_decision_prefix):
            return "SUBGRAPH"
        if decision is None:
            return "FALLBACK"
        return "NODE"

    def _get_allowlist(
        self,
        supervisor_name: str,
        supervisor_instance: Any | None,
    ) -> set[str] | None:
        if supervisor_instance is not None:
            allowlist = getattr(supervisor_instance, "allowlist", None)
            if allowlist:
                return set(allowlist)
        if supervisor_name in self.supervisor_allowlists:
            return set(self.supervisor_allowlists[supervisor_name])
        return None

    def _is_decision_allowed(self, decision: str, allowlist: set[str]) -> bool:
        if decision == "done":
            return True
        if decision in allowlist:
            return True
        if decision.startswith(self.subgraph_decision_prefix):
            subgraph_id = decision[len(self.subgraph_decision_prefix):]
            if subgraph_id in allowlist:
                return True
        return False

    def _build_terminal_response(self, state: dict, reason: str) -> dict:
        response = state.get("response", {})
        if not isinstance(response, dict):
            response = {}
        return {
            **response,
            "response_type": "terminal",
            "response_message": reason,
        }

    def create_node_wrapper(self, node_name: str) -> Callable:
        """Create a LangGraph-compatible node wrapper.

        Args:
            - node_name: Node name to wrap.
        Returns:
            - Async callable for LangGraph execution.
        """
        node_cls = self.node_classes.get(node_name)
        instance = self.node_instances.get(node_name)
        
        async def wrapper(state: dict, config: Optional[RunnableConfig] = None) -> dict:
            if node_cls is None:
                self.logger.error(f"Node class not found: {node_name}")
                return {}

            internal = self._get_internal(state)
            if self.enable_subgraphs:
                internal, _ = self._increment_step(internal)

            if self.dependency_provider or self.llm_provider:
                contract = node_cls.CONTRACT
                services = self.dependency_provider(contract) if self.dependency_provider else {}
                llm = self.llm_provider() if (self.llm_provider and contract.requires_llm) else None
                node = node_cls(llm=llm, **services)
                updates = await node(state, config=config)
            else:
                if instance is None:
                    self.logger.error(f"Node instance not found: {node_name}")
                    return {}
                updates = await instance(state, config=config)
            if self.enable_subgraphs:
                internal_updates = {}
                if updates and isinstance(updates.get("_internal"), dict):
                    internal_updates = updates.get("_internal", {})
                updates = {
                    **(updates or {}),
                    "_internal": {
                        **internal,
                        **internal_updates,
                        "step_count": internal.get("step_count", 0),
                    },
                }
            return self._return_state(state, updates)
        
        wrapper.__name__ = f"{node_name}_node"
        return wrapper
    
    def create_supervisor_wrapper(self, supervisor_name: str) -> Callable:
        """Create a LangGraph-compatible supervisor wrapper.

        Args:
            - supervisor_name: Supervisor name to wrap.
        Returns:
            - Async callable for LangGraph execution.
        """
        supervisor = self.supervisor_instances.get(supervisor_name)

        async def wrapper(state: dict, config: Optional[RunnableConfig] = None) -> dict:
            internal = self._get_internal(state)
            step_count = internal.get("step_count", 0)
            if self.enable_subgraphs:
                internal, step_count = self._increment_step(internal)
            if self.llm_provider:
                llm = self.llm_provider()
                # Use custom supervisor_factory if provided, otherwise create default
                if self.supervisor_factory:
                    current = self.supervisor_factory(supervisor_name, llm)
                else:
                    current = GenericSupervisor(
                        supervisor_name=supervisor_name,
                        llm=llm,
                        registry=self.registry,
                    )
                updates = await current.run(state, config=config)
            else:
                if supervisor is None:
                    self.logger.error(f"Supervisor not found: {supervisor_name}")
                    return {}
                updates = await supervisor.run(state, config=config)
                current = supervisor

            if self.enable_subgraphs:
                internal_updates = {}
                if updates and isinstance(updates.get("_internal"), dict):
                    internal_updates = updates.get("_internal", {})
                combined_internal = {
                    **internal,
                    **internal_updates,
                    "step_count": internal.get("step_count", 0),
                }
                combined_internal["last_supervisor"] = supervisor_name

                decision = combined_internal.get("decision")
                target = None
                if isinstance(decision, str):
                    if decision.startswith(self.subgraph_decision_prefix):
                        target = decision[len(self.subgraph_decision_prefix):]
                    else:
                        target = decision
                allowlist = self._get_allowlist(supervisor_name, current)
                if allowlist and isinstance(decision, str) and not self._is_decision_allowed(
                    decision, allowlist
                ):
                    depth = self._current_depth(combined_internal)
                    combined_internal = {
                        **combined_internal,
                        "decision": "done",
                    }
                    combined_internal = self._append_decision_trace(
                        combined_internal,
                        step=step_count,
                        depth=depth,
                        supervisor=supervisor_name,
                        decision_kind="STOP_GLOBAL",
                        target=target,
                        termination_reason="allowlist_violation",
                    )
                    response = self._build_terminal_response(
                        state, "allowlist_violation"
                    )
                    updates = {
                        "_internal": combined_internal,
                        "response": response,
                    }
                    return self._return_state(state, updates)

                depth = self._current_depth(combined_internal)
                response = state.get("response", {})
                response_type = None
                if isinstance(response, dict):
                    response_type = response.get("response_type")
                decision_kind = self._decision_kind_for_supervisor(
                    decision,
                    depth,
                    response_type,
                )
                combined_internal = self._append_decision_trace(
                    combined_internal,
                    step=step_count,
                    depth=depth,
                    supervisor=supervisor_name,
                    decision_kind=decision_kind,
                    target=target,
                )
                updates = {
                    **(updates or {}),
                    "_internal": combined_internal,
                }
                if "response" not in updates:
                    response = state.get("response")
                    if isinstance(response, dict):
                        updates["response"] = response
            return self._return_state(state, updates)
        
        wrapper.__name__ = f"{supervisor_name}_supervisor"
        return wrapper

    def _resolve_subgraph_members(
        self,
        subgraph_id: str,
    ) -> tuple[list[str], set[str] | None, str]:
        subgraph = self.registry.get_subgraph(subgraph_id)
        if subgraph is None:
            raise ValueError(f"Subgraph not found: {subgraph_id}")
        contract, definition = subgraph

        supervisors = set(definition.supervisors or [])
        node_names = set(definition.nodes or [])

        if contract.entrypoint in self.registry.get_all_nodes():
            node_names.add(contract.entrypoint)
        else:
            supervisors.add(contract.entrypoint)

        for node_name in node_names:
            node_contract = self.registry.get_contract(node_name)
            if node_contract:
                supervisors.add(node_contract.supervisor)

        node_allowlist = node_names if definition.nodes is not None else None
        return sorted(supervisors), node_allowlist, contract.entrypoint

    def _build_subgraph_graph(self, subgraph_id: str) -> StateGraph:
        supervisors, node_allowlist, entrypoint = self._resolve_subgraph_members(subgraph_id)
        if not supervisors:
            raise ValueError(f"Subgraph has no supervisors: {subgraph_id}")

        graph = build_graph_from_registry(
            registry=self.registry,
            llm=self.default_llm,
            llm_provider=self.llm_provider,
            dependency_provider=self.dependency_provider,
            supervisor_factory=self.supervisor_factory,
            supervisors=supervisors,
            state_class=self.state_class,
            enable_subgraphs=self.enable_subgraphs,
            supervisor_allowlists=self.supervisor_allowlists,
            node_allowlist=node_allowlist,
            **self.services,
        )

        entry_node = None
        if entrypoint in graph.nodes:
            entry_node = entrypoint
        elif f"{entrypoint}_supervisor" in graph.nodes:
            entry_node = f"{entrypoint}_supervisor"
        elif entrypoint.endswith("_supervisor") and entrypoint in graph.nodes:
            entry_node = entrypoint

        if entry_node is None:
            raise ValueError(
                f"Subgraph entrypoint not found: {entrypoint} (subgraph={subgraph_id})"
            )

        graph.set_entry_point(entry_node)
        return graph

    def _get_compiled_subgraph(self, subgraph_id: str) -> Any:
        cached = self.subgraph_cache.get(subgraph_id)
        if cached is not None:
            return cached
        graph = self._build_subgraph_graph(subgraph_id)
        compiled = graph.compile()
        self.subgraph_cache[subgraph_id] = compiled
        return compiled

    def create_call_subgraph_wrapper(self, subgraph_id: str) -> Callable:
        """Create a LangGraph-compatible CallSubgraph node wrapper."""
        node_name = self._call_subgraph_node_name(subgraph_id)

        async def wrapper(state: dict, config: Optional[RunnableConfig] = None) -> dict:
            internal = self._get_internal(state)
            if not self.enable_subgraphs:
                self.logger.error("CallSubgraph invoked without subgraph support enabled")
                return {}

            internal, step_count = self._increment_step(internal)
            internal, budgets = self._normalize_budgets(internal)

            call_stack = internal.get("call_stack", [])
            if not isinstance(call_stack, list):
                call_stack = []
            visited = internal.get("visited_subgraphs", {})
            if not isinstance(visited, dict):
                visited = {}

            parent_supervisor = internal.get("last_supervisor")
            depth = len(call_stack) + 1
            visit_count = visited.get(subgraph_id, 0) + 1

            if step_count > budgets.max_steps:
                internal = {**internal, "return_to_supervisor": parent_supervisor}
                internal = self._append_decision_trace(
                    internal,
                    step=step_count,
                    depth=len(call_stack),
                    supervisor=parent_supervisor if isinstance(parent_supervisor, str) else None,
                    decision_kind="STOP_GLOBAL",
                    target=subgraph_id,
                    termination_reason="max_steps_exceeded",
                )
                updates = {
                    "_internal": {**internal, "decision": "done"},
                    "response": self._build_terminal_response(
                        state, "max_steps_exceeded"
                    ),
                }
                return self._return_state(state, updates)

            if depth > budgets.max_depth:
                internal = {**internal, "return_to_supervisor": parent_supervisor}
                internal = self._append_decision_trace(
                    internal,
                    step=step_count,
                    depth=len(call_stack),
                    supervisor=parent_supervisor if isinstance(parent_supervisor, str) else None,
                    decision_kind="STOP_GLOBAL",
                    target=subgraph_id,
                    termination_reason="max_depth_exceeded",
                )
                updates = {
                    "_internal": {**internal, "decision": "done"},
                    "response": self._build_terminal_response(
                        state, "max_depth_exceeded"
                    ),
                }
                return self._return_state(state, updates)

            if visit_count > budgets.max_reentry:
                internal = {**internal, "return_to_supervisor": parent_supervisor}
                internal = self._append_decision_trace(
                    internal,
                    step=step_count,
                    depth=len(call_stack),
                    supervisor=parent_supervisor if isinstance(parent_supervisor, str) else None,
                    decision_kind="STOP_GLOBAL",
                    target=subgraph_id,
                    termination_reason="cycle_detected",
                )
                updates = {
                    "_internal": {**internal, "decision": "done"},
                    "response": self._build_terminal_response(
                        state, "cycle_detected"
                    ),
                }
                return self._return_state(state, updates)

            frame = {
                "subgraph_id": subgraph_id,
                "depth": depth,
                "entry_step": step_count,
                "locals": {
                    "parent_supervisor": parent_supervisor,
                },
            }
            call_stack = [*call_stack, frame]
            visited = {**visited, subgraph_id: visit_count}
            internal = {
                **internal,
                "call_stack": call_stack,
                "visited_subgraphs": visited,
            }

            child_state = {**state, "_internal": internal}
            compiled = self._get_compiled_subgraph(subgraph_id)
            child_result = await compiled.ainvoke(child_state, config=config)
            if not isinstance(child_result, dict):
                return {}

            child_internal = child_result.get("_internal", {})
            if not isinstance(child_internal, dict):
                child_internal = {}

            child_stack = child_internal.get("call_stack", [])
            if not isinstance(child_stack, list):
                child_stack = []
            popped = None
            if child_stack:
                popped = child_stack[-1]
                child_stack = child_stack[:-1]

            return_to = None
            if isinstance(popped, dict):
                locals_data = popped.get("locals", {})
                if isinstance(locals_data, dict):
                    return_to = locals_data.get("parent_supervisor")
            if return_to is None:
                return_to = parent_supervisor

            child_internal = {
                **child_internal,
                "call_stack": child_stack,
            }
            if isinstance(return_to, str):
                child_internal["return_to_supervisor"] = return_to

            child_result["_internal"] = child_internal
            return self._return_state(state, child_result)

        wrapper.__name__ = f"{node_name}_node"
        return wrapper

    def create_call_subgraph_return_router(self) -> Callable:
        """Route back to the supervisor that initiated the subgraph."""
        def route(state: dict) -> str:
            internal = state.get("_internal", {})
            if not isinstance(internal, dict):
                return END
            return_to = internal.get("return_to_supervisor")
            if isinstance(return_to, str):
                return f"{return_to}_supervisor"
            return END

        route.__name__ = "route_after_call_subgraph"
        return route
    
    def create_routing_function(self, supervisor_name: str) -> Callable:
        """Create a routing function for post-supervisor routing.

        Args:
            - supervisor_name: Supervisor name for routing context.
        Returns:
            - Routing function returning the next node name.
        """
        valid_nodes = {
            name
            for name, node_cls in self.node_classes.items()
            if node_cls.CONTRACT.supervisor == supervisor_name
        }
        if self.enable_subgraphs:
            valid_nodes.update(self._list_call_subgraph_decisions())
        
        # Get terminal types from config
        config = get_config()
        terminal_types = set(config.supervisor.terminal_response_types)
        
        def route(state: dict) -> str:
            # First check response_type (termination signal from node)
            response = state.get("response", {})
            response_type = response.get("response_type")
            if response_type in terminal_types:
                return "done"
            
            # Then check decision
            internal = state.get("_internal", {})
            decision = internal.get("decision", "done")
            if decision in valid_nodes:
                return decision
            return "done"
        
        route.__name__ = f"route_after_{supervisor_name}_supervisor"
        return route


def build_graph_from_registry(
    registry: NodeRegistry | None = None,
    llm: Any | None = None,
    llm_provider: Callable[[], Any] | None = None,
    dependency_provider: Callable[[NodeContract], dict] | None = None,
    supervisor_factory: Callable[[str, Any], GenericSupervisor] | None = None,
    entrypoint: tuple[str, Callable, Callable] | None = None,
    supervisors: list[str] | None = None,
    state_class: type | None = None,
    enable_subgraphs: bool = False,
    supervisor_allowlists: dict[str, set[str]] | None = None,
    node_allowlist: set[str] | None = None,
    **services: Any,
) -> StateGraph:
    """Build a LangGraph StateGraph from a registry.

    Args:
        - registry: Node registry to read from.
        - llm: LLM instance for supervisor/node creation.
        - llm_provider: Callable providing LLM instances.
        - dependency_provider: Callable providing services for nodes.
        - supervisor_factory: Callable creating supervisors.
        - entrypoint: Optional entry node tuple (name, node_func, route_func).
        - supervisors: Supervisor names to add.
        - state_class: State class for the StateGraph.
        - enable_subgraphs: Whether to include CallSubgraph nodes.
        - supervisor_allowlists: Optional per-supervisor allowlists.
        - node_allowlist: Optional node allowlist (primarily for subgraphs).
        - **services: Services to inject into nodes.
    Returns:
        - Uncompiled StateGraph instance.
    """
    reg = registry or get_node_registry()
    builder = GraphBuilder(
        registry=reg,
        state_class=state_class,
        llm_provider=llm_provider,
        dependency_provider=dependency_provider,
        supervisor_factory=supervisor_factory,
        llm=llm,
        enable_subgraphs=enable_subgraphs,
        supervisor_allowlists=supervisor_allowlists,
        node_allowlist=node_allowlist,
        services=services,
    )

    if enable_subgraphs:
        for node_name in reg.get_all_nodes():
            if node_name.startswith(builder.subgraph_node_prefix):
                raise ValueError(
                    f"Node name uses reserved prefix '{builder.subgraph_node_prefix}': {node_name}"
                )
            if node_name.startswith(builder.subgraph_decision_prefix):
                raise ValueError(
                    f"Node name uses reserved prefix '{builder.subgraph_decision_prefix}': {node_name}"
                )
        for subgraph_id in reg.list_subgraphs():
            node_name = builder._call_subgraph_node_name(subgraph_id)
            if node_name in reg.get_all_nodes():
                raise ValueError(
                    f"Node name conflicts with generated CallSubgraph node: {node_name}"
                )
    
    # Add supervisors
    supervisor_list = supervisors or []
    for sup_name in supervisor_list:
        builder.add_supervisor(sup_name, llm=llm, **services)
    
    # Create StateGraph
    state_cls = state_class or dict
    graph = StateGraph(state_cls)
    
    # Add Supervisor nodes
    for sup_name in builder.supervisor_names:
        graph.add_node(f"{sup_name}_supervisor", builder.create_supervisor_wrapper(sup_name))
    
    # Add worker nodes
    for node_name in builder.node_classes.keys():
        graph.add_node(node_name, builder.create_node_wrapper(node_name))

    # Add CallSubgraph nodes
    if enable_subgraphs:
        for subgraph_id in reg.list_subgraphs():
            node_name = builder._call_subgraph_node_name(subgraph_id)
            graph.add_node(node_name, builder.create_call_subgraph_wrapper(subgraph_id))
    
    # Supervisor -> workers conditional edges
    for sup_name in builder.supervisor_names:
        route_fn = builder.create_routing_function(sup_name)
        routing_map = builder.build_routing_map(sup_name)
        
        graph.add_conditional_edges(
            f"{sup_name}_supervisor",
            route_fn,
            routing_map,
        )
    
    # Worker -> Supervisor return edges
    for node_name, node_cls in builder.node_classes.items():
        contract = node_cls.CONTRACT
        sup_name = contract.supervisor
        
        if contract.is_terminal:
            graph.add_edge(node_name, END)
        else:
            graph.add_edge(node_name, f"{sup_name}_supervisor")

    # CallSubgraph -> Parent Supervisor return edges
    if enable_subgraphs:
        return_router = builder.create_call_subgraph_return_router()
        return_map = {
            f"{sup_name}_supervisor": f"{sup_name}_supervisor"
            for sup_name in builder.supervisor_names
        }
        return_map[END] = END
        for subgraph_id in reg.list_subgraphs():
            node_name = builder._call_subgraph_node_name(subgraph_id)
            graph.add_conditional_edges(node_name, return_router, return_map)

    # Entry point
    if entrypoint:
        entry_name, entry_node, route_fn = entrypoint
        graph.add_node(entry_name, entry_node)
        graph.set_entry_point(entry_name)

        routing_map = {
            f"{sup_name}_supervisor": f"{sup_name}_supervisor"
            for sup_name in builder.supervisor_names
        }
        routing_map[END] = END
        graph.add_conditional_edges(entry_name, route_fn, routing_map)
    
    logger.info(
        f"Graph built: {len(builder.supervisor_names)} supervisors, "
        f"{len(builder.node_classes)} nodes, "
        f"{len(reg.list_subgraphs()) if enable_subgraphs else 0} subgraphs"
    )
    
    return graph
