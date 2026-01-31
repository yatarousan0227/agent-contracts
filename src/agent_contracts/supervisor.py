"""GenericSupervisor - Generic Supervisor.

Has no node-specific routing logic, determines routing via
Registry trigger conditions and LLM.
"""
from __future__ import annotations

import json
from typing import Any, Optional, Protocol, TypedDict

from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from agent_contracts.registry import NodeRegistry, TriggerMatch, get_node_registry
from agent_contracts.config import get_config
from agent_contracts.utils.logging import get_logger
from agent_contracts.utils.sanitize_context import sanitize_for_llm_util
from agent_contracts.routing import MatchedRule, RoutingReason, RoutingDecision

logger = get_logger("agent_contracts.supervisor")


class SupervisorDecision(BaseModel):
    """Represent a supervisor's routing decision.

    Args:
        - next_node: Next node name or "done".
        - reasoning: Human-readable reasoning summary.
    Returns:
        - SupervisorDecision instance.
    """
    next_node: str = Field(description="Next node name, or 'done'")
    reasoning: str = Field(default="", description="Decision reasoning")


class ContextBuilderResult(TypedDict, total=False):
    """Result from ContextBuilder.
    
    Attributes:
        slices: Set of slice names to include in LLM context (required)
        summary: Additional context summary as dict or string (optional)
    """
    slices: set[str]
    summary: dict | str | None


class ContextBuilder(Protocol):
    """Protocol for building context for LLM routing decisions.
    
    Allows customization of which state slices and additional context
    are passed to LLM for routing decisions.
    
    Example:
        def my_context_builder(state: dict, candidates: list[str]) -> dict:
            return {
                "slices": {"request", "response", "_internal", "conversation"},
                "summary": {
                    "total_turns": len(state.get("conversation", {}).get("messages", [])),
                    "readiness": 0.67,
                }
            }
        
        supervisor = GenericSupervisor(
            supervisor_name="workflow",
            llm=llm,
            context_builder=my_context_builder,
        )
    """
    
    def __call__(
        self,
        state: dict,
        candidates: list[str],
    ) -> ContextBuilderResult:
        """Build context for LLM routing decision.
        
        Args:
            state: Current agent state
            candidates: List of candidate node names from trigger evaluation
            
        Returns:
            ContextBuilderResult with:
                - "slices" (set[str]): Set of slice names to include in LLM context
                - "summary" (dict | str | None): Optional additional context summary.
                  Can be a dict (will be JSON-serialized) or pre-formatted string.
        """
        ...


class ExplicitRoutingHandler(Protocol):
    """Protocol for explicit routing (e.g., return-to-sender patterns).
    
    Allows applications to implement domain-specific routing logic that
    bypasses normal trigger evaluation.
    
    Example:
        def interview_router(state: dict) -> str | None:
            '''Route answers back to the node that asked the question.'''
            req = state.get("request", {})
            if req.get("action") == "answer":
                interview = state.get("interview", {})
                last_q = interview.get("last_question", {})
                if isinstance(last_q, dict):
                    return last_q.get("node_id")
            return None
        
        supervisor = GenericSupervisor(
            supervisor_name="workflow",
            llm=llm,
            explicit_routing_handler=interview_router,
        )
    """
    
    def __call__(self, state: dict) -> str | None:
        """Determine explicit routing target.
        
        Args:
            state: Current agent state
            
        Returns:
            Node name to route to, or None to continue with normal routing.
        """  
        ...


