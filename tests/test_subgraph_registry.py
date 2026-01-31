import pytest

from agent_contracts import (
    NodeContract,
    NodeInputs,
    NodeOutputs,
    ModularNode,
    NodeRegistry,
    SubgraphContract,
    SubgraphDefinition,
)


def _make_contract(subgraph_id: str = "sg_test") -> SubgraphContract:
    return SubgraphContract(
        subgraph_id=subgraph_id,
        description="Test subgraph",
        reads=["request"],
        writes=["response"],
        entrypoint="entry",
    )


def _make_definition(subgraph_id: str = "sg_test") -> SubgraphDefinition:
    return SubgraphDefinition(
        subgraph_id=subgraph_id,
        supervisors=["sup"],
        nodes=["node_a"],
    )


class TestSubgraphRegistry:
    def test_register_get_list(self):
        registry = NodeRegistry()
        contract = _make_contract()
        definition = _make_definition()

        registry.register_subgraph(contract, definition)

        stored = registry.get_subgraph("sg_test")
        assert stored is not None
        assert stored[0] == contract
        assert stored[1] == definition
        assert registry.list_subgraphs() == ["sg_test"]

    def test_duplicate_subgraph_id_raises(self):
        registry = NodeRegistry()
        contract = _make_contract()
        definition = _make_definition()

        registry.register_subgraph(contract, definition)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_subgraph(contract, definition)

    def test_subgraph_id_collision_with_node(self):
        registry = NodeRegistry()

        class CollidingNode(ModularNode):
            CONTRACT = NodeContract(
                name="sg_test",
                description="Colliding node",
                reads=[],
                writes=[],
                supervisor="test",
            )

            async def execute(self, inputs: NodeInputs) -> NodeOutputs:
                return NodeOutputs(response={})

        registry.register(CollidingNode)

        contract = _make_contract()
        definition = _make_definition()

        with pytest.raises(ValueError, match="conflicts with registered node"):
            registry.register_subgraph(contract, definition)

    def test_node_name_collision_with_subgraph(self):
        registry = NodeRegistry()
        contract = _make_contract()
        definition = _make_definition()

        registry.register_subgraph(contract, definition)

        class CollidingNode(ModularNode):
            CONTRACT = NodeContract(
                name="sg_test",
                description="Colliding node",
                reads=[],
                writes=[],
                supervisor="test",
            )

            async def execute(self, inputs: NodeInputs) -> NodeOutputs:
                return NodeOutputs(response={})

        with pytest.raises(ValueError, match="conflicts with registered subgraph"):
            registry.register(CollidingNode)

    def test_node_name_reserved_prefix(self):
        registry = NodeRegistry()

        class ReservedPrefixNode(ModularNode):
            CONTRACT = NodeContract(
                name="call_subgraph::blocked",
                description="Reserved prefix node",
                reads=[],
                writes=[],
                supervisor="test",
            )

            async def execute(self, inputs: NodeInputs) -> NodeOutputs:
                return NodeOutputs(response={})

        with pytest.raises(ValueError, match="reserved prefix"):
            registry.register(ReservedPrefixNode)

    def test_export_subgraphs(self):
        registry = NodeRegistry()
        contract = _make_contract()
        definition = _make_definition()

        registry.register_subgraph(contract, definition)

        exported = registry.export_subgraphs()
        assert "sg_test" in exported
        assert exported["sg_test"]["contract"]["subgraph_id"] == "sg_test"
        assert exported["sg_test"]["definition"]["subgraph_id"] == "sg_test"
