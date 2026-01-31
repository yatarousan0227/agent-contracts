"""Framework exceptions."""

from __future__ import annotations


class ContractViolationError(RuntimeError):
    """Signal a node contract I/O violation.

    Args:
        - message: Error message describing the violation.
    Returns:
        - ContractViolationError instance.
    """
