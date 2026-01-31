"""Tests for ContractValidator."""
import pytest

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    SubgraphContract,
    SubgraphDefinition,
)
from agent_contracts.registry import NodeRegistry
from agent_contracts.validator import ContractValidator, ValidationResult


# =============================================================================
# Test Fixtures
# =============================================================================

class ValidNode(ModularNode):
    """A valid node for testing."""
    CONTRACT = NodeContract(
        name="valid_node",
        description="A valid test node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                when={"request.action": "test"},
                llm_hint="Test action",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class AnotherValidNode(ModularNode):
    """Another valid node that also writes to response."""
    CONTRACT = NodeContract(
        name="another_valid_node",
        description="Another valid test node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=5,
                when={"request.action": "other"},
                llm_hint="Other action",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class NodeWithUnknownSlice(ModularNode):
    """A node with an unknown slice."""
    CONTRACT = NodeContract(
        name="unknown_slice_node",
        description="Node with unknown slice",
        reads=["invalid_slice"],  # This slice doesn't exist
        writes=["response"],
        supervisor="main",
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class NodeWithUnknownService(ModularNode):
    """A node requiring an unknown service."""
    CONTRACT = NodeContract(
        name="unknown_service_node",
        description="Node with unknown service",
        reads=["request"],
        writes=["response"],
        services=["nonexistent_service"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(priority=1)
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class OrphanNode(ModularNode):
    """A node without a supervisor."""
    CONTRACT = NodeContract(
        name="orphan_node",
        description="Node without supervisor",
        reads=["request"],
        writes=["response"],
        supervisor="",  # Empty supervisor
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class UnreachableNode(ModularNode):
    """A node with no trigger conditions."""
    CONTRACT = NodeContract(
        name="unreachable_node",
        description="Node without trigger conditions",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[],  # No conditions
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"done": True})


class RequestWriterNode(ModularNode):
    """A node that writes to request slice."""
    CONTRACT = NodeContract(
        name="request_writer",
        description="Writes to request slice",
        reads=["request"],
        writes=["request"],
        supervisor="main",
        trigger_conditions=[TriggerCondition(priority=1)],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(request={"mutated": True})


class SubgraphGoodNode(ModularNode):
    """A subgraph node that stays within the boundary."""
    CONTRACT = NodeContract(
        name="subgraph_good_node",
        description="Subgraph-good node",
        reads=["request"],
        writes=["response"],
        supervisor="subgraph_supervisor",
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"ok": True})


class SubgraphBadNode(ModularNode):
    """A subgraph node that violates the boundary."""
    CONTRACT = NodeContract(
        name="subgraph_bad_node",
        description="Subgraph-bad node",
        reads=["request", "extra_slice"],
        writes=["response"],
        supervisor="subgraph_supervisor",
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"ok": False})


# =============================================================================
# Tests
# =============================================================================

class TestValidationResult:
    """Tests for ValidationResult."""
    
    def test_empty_result_is_valid(self):
        """Empty result should be valid."""
        result = ValidationResult()
        assert result.is_valid
        assert not result.has_errors
        assert not result.has_warnings
    
    def test_result_with_errors_is_invalid(self):
        """Result with errors should be invalid."""
        result = ValidationResult(errors=["Some error"])
        assert not result.is_valid
        assert result.has_errors
    
    def test_result_with_warnings_is_valid(self):
        """Result with only warnings should be valid."""
        result = ValidationResult(warnings=["Some warning"])
        assert result.is_valid
        assert not result.has_errors
        assert result.has_warnings
    
    def test_str_format(self):
        """Test string formatting."""
        result = ValidationResult(
            errors=["Error 1"],
            warnings=["Warning 1"],
            info=["Info 1"],
        )
        output = str(result)
        assert "ERRORS:" in output
        assert "Error 1" in output
        assert "WARNINGS:" in output
        assert "Warning 1" in output
        assert "INFO:" in output
        assert "Info 1" in output


class TestContractValidator:
    """Tests for ContractValidator."""
    
    def test_valid_nodes_pass_validation(self):
        """Valid nodes should pass validation."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.is_valid
        assert not result.has_errors
    
    def test_unknown_slice_detected(self):
        """Unknown slice should be detected as error."""
        registry = NodeRegistry()
        # Suppress the warning during registration
        registry.register(NodeWithUnknownSlice)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_errors
        assert any("invalid_slice" in e for e in result.errors)
        assert any("unknown_slice_node" in e for e in result.errors)
    
    def test_unknown_service_warning(self):
        """Unknown service should be detected as warning."""
        registry = NodeRegistry()
        registry.register(NodeWithUnknownService)
        
        # Provide known services
        validator = ContractValidator(
            registry,
            known_services={"db_service", "api_service"},
        )
        result = validator.validate()
        
        assert result.has_warnings
        assert any("nonexistent_service" in w for w in result.warnings)
    
    def test_service_validation_skipped_if_no_known_services(self):
        """Service validation should be skipped if known_services is None."""
        registry = NodeRegistry()
        registry.register(NodeWithUnknownService)
        
        # No known_services provided
        validator = ContractValidator(registry)
        result = validator.validate()
        
        # Should not have service-related warnings
        assert not any("nonexistent_service" in w for w in result.warnings)
    
    def test_orphan_node_warning(self):
        """Orphan node should be detected as warning."""
        registry = NodeRegistry()
        registry.register(OrphanNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_warnings
        assert any("orphan" in w.lower() for w in result.warnings)
    
    def test_unreachable_node_warning(self):
        """Unreachable node should be detected as warning."""
        registry = NodeRegistry()
        registry.register(UnreachableNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_warnings
        assert any("unreachable" in w.lower() for w in result.warnings)
    
    def test_shared_writers_info(self):
        """Shared writers should be reported as info."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        # Both nodes write to 'response'
        assert any("response" in info and "valid_node" in info for info in result.info)

    def test_request_write_warning(self):
        """Writing to request slice should be warned."""
        registry = NodeRegistry()
        registry.register(RequestWriterNode)
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        assert result.has_warnings
        assert any("request" in w for w in result.warnings)

    def test_strict_mode_escalates_warnings(self):
        """Strict mode should convert warnings to errors."""
        registry = NodeRegistry()
        registry.register(NodeWithUnknownService)
        
        validator = ContractValidator(
            registry,
            known_services={"db_service"},
            strict=True,
        )
        result = validator.validate()
        
        assert result.has_errors
        assert not result.has_warnings
        assert any("STRICT:" in e for e in result.errors)

    def test_subgraph_boundary_violation_error(self):
        """Subgraph boundary violations should be errors."""
        registry = NodeRegistry()
        registry.add_valid_slice("extra_slice")
        registry.register(SubgraphGoodNode)
        registry.register(SubgraphBadNode)

        contract = SubgraphContract(
            subgraph_id="sg_boundary",
            description="Boundary test subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="subgraph_supervisor",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_boundary",
            supervisors=["subgraph_supervisor"],
            nodes=["subgraph_good_node", "subgraph_bad_node"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(registry)
        result = validator.validate()

        assert result.has_errors
        assert any(
            "boundary violation" in e and "subgraph_bad_node" in e
            for e in result.errors
        )

    def test_subgraph_entrypoint_missing_error(self):
        """Missing subgraph entrypoint should be an error."""
        registry = NodeRegistry()
        registry.register(ValidNode)

        contract = SubgraphContract(
            subgraph_id="sg_missing_entry",
            description="Missing entrypoint subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="missing_entrypoint",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_missing_entry",
            supervisors=["main"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(registry)
        result = validator.validate()

        assert result.has_errors
        assert any("entrypoint" in e for e in result.errors)

    def test_subgraph_definition_missing_node_error(self):
        """Unknown node in subgraph definition should be an error."""
        registry = NodeRegistry()
        registry.register(ValidNode)

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
            nodes=["missing_node"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(registry)
        result = validator.validate()

        assert result.has_errors
        assert any("unknown node" in e for e in result.errors)

    def test_allowlist_unknown_entry_warning(self):
        """Unknown allowlist entries should warn."""
        registry = NodeRegistry()
        registry.register(ValidNode)

        contract = SubgraphContract(
            subgraph_id="sg_allowlist",
            description="Allowlist test subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="main",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_allowlist",
            supervisors=["main"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(
            registry,
            supervisor_allowlists={"main": {"missing_node"}},
        )
        result = validator.validate()

        assert result.has_warnings
        assert any("Allowlist entry" in w for w in result.warnings)

    def test_allowlist_unknown_entry_strict_error(self):
        """Strict mode should escalate allowlist warnings to errors."""
        registry = NodeRegistry()
        registry.register(ValidNode)

        contract = SubgraphContract(
            subgraph_id="sg_allowlist_strict",
            description="Allowlist strict test subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="main",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_allowlist_strict",
            supervisors=["main"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(
            registry,
            strict=True,
            supervisor_allowlists={"main": {"missing_node"}},
        )
        result = validator.validate()

        assert result.has_errors
        assert not result.has_warnings
        assert any("STRICT:" in e and "Allowlist entry" in e for e in result.errors)
    
    def test_get_shared_writers(self):
        """get_shared_writers should return correct mapping."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        writers = validator.get_shared_writers()
        
        assert "response" in writers
        assert set(writers["response"]) == {"valid_node", "another_valid_node"}
    
    def test_get_slice_readers(self):
        """get_slice_readers should return correct mapping."""
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)
        
        validator = ContractValidator(registry)
        readers = validator.get_slice_readers()
        
        assert "request" in readers
        assert set(readers["request"]) == {"valid_node", "another_valid_node"}

    def test_all_pass_message(self):
        """Test validation result str when all validations pass."""
        result = ValidationResult()
        output = str(result)
        assert "All validations passed" in output

    def test_get_unused_slices_write_only(self):
        """get_unused_slices detects write-only slices."""
        class WriteOnlyNode(ModularNode):
            CONTRACT = NodeContract(
                name="write_only_node",
                description="Writes to custom slice",
                reads=["request"],
                writes=["custom_output"],
                supervisor="main",
                trigger_conditions=[TriggerCondition(priority=10)],
            )
            async def execute(self, inputs, config=None): 
                return NodeOutputs()
        
        registry = NodeRegistry()
        registry.add_valid_slice("custom_output")
        registry.register(WriteOnlyNode)
        
        validator = ContractValidator(registry)
        unused = validator.get_unused_slices()
        
        assert "custom_output" in unused
        assert unused["custom_output"] == "write_only"

    def test_get_unused_slices_read_only(self):
        """get_unused_slices detects read-only slices (non-request)."""
        class ReadOnlyNode(ModularNode):
            CONTRACT = NodeContract(
                name="read_only_node",
                description="Reads from custom slice",
                reads=["custom_input"],
                writes=["response"],
                supervisor="main",
                trigger_conditions=[TriggerCondition(priority=10)],
            )
            async def execute(self, inputs, config=None): 
                return NodeOutputs()
        
        registry = NodeRegistry()
        registry.add_valid_slice("custom_input")
        registry.register(ReadOnlyNode)
        
        validator = ContractValidator(registry)
        unused = validator.get_unused_slices()
        
        # custom_input is read but never written
        assert "custom_input" in unused
        assert unused["custom_input"] == "read_only"

    def test_get_unused_slices_request_not_flagged(self):
        """get_unused_slices doesn't flag 'request' as read-only."""
        registry = NodeRegistry()
        registry.register(ValidNode)  # Reads from request, writes to response
        
        validator = ContractValidator(registry)
        unused = validator.get_unused_slices()
        
        # request should NOT be flagged as read_only (it's an input slice)
        assert "request" not in unused


class TestContractValidatorBranches:
    """Additional branch coverage for ContractValidator."""

    def test_validate_slices_skips_missing_contract(self):
        class StubRegistry:
            _valid_slices = {"request", "response", "_internal"}

            def get_all_nodes(self):
                return ["ghost"]

            def get_contract(self, _name):
                return None

        validator = ContractValidator(StubRegistry())
        result = ValidationResult()
        validator._validate_slices(result)
        assert result.errors == []

    def test_validate_services_skips_missing_contract(self):
        class StubRegistry:
            def get_all_nodes(self):
                return ["ghost"]

            def get_contract(self, _name):
                return None

        validator = ContractValidator(StubRegistry(), known_services={"svc"})
        result = ValidationResult()
        validator._validate_services(result)
        assert result.warnings == []

    def test_validate_reachability_skips_missing_contract(self):
        class StubRegistry:
            def get_all_nodes(self):
                return ["ghost"]

            def get_contract(self, _name):
                return None

        validator = ContractValidator(StubRegistry())
        result = ValidationResult()
        validator._validate_reachability(result)
        assert result.warnings == []

    def test_validate_services_known_service_no_warning(self):
        class NodeWithKnownService(ModularNode):
            CONTRACT = NodeContract(
                name="known_service_node",
                description="Known service node",
                reads=["request"],
                writes=["response"],
                services=["db_service"],
                supervisor="main",
                trigger_conditions=[TriggerCondition(priority=1)],
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                return NodeOutputs(response={"done": True})

        registry = NodeRegistry()
        registry.register(NodeWithKnownService)

        validator = ContractValidator(registry, known_services={"db_service"})
        result = validator.validate()
        assert not any("Unknown service" in w for w in result.warnings)

    def test_unknown_write_slice_detected(self):
        class NodeWithUnknownWrite(ModularNode):
            CONTRACT = NodeContract(
                name="unknown_write_node",
                description="Unknown write slice",
                reads=["request"],
                writes=["invalid_write"],
                supervisor="main",
                trigger_conditions=[TriggerCondition(priority=1)],
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                return NodeOutputs(response={"done": True})

        registry = NodeRegistry()
        registry.register(NodeWithUnknownWrite)
        validator = ContractValidator(registry)
        result = validator.validate()
        assert any("invalid_write" in e for e in result.errors)

    def test_validate_subgraphs_skips_missing_subgraph(self):
        class StubRegistry:
            def list_subgraphs(self):
                return ["missing_subgraph"]

            def get_subgraph(self, _subgraph_id):
                return None

            def get_all_nodes(self):
                return []

            def get_contract(self, _name):
                return None

        validator = ContractValidator(StubRegistry())
        result = ValidationResult()
        validator._validate_subgraphs(result)
        assert result.errors == []

    def test_validate_subgraphs_unknown_supervisor(self):
        registry = NodeRegistry()
        registry.register(ValidNode)

        contract = SubgraphContract(
            subgraph_id="sg_unknown_supervisor",
            description="Unknown supervisor subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="main",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_unknown_supervisor",
            supervisors=["ghost_supervisor"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(registry)
        result = validator.validate()
        assert any("unknown supervisor" in e for e in result.errors)

    def test_subgraph_boundary_violation_extra_writes(self):
        class SubgraphWriteViolationNode(ModularNode):
            CONTRACT = NodeContract(
                name="subgraph_write_violation",
                description="Subgraph write violation node",
                reads=["request"],
                writes=["response", "extra_output"],
                supervisor="subgraph_supervisor",
                trigger_conditions=[TriggerCondition(priority=1)],
            )

            async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
                return NodeOutputs(response={"ok": False})

        registry = NodeRegistry()
        registry.add_valid_slice("extra_output")
        registry.register(SubgraphWriteViolationNode)

        contract = SubgraphContract(
            subgraph_id="sg_write_violation",
            description="Write violation subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="subgraph_supervisor",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_write_violation",
            supervisors=["subgraph_supervisor"],
            nodes=["subgraph_write_violation"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(registry)
        result = validator.validate()
        assert any("writes undeclared slices" in e for e in result.errors)

    def test_resolve_subgraph_nodes_entrypoint_node(self):
        registry = NodeRegistry()
        registry.register(ValidNode)
        registry.register(AnotherValidNode)

        contract = SubgraphContract(
            subgraph_id="sg_entrypoint_node",
            description="Entrypoint node subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="valid_node",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_entrypoint_node",
            supervisors=["main"],
            nodes=None,
        )

        validator = ContractValidator(registry)
        nodes = validator._resolve_subgraph_nodes(contract, definition)
        assert "valid_node" in nodes

    def test_allowlist_valid_entries_no_warning(self):
        registry = NodeRegistry()
        registry.register(ValidNode)

        contract = SubgraphContract(
            subgraph_id="sg_allowlist_ok",
            description="Allowlist ok subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="main",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_allowlist_ok",
            supervisors=["main"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(
            registry,
            supervisor_allowlists={
                "main": {"done", "valid_node", "sg_allowlist_ok", "call_subgraph::sg_allowlist_ok"},
            },
        )
        result = validator.validate()
        assert not result.warnings

    def test_allowlist_call_subgraph_entry_skipped(self):
        registry = NodeRegistry()
        contract = SubgraphContract(
            subgraph_id="sg_allowlist_call",
            description="Allowlist call subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="main",
        )
        definition = SubgraphDefinition(
            subgraph_id="sg_allowlist_call",
            supervisors=["main"],
        )
        registry.register_subgraph(contract, definition)

        validator = ContractValidator(
            registry,
            supervisor_allowlists={"main": {"call_subgraph::sg_allowlist_call"}},
        )
        result = ValidationResult()
        validator._validate_allowlists(result)
        assert result.warnings == []

    def test_shared_writers_skips_missing_contract(self):
        class StubRegistry:
            def get_all_nodes(self):
                return ["ghost"]

            def get_contract(self, _name):
                return None

        validator = ContractValidator(StubRegistry())
        assert validator.get_shared_writers() == {}

    def test_slice_readers_skips_missing_contract(self):
        class StubRegistry:
            def get_all_nodes(self):
                return ["ghost"]

            def get_contract(self, _name):
                return None

        validator = ContractValidator(StubRegistry())
        assert validator.get_slice_readers() == {}
