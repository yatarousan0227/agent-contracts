"""GraphBuilder - Registry-based graph construction.

Reads registered nodes from NodeRegistry and
automatically builds LangGraph StateGraph.
"""
from __future__ import annotations

from typing import Any, Callable, Optional
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, END

from agent_contracts.registry import NodeRegistry, get_node_registry
from agent_contracts.supervisor import GenericSupervisor
from agent_contracts.state import merge_slice_updates
from agent_contracts.contracts import NodeContract
from agent_contracts.config import get_config
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
    Returns:
        - GraphBuilder instance.
    """
    
    def __init__(
        self,
        registry: NodeRegistry | None = None,
        state_class: type | None = None,
        llm_provider: Callable[[], Any] | None = None,
        dependency_provider: Callable[[NodeContract], dict] | None = None,
        supervisor_factory: Callable[[str, Any], GenericSupervisor] | None = None,
    ) -> None:
        """Initialize the graph builder.

        Args:
            - registry: Node registry.
            - state_class: State type (uses dict if not provided).
            - llm_provider: Function that provides LLM instances.
            - dependency_provider: Function that provides dependencies for nodes.
            - supervisor_factory: Function that creates supervisor instances.
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
        self.supervisor_names.add(name)
        if self.llm_provider is None:
            supervisor = GenericSupervisor(
                supervisor_name=name,
                llm=llm,
                registry=self.registry,
            )
            self.supervisor_instances[name] = supervisor
        
        # Create related node instances
        for node_name in self.registry.get_supervisor_nodes(name):
            node_cls = self.registry.get_node_class(node_name)
            if node_cls is None:
                continue
            self.node_classes[node_name] = node_cls
            if self.dependency_provider is None and self.llm_provider is None:
                instance = node_cls(llm=llm, **services)
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
        routing = {name: name for name in self.registry.get_supervisor_nodes(supervisor_name)}
        routing["done"] = END  # LangGraph END constant
        return routing

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
            return merge_slice_updates(state, updates)
        
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
            return merge_slice_updates(state, updates)
        
        wrapper.__name__ = f"{supervisor_name}_supervisor"
        return wrapper
    
    def create_routing_function(self, supervisor_name: str) -> Callable:
        """Create a routing function for post-supervisor routing.

        Args:
            - supervisor_name: Supervisor name for routing context.
        Returns:
            - Routing function returning the next node name.
        """
        valid_nodes = set(self.registry.get_supervisor_nodes(supervisor_name))
        
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
        f"Graph built: {len(builder.supervisor_names)} supervisors, {len(builder.node_classes)} nodes"
    )
    
    return graph