class GenericSupervisor:
    """Route to the next node using triggers and optional LLM.

    Args:
        - supervisor_name: Supervisor namespace to evaluate.
        - llm: Optional LangChain LLM instance.
        - registry: Optional NodeRegistry (defaults to global registry).
        - max_iterations: Optional max iteration count for safety.
        - terminal_response_types: Optional terminal response types.
        - context_builder: Optional context builder for LLM prompts.
        - max_field_length: Max field length for prompt sanitization.
        - explicit_routing_handler: Optional explicit routing handler.
    Returns:
        - GenericSupervisor instance.
    """
    
    def __init__(
        self,
        supervisor_name: str,
        llm: BaseChatModel | None = None,
        registry: NodeRegistry | None = None,
        max_iterations: int | None = None,
        terminal_response_types: set[str] | None = None,
        context_builder: ContextBuilder | None = None,
        max_field_length: int | None = None,
        explicit_routing_handler: ExplicitRoutingHandler | None = None,
    ) -> None:
        """Initialize the supervisor instance.

        Args:
            - supervisor_name: Supervisor namespace to evaluate.
            - llm: LangChain LLM instance (optional).
            - registry: Node registry (uses global if omitted).
            - max_iterations: Max iterations (uses config if omitted).
            - terminal_response_types: Terminal response types (uses config if omitted).
            - context_builder: Optional context builder for LLM routing.
            - max_field_length: Maximum field length for sanitization.
            - explicit_routing_handler: Optional explicit routing handler.
        Returns:
            - None.
        """
        self.name = supervisor_name
        self.llm = llm
        self.registry = registry or get_node_registry()
        self.logger = logger
        self.context_builder = context_builder
        self.max_field_length = max_field_length or 10000
        self.explicit_routing_handler = explicit_routing_handler
        
        # Load from config or use defaults
        config = get_config()
        self.max_iterations = max_iterations or config.supervisor.max_iterations
        self.terminal_response_types = terminal_response_types or set(
            config.supervisor.terminal_response_types
        )
    
    async def run(
        self,
        state: dict[str, Any],
        config: Optional[RunnableConfig] = None,
    ) -> dict[str, Any]:
        """Execute as a LangGraph node and update routing decision.

        Args:
            - state: Current agent state.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - State updates for the _internal slice.
        """
        # Iteration management
        internal = state.get("_internal", {})
        iteration_key = f"{self.name}_iteration"
        current_iteration = internal.get(iteration_key, 0)
        
        # Infinite loop prevention
        if current_iteration >= self.max_iterations:
            self.logger.warning(f"Max iterations ({self.max_iterations}) reached for {self.name}")
            return {
                "_internal": {
                    **internal,
                    "decision": "done",
                    iteration_key: current_iteration,
                }
            }
        
        # Decide
        decision = await self.decide(state, config)
        
        self.logger.info(
            f"{self.name} supervisor decision: {decision.next_node} ({decision.reasoning})"
        )
        
        return {
            "_internal": {
                **internal,
                "decision": decision.next_node,
                iteration_key: current_iteration + 1,
            }
        }
    
    async def decide(
        self,
        state: dict[str, Any],
        config: Optional[RunnableConfig] = None,
    ) -> SupervisorDecision:
        """Determine the next node with a simplified result.

        Args:
            - state: Current agent state.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - SupervisorDecision with selected node and reasoning.
        """
        routing_decision = await self.decide_with_trace(state, config)
        return routing_decision.to_supervisor_decision()
    
    def _check_immediate_rules(self, state: dict) -> str | None:
        """Check if should exit immediately.
        
        Returns 'done' for user input waiting or final states.
        """
        response = state.get("response", {})
        response_type = response.get("response_type")
        
        if response_type in self.terminal_response_types:
            return "done"
        
        return None
    
    def _select_top_matches(self, matches: list[TriggerMatch]) -> list[str]:
        """Select top candidates handling ties (Top 3 + Ties)."""
        if not matches:
            return []
            
        selected = []
        limit = 3
        last_prio = -1
        
        for i, match in enumerate(matches):
            if i < limit:
                selected.append(match.node_name)
                last_prio = match.priority
            elif match.priority == last_prio:
                selected.append(match.node_name)
            else:
                break
        return selected

    def _get_valid_targets(self) -> set[str]:
        """Return valid routing targets including CallSubgraph nodes."""
        valid_nodes = set(self.registry.get_supervisor_nodes(self.name))
        valid_nodes.add("done")
        for subgraph_id in self.registry.list_subgraphs():
            valid_nodes.add(f"call_subgraph::{subgraph_id}")
        return valid_nodes
    
    def _collect_context_slices(
        self,
        state: dict,
        rule_candidates: list[str],
    ) -> tuple[set[str], str]:
        """Collect state slices and build additional context for LLM routing.
        
        If a custom context_builder is provided, uses it to determine which
        slices to include and any additional context summary. Otherwise, uses
        minimal default context.
        
        Args:
            state: Current state
            rule_candidates: List of candidate node names from trigger evaluation
            
        Returns:
            Tuple of (slice_names, additional_context_string)
        """
        context_slices = {"request", "response", "_internal"}  # default
        additional_context = ""
        
        if self.context_builder:
            result = self.context_builder(state, rule_candidates)
            
            # Normalize slices to set
            slices_raw = result.get("slices", context_slices)
            context_slices = set(slices_raw) if not isinstance(slices_raw, set) else slices_raw
            
            # Handle summary - support both dict and string formats
            summary = result.get("summary")
            if summary is not None:
                if isinstance(summary, str):
                    # Already formatted as string
                    additional_context = f"\n\nAdditional Context:\n{summary}"
                else:
                    # Dict format - convert to JSON
                    summary_json = json.dumps(summary, ensure_ascii=False, default=str)
                    additional_context = f"\n\nAdditional Context:\n{summary_json}"
        
        return context_slices, additional_context
    
    
    def _format_rule_candidates_with_reasons(
        self,
        matches: list[TriggerMatch],
        candidates: list[str],
    ) -> str:
        """Format rule candidates with match reasons for LLM context.
        
        Example output:
            - data_processor (P95): matched because request.has_data=True
            - workflow_handler (P90): matched because request.action=process
        """
        if not candidates:
            return "(none)"
        
        lines = []
        for match in matches:
            if match.node_name not in candidates:
                continue
            
            contract = self.registry.get_contract(match.node_name)
            if not contract:
                lines.append(f"- {match.node_name} (P{match.priority})")
                continue
            
            # Use the actual matched condition
            condition = contract.trigger_conditions[match.condition_index]
            condition_str = ""
            if condition.when:
                parts = [f"{k}={v}" for k, v in condition.when.items()]
                condition_str = " AND ".join(parts)
            elif condition.when_not:
                parts = [f"NOT {k}={v}" for k, v in condition.when_not.items()]
                condition_str = " AND ".join(parts)
            else:
                condition_str = "(always)"
            
            lines.append(f"- {match.node_name} (P{match.priority}): matched because {condition_str}")
        
        return "\n".join(lines) if lines else "(none)"
    
    def _sanitize_for_llm(self, data: Any, max_str_length: int | None = None) -> Any:
        """Sanitize data for LLM prompt.
        
        Exclude large binary data (images, etc.) to reduce token consumption.
        
        Args:
            Data: to be sanitized
            max_str_length: Maximum string length (default: 10000)
            
        Returns:
            Sanitized data
        """
        return sanitize_for_llm_util(
            data,
            max_str_length=max_str_length or self.max_field_length,
            sanitize_binary_urls=True,
            base64_min_length=128,
            hex_min_length=128,
            classify_base64_magic=True,
        )
    
    async def _decide_with_llm(
        self,
        state: dict,
        matches: list[TriggerMatch],
        rule_candidates: list[str],
        child_decision: str | None,
        config: Optional[RunnableConfig] = None,
    ) -> SupervisorDecision | None:
        """Decide using LLM with enriched context.
        
        Builds context from:
        1. Base slices (request, response, _internal) - directly serialized as JSON
        2. Rule match reasons
        3. Previous node suggestion
        """
        try:
            # Collect relevant slices and additional context
            context_slices, additional_context = self._collect_context_slices(
                state, rule_candidates
            )
            
            # Build state summary using direct JSON serialization with sanitization
            state_parts = []
            for slice_name in sorted(context_slices):
                if slice_name in state:
                    slice_data = state[slice_name]
                    # サApply sanitization
                    sanitized_data = self._sanitize_for_llm(slice_data)
                    slice_json = json.dumps(sanitized_data, ensure_ascii=False, default=str)
                    state_parts.append(f"{slice_name}: {slice_json}")
            
            state_summary = "\n".join(state_parts) if state_parts else "(no state)"
            
            # Format candidates with match reasons
            candidates_with_reasons = self._format_rule_candidates_with_reasons(
                matches, rule_candidates
            )
            
            # Build full context
            context = f"""
Current State:
{state_summary}{additional_context}

High priority system rules suggest:
{candidates_with_reasons}

Last active node suggested: {child_decision or 'None'}
"""
            
            # Build prompt with context embedded
            prompt = self.registry.build_llm_prompt(self.name, state, context=context)
            
            # Use LangChain structured output
            structured_llm = self.llm.with_structured_output(SupervisorDecision)
            result = await structured_llm.ainvoke(
                f"System: You are a decision-making supervisor for a {self.name} flow. "
                f"If 'High priority system rules' are provided, you MUST select one of them. "
                f"Otherwise, prioritize user intent.\n\n{prompt}",
                config=config,
            )
            
            # Validate LLM decision against valid nodes
            valid_nodes = self._get_valid_targets()
            
            if result.next_node not in valid_nodes:
                self.logger.warning(
                    f"LLM returned invalid node: {result.next_node}, "
                    f"valid nodes: {valid_nodes}"
                )
                # If rule candidates exist, use the top one
                if rule_candidates:
                    return SupervisorDecision(
                        next_node=rule_candidates[0],
                        reasoning=f"LLM returned invalid '{result.next_node}', using rule candidate"
                    )
                # Otherwise return None to trigger fallback
                return None
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM decision failed: {e}")
            return None
    
    def _build_matched_rules(
        self,
        matches: list[TriggerMatch],
    ) -> list[MatchedRule]:
        """Build MatchedRule list from trigger matches."""
        matched_rules = []
        
        for match in matches:
            contract = self.registry.get_contract(match.node_name)
            if not contract:
                continue
            
            # Use the actual matched condition
            condition = contract.trigger_conditions[match.condition_index]
            condition_str = ""
            if condition.when:
                parts = [f"{k}={v}" for k, v in condition.when.items()]
                condition_str = " AND ".join(parts)
            elif condition.when_not:
                parts = [f"NOT {k}={v}" for k, v in condition.when_not.items()]
                condition_str = " AND ".join(parts)
            else:
                condition_str = "(always)"
            
            matched_rules.append(MatchedRule(
                node=match.node_name,
                condition=condition_str or "(unknown)",
                priority=match.priority,
            ))
        
        return matched_rules
    
    async def decide_with_trace(
        self,
        state: dict[str, Any],
        config: Optional[RunnableConfig] = None,
    ) -> RoutingDecision:
        """Determine the next node with traceable reasoning.

        Args:
            - state: Current agent state.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - RoutingDecision with detailed reasoning.
        """
        # Enhance trace config (create new config to avoid mutation)
        base_config = config or {}
        existing_metadata = base_config.get("metadata", {})
        existing_tags = base_config.get("tags", [])
        config = {
            **base_config,
            "metadata": {
                **existing_metadata,
                "supervisor_name": self.name,
                "supervisor_iteration": state.get("_internal", {}).get(f"{self.name}_iteration", 0),
            },
            "tags": [*existing_tags, "supervisor_decision"],
        }
        
        # Phase 0: Immediate exit check (terminal state)
        immediate = self._check_immediate_rules(state)
        if immediate:
            return RoutingDecision(
                selected_node=immediate,
                reason=RoutingReason(decision_type="terminal_state")
            )
        
        # Phase 0.5: Explicit Routing (via pluggable handler)
        if self.explicit_routing_handler:
            explicit_target = self.explicit_routing_handler(state)
            if explicit_target:
                # Validate that the explicit target is a valid node
                valid_nodes = self._get_valid_targets()
                
                if explicit_target not in valid_nodes:
                    self.logger.warning(
                        f"explicit_routing_handler returned invalid node: '{explicit_target}', "
                        f"valid nodes: {valid_nodes}. Falling back to normal routing."
                    )
                    # Fall through to normal routing instead of using invalid node
                else:
                    return RoutingDecision(
                        selected_node=explicit_target,
                        reason=RoutingReason(decision_type="explicit_routing")
                    )

        # Phase 1: Rule-based evaluation
        matches = self.registry.evaluate_triggers(self.name, state)
        matched_rules = self._build_matched_rules(matches)
        
        # Smart selection for LLM context (Top 3 + Ties)
        rule_candidates = self._select_top_matches(matches)
        
        # Child node suggestion
        internal = state.get("_internal", {})
        previous_decision = internal.get("decision")
        
        child_decision = None
        if previous_decision and previous_decision != "done":
            child_decision = previous_decision
        
        # Phase 2: LLM decision
        if self.llm:
            llm_result = await self._decide_with_llm(
                state,
                matches,
                rule_candidates,
                child_decision,
                config=config,
            )
            if llm_result:
                return RoutingDecision(
                    selected_node=llm_result.next_node,
                    reason=RoutingReason(
                        decision_type="llm_decision",
                        matched_rules=matched_rules,
                        llm_used=True,
                        llm_reasoning=llm_result.reasoning,
                    )
                )
        
        # Phase 3: Fallback
        if matches:
            return RoutingDecision(
                selected_node=matches[0].node_name,
                reason=RoutingReason(
                    decision_type="rule_match",
                    matched_rules=matched_rules,
                )
            )
        
        if child_decision:
            return RoutingDecision(
                selected_node=child_decision,
                reason=RoutingReason(decision_type="fallback")
            )
            
        return RoutingDecision(
            selected_node="done",
            reason=RoutingReason(decision_type="fallback")
        )
    
    async def __call__(
        self,
        state: dict[str, Any],
        config: Optional[RunnableConfig] = None,
    ) -> dict[str, Any]:
        """Invoke the supervisor as a LangGraph-compatible callable.

        Args:
            - state: Current agent state.
            - config: Optional RunnableConfig for tracing.
        Returns:
            - State updates for the _internal slice.
        """
        return await self.run(state, config)
