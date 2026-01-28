"""ModularNode and InteractiveNode - Base classes for nodes.

All nodes inherit from ModularNode and define a CONTRACT.
Contract-based I/O is automatically validated.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from agent_contracts.contracts import NodeContract, NodeInputs, NodeOutputs
from agent_contracts.config import get_config
from agent_contracts.errors import ContractViolationError
from agent_contracts.utils.logging import get_logger


class ModularNode(ABC):
    """Provide a base class for modular nodes.

    Args:
        - llm: Optional LangChain LLM instance.
        - **services: Named services declared in the node contract.
    Returns:
        - ModularNode instance.
    """
    
    # Subclasses must define this
    CONTRACT: ClassVar[NodeContract]
    
    def __init__(
        self,
        llm: BaseChatModel | None = None,
        **services: Any,
    ) -> None:
        """Initialize the node with services and optional LLM.

        Args:
            - llm: LangChain LLM (required if CONTRACT.requires_llm is True).
            - **services: Other services (declared in CONTRACT.services).
        Returns:
            - None.
        """
        self.logger = get_logger(self.__class__.__name__)
        self.llm = llm
        self._validated = False  # Deferred validation flag
        
        # Service injection
        self._services = services
        for service_name in self.CONTRACT.services:
            if service_name in services:
                setattr(self, service_name, services[service_name])
    
    def _validate_dependencies(self) -> None:
        """Validate declared dependencies from Contract.
        
        Called lazily on first execution to allow subclasses to set
        services after calling super().__init__().
        """
        if self._validated:
            return
        self._validated = True
        
        if self.CONTRACT.requires_llm and self.llm is None:
            self.logger.warning(
                f"Node {self.CONTRACT.name} requires LLM but none provided"
            )
        
        for service_name in self.CONTRACT.services:
            if not hasattr(self, service_name) or getattr(self, service_name) is None:
                self.logger.warning(
                    f"Node {self.CONTRACT.name} requires {service_name} but not provided"
                )
    
    @abstractmethod
    async def execute(
        self, 
        inputs: NodeInputs, 
        config: Optional[RunnableConfig] = None,
    ) -> NodeOutputs:
        """Execute the node's main processing logic.

        Args:
            - inputs: Input slices per CONTRACT.reads.
            - config: Optional RunnableConfig for LLM tracing.
        Returns:
            - Output slices per CONTRACT.writes.
        """
        pass
    
    async def __call__(
        self,
        state: dict,
        config: Optional[RunnableConfig] = None,
    ) -> dict[str, Any]:
        """Run as a LangGraph-compatible callable.

        Args:
            - state: Current agent state.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - State updates in LangGraph format.
        """
        # Deferred dependency validation (runs once on first call)
        self._validate_dependencies()
        
        # Extract input slices
        inputs = self._extract_inputs(state)
        
        # Merge config with node metadata (create new config to avoid mutation)
        base_config = config or {}
        existing_metadata = base_config.get("metadata", {})
        config = {
            **base_config,
            "metadata": {
                **existing_metadata,
                "node_name": self.CONTRACT.name,
                "node_supervisor": self.CONTRACT.supervisor,
                "node_type": self.__class__.__name__,
            },
        }
        
        # Execute
        try:
            # Execute
            outputs = await self.execute(inputs, config=config)
        except Exception as e:
            self.logger.error(f"Node {self.CONTRACT.name} execution failed: {e}")
            raise
        
        # Convert outputs to State update format
        return self._convert_outputs(outputs)
    
    def _extract_inputs(self, state: dict[str, Any]) -> NodeInputs:
        """Extract required slices from State.
        
        Only extracts slices declared in CONTRACT.reads
        and returns them as NodeInputs.
        """
        cfg = get_config()
        data = {}
        for slice_name in self.CONTRACT.reads:
            if slice_name == "_internal":
                data[slice_name] = state.get("_internal", {})
            else:
                data[slice_name] = state.get(slice_name, {})

        inputs = NodeInputs(**data)
        inputs._configure_contract_io(
            allowed_slices=set(self.CONTRACT.reads),
            node_name=self.CONTRACT.name,
            strict=cfg.io.strict,
            warn=cfg.io.warn,
            logger=self.logger,
        )
        return inputs
    
    def _convert_outputs(self, outputs: NodeOutputs) -> dict[str, Any]:
        """Convert NodeOutputs to LangGraph State update format.
        
        Expands from slice format to flat format.
        LangGraph expects a flat dict.
        """
        cfg = get_config()
        declared_writes = set(self.CONTRACT.writes)
        raw_updates = outputs.to_state_updates()
        extra_writes = sorted(set(raw_updates.keys()) - declared_writes)
        if extra_writes:
            msg = (
                f"Undeclared slice write(s) {extra_writes} in node '{self.CONTRACT.name}'"
            )
            if cfg.io.strict:
                raise ContractViolationError(msg)
            if cfg.io.warn:
                self.logger.warning(msg)
            if cfg.io.drop_undeclared_writes:
                for k in extra_writes:
                    raw_updates.pop(k, None)

        result = {}
        for slice_name, slice_data in raw_updates.items():
            if isinstance(slice_data, dict):
                result[slice_name] = slice_data
        return result
    
    # =========================================================================
    # Helper Methods (for subclasses)
    # =========================================================================
    
    def get_request_param(self, inputs: NodeInputs, key: str, default: Any = None) -> Any:
        """Fetch a parameter from the request slice.

        Args:
            - inputs: Node inputs containing the request slice.
            - key: Parameter key.
            - default: Default value when the key is missing.
        Returns:
            - Parameter value or default.
        """
        request = inputs.get_slice("request")
        params = request.get("params") or {}
        return params.get(key, default)
    
    def build_error_response(self, message: str, code: str) -> NodeOutputs:
        """Build a standardized error response output.

        Args:
            - message: Error message to include.
            - code: Error code string.
        Returns:
            - NodeOutputs containing an error response slice.
        """
        return NodeOutputs(
            response={
                "response_type": "error",
                "response_data": {"message": message, "code": code},
            }
        )


class InteractiveNode(ModularNode):
    """Provide a base class for conversational nodes.

    Args:
        - llm: Optional LangChain LLM instance.
        - **services: Named services declared in the node contract.
    Returns:
        - InteractiveNode instance.
    """
    
    @abstractmethod
    def prepare_context(self, inputs: NodeInputs) -> Any:
        """Prepare an execution context from inputs.

        Args:
            - inputs: Node inputs containing state slices.
        Returns:
            - Context object for subsequent steps.
        """
        pass
    
    @abstractmethod
    def check_completion(self, context: Any, inputs: NodeInputs) -> bool:
        """Check whether the interactive flow is complete.

        Args:
            - context: Prepared execution context.
            - inputs: Current node inputs.
        Returns:
            - True if the flow is complete, otherwise False.
        """
        pass
    
    @abstractmethod
    async def process_answer(
        self, 
        context: Any, 
        inputs: NodeInputs, 
        config: RunnableConfig | None = None
    ) -> bool:
        """Process the latest user answer, if present.

        Args:
            - context: Prepared execution context.
            - inputs: Current node inputs.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - True if the answer was processed and state updated.
        """
        pass
    
    @abstractmethod
    async def generate_question(
        self, 
        context: Any, 
        inputs: NodeInputs, 
        config: RunnableConfig | None = None
    ) -> NodeOutputs:
        """Generate the next question for the user.

        Args:
            - context: Prepared execution context.
            - inputs: Current node inputs.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - NodeOutputs containing the next question response.
        """
        pass

    async def create_completion_output(
        self, 
        context: Any, 
        inputs: NodeInputs,
        config: RunnableConfig | None = None
    ) -> NodeOutputs:
        """Create output when the flow is complete.

        Args:
            - context: Prepared execution context.
            - inputs: Current node inputs.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - NodeOutputs signaling completion (default: decision=done).
        """
        return NodeOutputs(_internal={"decision": "done"})
    
    async def execute(
        self, 
        inputs: NodeInputs, 
        config: Optional[RunnableConfig] = None,
    ) -> NodeOutputs:
        """Run the standard interactive execution flow.

        Args:
            - inputs: Node inputs containing state slices.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - NodeOutputs from completion or next question generation.
        """
        
        # 0. Prepare context
        context = self.prepare_context(inputs)
        
        # 1. Process answer
        await self.process_answer(context, inputs, config=config)
        
        # 2. Check completion
        if self.check_completion(context, inputs):
            return await self.create_completion_output(context, inputs, config=config)
            
        # 3. Generate question
        return await self.generate_question(context, inputs, config=config)
