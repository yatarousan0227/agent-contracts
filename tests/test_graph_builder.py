"""Tests for GraphBuilder and build_graph_from_registry."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langgraph.graph import StateGraph, END

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    NodeRegistry,
    GraphBuilder,
    build_graph_from_registry,
    SubgraphContract,
    SubgraphDefinition,
)
from agent_contracts.runtime.hierarchy import Budgets


# =============================================================================
# Test Nodes (prefixed with Sample to avoid pytest collection)
# =============================================================================

class SampleNodeA(ModularNode):
    """Test node A."""
    CONTRACT = NodeContract(
        name="node_a",
        description="Test node A",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        requires_llm=False,
        trigger_conditions=[
            TriggerCondition(priority=10, when={"request.action": "a"})
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"from": "node_a"})


class SampleNodeB(ModularNode):
    """Test node B (terminal)."""
    CONTRACT = NodeContract(
        name="node_b",
        description="Test node B",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(priority=5, when={"request.action": "b"})
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"from": "node_b"})


class SampleNodeWithLLM(ModularNode):
    """Test node that requires LLM."""
    CONTRACT = NodeContract(
        name="node_with_llm",
        description="Node requiring LLM",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        requires_llm=True,
        trigger_conditions=[
            TriggerCondition(priority=1)
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"from": "node_with_llm"})


def _make_registry() -> NodeRegistry:
    reg = NodeRegistry()
    reg.register(SampleNodeA)
    reg.register(SampleNodeB)
    return reg


# =============================================================================
# GraphBuilder Tests
# =============================================================================

class TestGraphBuilder:
    """Tests for GraphBuilder class."""

    @pytest.fixture
    def registry(self):
        """Create registry with test nodes."""
        reg = NodeRegistry()
        reg.register(SampleNodeA)
        reg.register(SampleNodeB)
        return reg

    def test_init_with_registry(self, registry):
        """Test initialization with registry."""
        builder = GraphBuilder(registry=registry)
        
        assert builder.registry is registry
        assert len(builder.supervisor_names) == 0
        assert len(builder.node_classes) == 0

    def test_init_without_registry_uses_global(self):
        """Test initialization without registry uses global."""
        builder = GraphBuilder()
        
        assert builder.registry is not None

    def test_add_supervisor(self, registry):
        """Test adding a supervisor."""
        builder = GraphBuilder(registry=registry)
        
        result = builder.add_supervisor("main", llm=None)
        
        assert result is builder  # Returns self for chaining
        assert "main" in builder.supervisor_names
        assert "node_a" in builder.node_classes
        assert "node_b" in builder.node_classes
        assert "node_a" in builder.node_instances
        assert "node_b" in builder.node_instances

    def test_add_supervisor_with_llm_provider(self, registry):
        """Test adding supervisor with llm_provider skips instance creation."""
        mock_llm_provider = MagicMock(return_value="mock_llm")
        builder = GraphBuilder(registry=registry, llm_provider=mock_llm_provider)
        
        builder.add_supervisor("main")
        
        # With llm_provider, instances are created on-demand, not upfront
        assert "main" in builder.supervisor_names
        assert "node_a" in builder.node_classes
        assert len(builder.node_instances) == 0  # Not created upfront

    def test_build_routing_map(self, registry):
        """Test building routing map."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        routing_map = builder.build_routing_map("main")
        
        assert routing_map["node_a"] == "node_a"
        assert routing_map["node_b"] == "node_b"
        assert routing_map["done"] == END

    def test_create_node_wrapper(self, registry):
        """Test creating node wrapper function."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_a")
        
        assert callable(wrapper)
        assert wrapper.__name__ == "node_a_node"

    @pytest.mark.asyncio
    async def test_node_wrapper_executes_node(self, registry):
        """Test that node wrapper executes the node."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_a")
        state = {"request": {"action": "a"}, "response": {}}
        
        result = await wrapper(state)
        
        assert result["response"]["from"] == "node_a"

    @pytest.mark.asyncio
    async def test_node_wrapper_with_missing_class(self, registry):
        """Test node wrapper with missing class returns empty dict."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        # Remove node class to simulate missing
        del builder.node_classes["node_a"]
        
        wrapper = builder.create_node_wrapper("node_a")
        result = await wrapper({})
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_wrapper_with_missing_instance(self, registry):
        """Test node wrapper with missing instance returns empty dict."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        # Remove instance to simulate missing
        del builder.node_instances["node_a"]
        
        wrapper = builder.create_node_wrapper("node_a")
        result = await wrapper({})
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_wrapper_with_dependency_provider(self, registry):
        """Test node wrapper uses dependency_provider."""
        mock_dep_provider = MagicMock(return_value={})
        builder = GraphBuilder(
            registry=registry,
            dependency_provider=mock_dep_provider,
        )
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_a")
        state = {"request": {"action": "a"}, "response": {}}
        
        result = await wrapper(state)
        
        mock_dep_provider.assert_called_once()
        assert result["response"]["from"] == "node_a"

    @pytest.mark.asyncio
    async def test_node_wrapper_with_llm_provider(self):
        """Test node wrapper uses llm_provider for nodes requiring LLM."""
        registry = NodeRegistry()
        registry.register(SampleNodeWithLLM)
        
        mock_llm = MagicMock()
        mock_llm_provider = MagicMock(return_value=mock_llm)
        
        builder = GraphBuilder(
            registry=registry,
            llm_provider=mock_llm_provider,
        )
        builder.add_supervisor("main")
        
        wrapper = builder.create_node_wrapper("node_with_llm")
        state = {"request": {}, "response": {}}
        
        result = await wrapper(state)
        
        mock_llm_provider.assert_called()
        assert result["response"]["from"] == "node_with_llm"

    def test_create_supervisor_wrapper(self, registry):
        """Test creating supervisor wrapper."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        wrapper = builder.create_supervisor_wrapper("main")
        
        assert callable(wrapper)
        assert wrapper.__name__ == "main_supervisor"

    @pytest.mark.asyncio
    async def test_supervisor_wrapper_with_missing_supervisor(self, registry):
        """Test supervisor wrapper with missing supervisor returns empty dict."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        # Remove supervisor to simulate missing
        del builder.supervisor_instances["main"]
        
        wrapper = builder.create_supervisor_wrapper("main")
        result = await wrapper({})
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_supervisor_wrapper_preserves_response_updates(self, registry):
        """Supervisor response updates should not be overwritten."""
        class ResponseSupervisor:
            async def run(self, state, config=None) -> dict:
                internal = state.get("_internal", {})
                if not isinstance(internal, dict):
                    internal = {}
                return {
                    "_internal": {**internal, "decision": "done"},
                    "response": {"response_type": "terminal", "response_message": "stop"},
                }

        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.supervisor_instances["main"] = ResponseSupervisor()

        wrapper = builder.create_supervisor_wrapper("main")
        result = await wrapper({"response": {}, "_internal": {}})

        assert result["response"]["response_type"] == "terminal"

    @pytest.mark.asyncio
    async def test_supervisor_wrapper_with_llm_provider(self, registry):
        """Test supervisor wrapper creates supervisor on-demand with llm_provider."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="node_a"))
        mock_llm_provider = MagicMock(return_value=mock_llm)
        
        builder = GraphBuilder(
            registry=registry,
            llm_provider=mock_llm_provider,
        )
        builder.add_supervisor("main")
        
        wrapper = builder.create_supervisor_wrapper("main")
        state = {
            "request": {"action": "a"},
            "response": {},
            "_internal": {},
        }
        
        # Should create supervisor on-demand
        result = await wrapper(state)
        
        mock_llm_provider.assert_called()

    def test_create_routing_function(self, registry):
        """Test creating routing function."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        
        route_fn = builder.create_routing_function("main")
        
        assert callable(route_fn)
        assert route_fn.__name__ == "route_after_main_supervisor"

    def test_routing_function_returns_done_for_terminal_response(self, registry):
        """Test routing returns 'done' for terminal response type."""
        # Set up config with terminal types
        from agent_contracts.config import set_config
        from agent_contracts.config.schema import FrameworkConfig, SupervisorConfig
        config = FrameworkConfig(
            supervisor=SupervisorConfig(
                max_iterations=10,
                terminal_response_types=["interview", "error"],
            )
        )
        set_config(config)
        
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        route_fn = builder.create_routing_function("main")
        
        state = {
            "response": {"response_type": "interview"},  # Terminal type
            "_internal": {"decision": "node_a"},
        }
        
        result = route_fn(state)
        
        assert result == "done"

    def test_routing_function_returns_decision(self, registry):
        """Test routing returns decision from _internal."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        route_fn = builder.create_routing_function("main")
        
        state = {
            "response": {},
            "_internal": {"decision": "node_a"},
        }
        
        result = route_fn(state)
        
        assert result == "node_a"

    def test_routing_function_returns_done_for_invalid_decision(self, registry):
        """Test routing returns 'done' for invalid decision."""
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main")
        route_fn = builder.create_routing_function("main")
        
        state = {
            "response": {},
            "_internal": {"decision": "invalid_node"},
        }
        
        result = route_fn(state)
        
        assert result == "done"


# =============================================================================
# build_graph_from_registry Tests
# =============================================================================

class TestBuildGraphFromRegistry:
    """Tests for build_graph_from_registry function."""

    @pytest.fixture
    def registry(self):
        """Create registry with test nodes."""
        reg = NodeRegistry()
        reg.register(SampleNodeA)
        reg.register(SampleNodeB)
        return reg

    def test_builds_state_graph(self, registry):
        """Test that function returns a StateGraph."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        assert isinstance(graph, StateGraph)

    def test_adds_supervisor_nodes(self, registry):
        """Test that supervisor nodes are added."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        # Check nodes exist in graph
        assert "main_supervisor" in graph.nodes

    def test_adds_worker_nodes(self, registry):
        """Test that worker nodes are added."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        assert "node_a" in graph.nodes
        assert "node_b" in graph.nodes

    def test_with_entrypoint(self, registry):
        """Test with custom entrypoint."""
        async def entry_node(state):
            return state
        
        def entry_route(state):
            return "main_supervisor"
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            entrypoint=("entry", entry_node, entry_route),
        )
        
        assert "entry" in graph.nodes

    def test_with_llm_provider(self, registry):
        """Test with llm_provider."""
        mock_llm_provider = MagicMock(return_value=MagicMock())
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            llm_provider=mock_llm_provider,
        )
        
        assert isinstance(graph, StateGraph)

    def test_with_dependency_provider(self, registry):
        """Test with dependency_provider."""
        mock_dep_provider = MagicMock(return_value={})
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            dependency_provider=mock_dep_provider,
        )
        
        assert isinstance(graph, StateGraph)

    def test_with_state_class(self, registry):
        """Test with custom state class."""
        class CustomState(dict):
            pass
        
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            state_class=CustomState,
        )
        
        assert isinstance(graph, StateGraph)

    def test_terminal_node_edges_to_end(self, registry):
        """Test that terminal nodes edge to END."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        # node_b is terminal, should edge to END
        edges = graph.edges
        # Check that node_b has an edge (to END)
        node_b_edges = [e for e in edges if e[0] == "node_b"]
        assert len(node_b_edges) > 0

    def test_non_terminal_node_edges_to_supervisor(self, registry):
        """Test that non-terminal nodes edge back to supervisor."""
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
        )
        
        # node_a is not terminal, should edge to supervisor
        edges = graph.edges
        node_a_edges = [e for e in edges if e[0] == "node_a"]
        assert len(node_a_edges) > 0

    def test_with_supervisor_factory(self, registry):
        """Test with custom supervisor_factory parameter."""
        from agent_contracts import GenericSupervisor
        
        def custom_context_builder(state, candidates):
            return {
                "slices": {"request", "response", "_internal", "custom"},
                "summary": "Custom context"
            }
        
        def supervisor_factory(name: str, llm):
            return GenericSupervisor(
                supervisor_name=name,
                llm=llm,
                registry=registry,
                context_builder=custom_context_builder,
            )
        
        mock_llm_provider = MagicMock(return_value=MagicMock())
        
        # Should not raise error
        graph = build_graph_from_registry(
            registry=registry,
            supervisors=["main"],
            llm_provider=mock_llm_provider,
            supervisor_factory=supervisor_factory,
        )
        
        assert isinstance(graph, StateGraph)
        assert "main_supervisor" in graph.nodes


class TestGraphBuilderInternals:
    def test_return_state_merges_for_typed_state(self):
        builder = GraphBuilder(state_class=type("State", (), {}))
        state = {"response": {"a": 1}}
        updates = {"response": {"b": 2}}
        assert builder._return_state(state, updates) == {"response": {"a": 1, "b": 2}}

    def test_add_supervisor_with_explicit_llm(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry)
        builder.add_supervisor("main", llm="provided")
        assert "main" in builder.supervisor_names

    def test_add_supervisor_respects_node_allowlist(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, node_allowlist={"node_a"})
        builder.add_supervisor("main")
        assert "node_b" not in builder.node_classes

    def test_add_supervisor_skips_missing_node_class(self, monkeypatch):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry)
        monkeypatch.setattr(registry, "get_supervisor_nodes", lambda _name: ["ghost"])
        monkeypatch.setattr(registry, "get_node_class", lambda _name: None)
        builder.add_supervisor("main")
        assert builder.node_classes == {}

    def test_list_call_subgraph_nodes(self):
        registry = NodeRegistry()
        contract = SubgraphContract(
            subgraph_id="sg1",
            description="subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="main",
        )
        definition = SubgraphDefinition(subgraph_id="sg1", supervisors=["main"])
        registry.register_subgraph(contract, definition)

        builder = GraphBuilder(registry=registry)
        assert builder._list_call_subgraph_nodes() == ["call_subgraph__sg1"]

    def test_get_internal_non_dict(self):
        builder = GraphBuilder()
        assert builder._get_internal({"_internal": "nope"}) == {}

    def test_increment_step_invalid_value(self):
        builder = GraphBuilder()
        internal, step = builder._increment_step({"step_count": "bad"})
        assert step == 1
        assert internal["step_count"] == 1

    def test_normalize_budgets_from_instance(self):
        builder = GraphBuilder()
        internal, budgets = builder._normalize_budgets({"budgets": Budgets(max_depth=1)})
        assert budgets.max_depth == 1
        assert internal["budgets"]["max_depth"] == 1

    def test_decision_kind_for_supervisor_terminal_and_fallback(self, monkeypatch):
        builder = GraphBuilder()

        class DummySupervisorConfig:
            terminal_response_types = ["terminal"]

        class DummyConfig:
            supervisor = DummySupervisorConfig()

        monkeypatch.setattr("agent_contracts.graph_builder.get_config", lambda: DummyConfig())
        assert builder._decision_kind_for_supervisor("done", 0, "terminal") == "STOP_GLOBAL"
        assert builder._decision_kind_for_supervisor(None, 0, None) == "FALLBACK"

    def test_get_allowlist_from_supervisor_instance(self):
        builder = GraphBuilder()

        class DummySupervisor:
            allowlist = ["node_a", "done"]

        allowlist = builder._get_allowlist("main", DummySupervisor())
        assert allowlist == {"node_a", "done"}

    def test_get_allowlist_falls_back_to_configured_list(self):
        builder = GraphBuilder(supervisor_allowlists={"main": {"node_a"}})

        class DummySupervisor:
            allowlist = []

        allowlist = builder._get_allowlist("main", DummySupervisor())
        assert allowlist == {"node_a"}

    def test_is_decision_allowed_variants(self):
        builder = GraphBuilder()
        allowlist = {"node_a", "child_graph"}
        assert builder._is_decision_allowed("done", allowlist) is True
        assert builder._is_decision_allowed("node_a", allowlist) is True
        assert builder._is_decision_allowed("call_subgraph::child_graph", allowlist) is True
        assert builder._is_decision_allowed("node_b", allowlist) is False

    def test_build_terminal_response_with_non_dict_response(self):
        builder = GraphBuilder()
        response = builder._build_terminal_response({"response": "nope"}, "reason")
        assert response["response_type"] == "terminal"
        assert response["response_message"] == "reason"

    @pytest.mark.asyncio
    async def test_create_node_wrapper_with_internal_updates(self):
        registry = _make_registry()
        class NodeWithInternal(ModularNode):
            CONTRACT = NodeContract(
                name="node_internal",
                description="Node with internal updates",
                reads=["request"],
                writes=["response", "_internal"],
                supervisor="main",
                trigger_conditions=[TriggerCondition(priority=1)],
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                return NodeOutputs(_internal={"foo": "bar"})

        registry.register(NodeWithInternal)
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.add_supervisor("main")

        wrapper = builder.create_node_wrapper("node_internal")
        result = await wrapper({"request": {}, "_internal": {}})
        assert result["_internal"]["foo"] == "bar"

    @pytest.mark.asyncio
    async def test_create_supervisor_wrapper_targets_and_response(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.add_supervisor("main")

        class FakeSupervisor:
            async def run(self, state, config=None):
                return {"_internal": {"decision": "call_subgraph::child_graph"}, "response": {}}

        builder.supervisor_instances["main"] = FakeSupervisor()
        wrapper = builder.create_supervisor_wrapper("main")
        result = await wrapper({"response": {"response_type": "ok"}, "_internal": {}})
        assert result["_internal"]["decision"] == "call_subgraph::child_graph"

    @pytest.mark.asyncio
    async def test_create_supervisor_wrapper_copies_response_when_missing(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.add_supervisor("main")

        class FakeSupervisor:
            async def run(self, state, config=None):
                return {"_internal": {"decision": "done"}}

        builder.supervisor_instances["main"] = FakeSupervisor()
        wrapper = builder.create_supervisor_wrapper("main")
        result = await wrapper({"response": {"response_type": "ok"}, "_internal": {}})
        assert result["response"]["response_type"] == "ok"

    @pytest.mark.asyncio
    async def test_create_supervisor_wrapper_without_internal_updates(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.add_supervisor("main")

        class FakeSupervisor:
            async def run(self, state, config=None):
                return {}

        builder.supervisor_instances["main"] = FakeSupervisor()
        wrapper = builder.create_supervisor_wrapper("main")
        result = await wrapper({"response": "nope", "_internal": {"decision": None}})
        assert result["_internal"]["decision"] is None

    def test_resolve_subgraph_members_errors_and_missing_contract(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry)
        with pytest.raises(ValueError):
            builder._resolve_subgraph_members("missing")

        contract = SubgraphContract(
            subgraph_id="sg_missing_node",
            description="Missing node subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="main",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_missing_node",
            supervisors=["main"],
            nodes=["ghost"],
        )
        registry.register_subgraph(contract, definition)
        supervisors, node_allowlist, entry = builder._resolve_subgraph_members("sg_missing_node")
        assert entry == "main"
        assert node_allowlist == {"ghost"}
        assert supervisors == ["main"]

    def test_build_subgraph_graph_errors(self, monkeypatch):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry)
        monkeypatch.setattr(builder, "_resolve_subgraph_members", lambda _subgraph_id: ([], None, "main"))
        with pytest.raises(ValueError):
            builder._build_subgraph_graph("sg_empty")

    def test_build_subgraph_graph_missing_entrypoint(self, monkeypatch):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry)
        monkeypatch.setattr(builder, "_resolve_subgraph_members", lambda _subgraph_id: (["main"], None, "missing"))
        monkeypatch.setattr(
            "agent_contracts.graph_builder.build_graph_from_registry",
            lambda **_kwargs: StateGraph(dict),
        )
        with pytest.raises(ValueError):
            builder._build_subgraph_graph("sg_missing_entry")

    def test_get_compiled_subgraph_uses_cache(self):
        builder = GraphBuilder()
        builder.subgraph_cache["sg_cached"] = "compiled"
        assert builder._get_compiled_subgraph("sg_cached") == "compiled"

    @pytest.mark.asyncio
    async def test_call_subgraph_wrapper_disabled(self):
        builder = GraphBuilder(enable_subgraphs=False)
        wrapper = builder.create_call_subgraph_wrapper("sg1")
        assert await wrapper({"_internal": {}}) == {}

    @pytest.mark.asyncio
    async def test_call_subgraph_wrapper_child_result_not_dict(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.subgraph_cache["sg1"] = AsyncMock(ainvoke=AsyncMock(return_value="nope"))

        wrapper = builder.create_call_subgraph_wrapper("sg1")
        result = await wrapper({"_internal": {"call_stack": "nope", "visited_subgraphs": "nope"}})
        assert result == {}

    @pytest.mark.asyncio
    async def test_call_subgraph_wrapper_child_internal_handling(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.subgraph_cache["sg1"] = AsyncMock(
            ainvoke=AsyncMock(return_value={"_internal": "nope"})
        )

        wrapper = builder.create_call_subgraph_wrapper("sg1")
        result = await wrapper({"_internal": {"call_stack": "nope", "visited_subgraphs": "nope"}})
        assert result["_internal"].get("return_to_supervisor") is None

    @pytest.mark.asyncio
    async def test_call_subgraph_wrapper_child_stack_non_list(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.subgraph_cache["sg1"] = AsyncMock(
            ainvoke=AsyncMock(return_value={"_internal": {"call_stack": "nope"}})
        )

        wrapper = builder.create_call_subgraph_wrapper("sg1")
        result = await wrapper({"_internal": {}})
        assert isinstance(result["_internal"].get("call_stack"), list)

    @pytest.mark.asyncio
    async def test_call_subgraph_wrapper_return_to_from_stack(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.subgraph_cache["sg1"] = AsyncMock(
            ainvoke=AsyncMock(
                return_value={
                    "_internal": {
                        "call_stack": [
                            {"locals": {"parent_supervisor": "main"}},
                        ]
                    }
                }
            )
        )

        wrapper = builder.create_call_subgraph_wrapper("sg1")
        result = await wrapper({"_internal": {}})
        assert result["_internal"]["return_to_supervisor"] == "main"

    @pytest.mark.asyncio
    async def test_call_subgraph_wrapper_locals_not_dict(self):
        registry = _make_registry()
        builder = GraphBuilder(registry=registry, enable_subgraphs=True)
        builder.subgraph_cache["sg1"] = AsyncMock(
            ainvoke=AsyncMock(
                return_value={
                    "_internal": {
                        "call_stack": [
                            {"locals": "nope"},
                        ]
                    }
                }
            )
        )

        wrapper = builder.create_call_subgraph_wrapper("sg1")
        result = await wrapper({"_internal": {"last_supervisor": "main"}})
        assert result["_internal"]["return_to_supervisor"] == "main"

    def test_call_subgraph_return_router(self):
        builder = GraphBuilder(enable_subgraphs=True)
        route = builder.create_call_subgraph_return_router()
        assert route({"_internal": "nope"}) == END
        assert route({"_internal": {"return_to_supervisor": 123}}) == END

    def test_build_graph_from_registry_subgraph_prefix_errors(self):
        registry = _make_registry()
        class BadNode(ModularNode):
            CONTRACT = NodeContract(
                name="call_subgraph__bad",
                description="Bad node",
                reads=[],
                writes=[],
                supervisor="main",
            )
            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                return NodeOutputs()

        registry.register(BadNode)
        with pytest.raises(ValueError):
            build_graph_from_registry(
                registry=registry,
                supervisors=["main"],
                enable_subgraphs=True,
            )
