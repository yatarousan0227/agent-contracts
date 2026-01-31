"""Contract diff utilities.

Provides structured diffs between two sets of NodeContracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_SEVERITY_ORDER = {
    "nonbreaking": 0,
    "behavioral": 1,
    "breaking": 2,
}


@dataclass
class NodeChange:
    """Describe a node-level contract change.

    Args:
        - node: Node name.
        - severity: Severity level (nonbreaking, behavioral, breaking).
        - details: List of change detail strings.
    Returns:
        - NodeChange instance.
    """
    node: str
    severity: str
    details: list[str] = field(default_factory=list)


@dataclass
class ContractDiffReport:
    """Summarize differences between two contract sets.

    Args:
        - added: Added node names.
        - removed: Removed node names.
        - changes: List of node-level changes.
    Returns:
        - ContractDiffReport instance.
    """
    added: list[str]
    removed: list[str]
    changes: list[NodeChange]

    def has_breaking(self) -> bool:
        """Check if the diff includes breaking changes.

        Args:
            - None.
        Returns:
            - True if breaking changes exist.
        """
        if self.removed:
            return True
        return any(c.severity == "breaking" for c in self.changes)

    def to_text(self) -> str:
        """Format the diff as human-readable text.

        Args:
            - None.
        Returns:
            - Human-readable diff summary.
        """
        lines: list[str] = []
        if self.added:
            lines.append("Added nodes:")
            for node in self.added:
                lines.append(f"- {node}")
            lines.append("")

        if self.removed:
            lines.append("Removed nodes:")
            for node in self.removed:
                lines.append(f"- {node}")
            lines.append("")

        grouped = {"breaking": [], "behavioral": [], "nonbreaking": []}
        for change in self.changes:
            grouped[change.severity].append(change)

        for severity in ("breaking", "behavioral", "nonbreaking"):
            items = grouped[severity]
            if not items:
                continue
            lines.append(f"{severity.capitalize()} changes:")
            for change in items:
                lines.append(f"- {change.node}")
                for detail in change.details:
                    lines.append(f"  - {detail}")
            lines.append("")

        return "\n".join(lines).strip() or "No changes detected."


def diff_contracts(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> ContractDiffReport:
    """Compute a structured diff between contract dictionaries.

    Args:
        - before: Exported contracts from the previous version.
        - after: Exported contracts from the new version.
    Returns:
        - ContractDiffReport with added/removed/changed nodes.
    """
    before_nodes = set(before.keys())
    after_nodes = set(after.keys())

    added = sorted(after_nodes - before_nodes)
    removed = sorted(before_nodes - after_nodes)
    changes: list[NodeChange] = []

    for node in sorted(before_nodes & after_nodes):
        before_contract = before[node]
        after_contract = after[node]
        node_change = _diff_node_contract(node, before_contract, after_contract)
        if node_change:
            changes.append(node_change)

    return ContractDiffReport(added=added, removed=removed, changes=changes)


def _diff_node_contract(
    node: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> NodeChange | None:
    details: list[str] = []
    severity = "nonbreaking"

    def bump(new_severity: str) -> None:
        nonlocal severity
        if _SEVERITY_ORDER[new_severity] > _SEVERITY_ORDER[severity]:
            severity = new_severity

    # Simple field changes
    if before.get("supervisor") != after.get("supervisor"):
        details.append(
            f"supervisor: {before.get('supervisor')} -> {after.get('supervisor')}"
        )
        bump("breaking")

    if before.get("requires_llm") != after.get("requires_llm"):
        details.append(
            f"requires_llm: {before.get('requires_llm')} -> {after.get('requires_llm')}"
        )
        if before.get("requires_llm") is False and after.get("requires_llm") is True:
            bump("breaking")
        else:
            bump("behavioral")

    if before.get("is_terminal") != after.get("is_terminal"):
        details.append(
            f"is_terminal: {before.get('is_terminal')} -> {after.get('is_terminal')}"
        )
        bump("behavioral")

    if before.get("description") != after.get("description"):
        details.append("description changed")

    if before.get("icon") != after.get("icon"):
        details.append("icon changed")

    # List/set changes
    _diff_list_field(
        "reads",
        before.get("reads", []),
        after.get("reads", []),
        details,
        bump,
        removed_severity="behavioral",
        added_severity="behavioral",
    )
    _diff_list_field(
        "writes",
        before.get("writes", []),
        after.get("writes", []),
        details,
        bump,
        removed_severity="breaking",
        added_severity="behavioral",
    )
    _diff_list_field(
        "services",
        before.get("services", []),
        after.get("services", []),
        details,
        bump,
        removed_severity="behavioral",
        added_severity="behavioral",
    )

    # Trigger conditions
    before_conditions = before.get("trigger_conditions", [])
    after_conditions = after.get("trigger_conditions", [])
    if before_conditions != after_conditions:
        details.append(
            f"trigger_conditions changed ({len(before_conditions)} -> {len(after_conditions)})"
        )
        bump("behavioral")

    if not details:
        return None
    return NodeChange(node=node, severity=severity, details=details)


def _diff_list_field(
    field_name: str,
    before_list: list[Any],
    after_list: list[Any],
    details: list[str],
    bump: Any,
    *,
    removed_severity: str,
    added_severity: str,
) -> None:
    before_set = set(before_list)
    after_set = set(after_list)
    added = sorted(after_set - before_set)
    removed = sorted(before_set - after_set)
    if not added and not removed:
        return

    parts = []
    if added:
        parts.append(f"+{', '.join(added)}")
        bump(added_severity)
    if removed:
        parts.append(f"-{', '.join(removed)}")
        bump(removed_severity)

    details.append(f"{field_name}: {' '.join(parts)}")
