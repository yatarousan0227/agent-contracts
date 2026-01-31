"""Routing types for traceable supervisor decisions.

These types provide structured, explainable routing decisions
for debugging and observability.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_contracts.supervisor import SupervisorDecision


# =============================================================================
# Traceable Routing Types
# =============================================================================

class MatchedRule(BaseModel):
    """Represent a matched trigger condition.

    Args:
        - node: Node name that matched.
        - condition: Human-readable condition description.
        - priority: Trigger priority (higher evaluates first).
    Returns:
        - MatchedRule instance.
    """
    node: str = Field(description="Node name")
    condition: str = Field(description="Human-readable condition description")
    priority: int = Field(description="Trigger priority")


class RoutingReason(BaseModel):
    """Describe why a routing decision was made.

    Args:
        - decision_type: Decision category (rule_match, llm_decision, etc.).
        - matched_rules: Trigger rules that matched.
        - llm_used: Whether an LLM was used.
        - llm_reasoning: LLM reasoning summary if present.
    Returns:
        - RoutingReason instance.
    """
    decision_type: str = Field(
        description="Type of decision: terminal_state, explicit_routing, rule_match, llm_decision, fallback"
    )
    matched_rules: list[MatchedRule] = Field(
        default_factory=list,
        description="List of matched trigger rules"
    )
    llm_used: bool = Field(default=False, description="Whether LLM was used for decision")
    llm_reasoning: str | None = Field(default=None, description="LLM's reasoning if used")


class RoutingDecision(BaseModel):
    """Capture a traceable routing decision.

    Args:
        - selected_node: Node name selected for execution.
        - reason: Detailed routing reason payload.
    Returns:
        - RoutingDecision instance.
    """
    selected_node: str = Field(description="Selected node name")
    reason: RoutingReason = Field(description="Decision reason details")
    
    def to_supervisor_decision(self) -> "SupervisorDecision":
        """Convert to a simplified SupervisorDecision.

        Args:
            - None.
        Returns:
            - SupervisorDecision with condensed reasoning.
        """
        # Import here to avoid circular dependency
        from agent_contracts.supervisor import SupervisorDecision
        
        reasoning_parts = [self.reason.decision_type]
        if self.reason.matched_rules:
            rules_str = ", ".join(r.node for r in self.reason.matched_rules)
            reasoning_parts.append(f"candidates: [{rules_str}]")
        if self.reason.llm_used:
            reasoning_parts.append("LLM")
        return SupervisorDecision(
            next_node=self.selected_node,
            reasoning=" | ".join(reasoning_parts)
        )
