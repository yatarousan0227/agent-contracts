"""Graph construction for the support assistant."""
from __future__ import annotations

from typing import Callable

from langgraph.graph import StateGraph, END

from agent_contracts import BaseAgentState, ContractValidator, NodeRegistry
from agent_contracts.graph_builder import GraphBuilder

from support_assistant.nodes import CreateTicketNode, FallbackNode, FaqNode, HandoffNode


def build_support_graph(
    llm_provider: Callable[[], object] | None = None,
) -> StateGraph:
    """Build the support assistant graph with GraphBuilder."""
    registry = NodeRegistry()
    registry.add_valid_slice("ticket")
    registry.register(FaqNode)
    registry.register(CreateTicketNode)
    registry.register(HandoffNode)
    registry.register(FallbackNode)

    validator = ContractValidator(registry, strict=True)
    result = validator.validate()
    if result.has_errors:
        raise SystemExit(str(result))

    builder = GraphBuilder(
        registry=registry,
        state_class=BaseAgentState,
        llm_provider=llm_provider,
    )
    builder.add_supervisor("support")

    graph = StateGraph(BaseAgentState)

    for sup_name in builder.supervisor_names:
        graph.add_node(f"{sup_name}_supervisor", builder.create_supervisor_wrapper(sup_name))

    for node_name in builder.node_classes.keys():
        graph.add_node(node_name, builder.create_node_wrapper(node_name))

    for sup_name in builder.supervisor_names:
        route_fn = builder.create_routing_function(sup_name)
        graph.add_conditional_edges(
            f"{sup_name}_supervisor",
            route_fn,
            builder.build_routing_map(sup_name),
        )

    for node_name, node_cls in builder.node_classes.items():
        contract = node_cls.CONTRACT
        sup_name = contract.supervisor
        if contract.is_terminal:
            graph.add_edge(node_name, END)
        else:
            graph.add_edge(node_name, f"{sup_name}_supervisor")

    graph.set_entry_point("support_supervisor")
    return graph
