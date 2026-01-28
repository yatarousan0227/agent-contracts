"""ContractValidator - Static validation for node contracts.

Validates contracts at registration time to catch configuration
errors before runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agent_contracts.utils.logging import get_logger

if TYPE_CHECKING:
    from agent_contracts.registry import NodeRegistry

logger = get_logger("agent_contracts.validator")


# =============================================================================
# Validation Result
# =============================================================================

@dataclass
class ValidationResult:
    """Capture contract validation results.

    Args:
        - errors: Fatal issues that prevent execution.
        - warnings: Non-fatal issues that deserve attention.
        - info: Informational messages.
    Returns:
        - ValidationResult instance.
    """
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """Check whether errors were recorded.

        Args:
            - None.
        Returns:
            - True if errors exist, otherwise False.
        """
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check whether warnings were recorded.

        Args:
            - None.
        Returns:
            - True if warnings exist, otherwise False.
        """
        return len(self.warnings) > 0
    
    @property
    def is_valid(self) -> bool:
        """Check whether validation passed without errors.

        Args:
            - None.
        Returns:
            - True if no errors were recorded.
        """
        return not self.has_errors
    
    def __str__(self) -> str:
        """Render the validation result as text.

        Args:
            - None.
        Returns:
            - Human-readable validation summary.
        """
        lines = []
        
        if self.errors:
            lines.append("ERRORS:")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        if self.warnings:
            lines.append("WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        if self.info:
            lines.append("INFO:")
            for info_msg in self.info:
                lines.append(f"  - {info_msg}")
        
        if not lines:
            lines.append("✅ All validations passed")
        
        return "\n".join(lines)


# =============================================================================
# Contract Validator
# =============================================================================

class ContractValidator:
    """Validate registered node contracts.

    Args:
        - registry: NodeRegistry instance to validate.
        - known_services: Optional set of known service names.
        - strict: Treat warnings as errors when True.
    Returns:
        - ContractValidator instance.
    """
    
    def __init__(
        self,
        registry: "NodeRegistry",
        known_services: set[str] | None = None,
        strict: bool = False,
    ) -> None:
        """Initialize the contract validator.

        Args:
            - registry: Node registry to validate.
            - known_services: Known service names for validation.
            - strict: Treat warnings as errors.
        Returns:
            - None.
        """
        self._registry = registry
        self._known_services = known_services
        self._strict = strict
    
    def validate(self) -> ValidationResult:
        """Run all validation checks.

        Args:
            - None.
        Returns:
            - ValidationResult with errors, warnings, and info.
        """
        result = ValidationResult()
        
        # Run validations
        self._validate_slices(result)
        self._validate_services(result)
        self._validate_reachability(result)
        self._report_shared_writers(result)
        self._apply_strict_mode(result)
        
        # Log summary
        if result.has_errors:
            logger.error(f"Contract validation failed: {len(result.errors)} errors")
        elif result.has_warnings:
            logger.warning(f"Contract validation passed with {len(result.warnings)} warnings")
        else:
            logger.info("Contract validation passed")
        
        return result
    
    def _validate_slices(self, result: ValidationResult) -> None:
        """Validate that all slice names are known."""
        valid_slices = self._registry._valid_slices
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            # Check reads
            for slice_name in contract.reads:
                if slice_name not in valid_slices:
                    result.errors.append(
                        f"Unknown slice '{slice_name}' in node '{name}' reads"
                    )
            
            # Check writes
            for slice_name in contract.writes:
                if slice_name not in valid_slices:
                    result.errors.append(
                        f"Unknown slice '{slice_name}' in node '{name}' writes"
                    )
                if slice_name == "request":
                    result.warnings.append(
                        f"Writing to 'request' slice is discouraged (node '{name}')"
                    )
    
    def _validate_services(self, result: ValidationResult) -> None:
        """Validate that required services are known."""
        if self._known_services is None:
            return  # Skip if no known services provided
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            for service_name in contract.services:
                if service_name not in self._known_services:
                    result.warnings.append(
                        f"Unknown service '{service_name}' required by node '{name}'"
                    )
    
    def _validate_reachability(self, result: ValidationResult) -> None:
        """Check for orphan/unreachable nodes."""
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            # Check for orphan (no supervisor)
            if not contract.supervisor:
                result.warnings.append(
                    f"Node '{name}' has no supervisor (orphan)"
                )
                continue
            
            # Check for unreachable (no trigger conditions)
            if not contract.trigger_conditions:
                result.warnings.append(
                    f"Node '{name}' has no trigger conditions (may be unreachable)"
                )
    
    def _report_shared_writers(self, result: ValidationResult) -> None:
        """Report slices with multiple writers (informational)."""
        shared_writers = self.get_shared_writers()
        
        for slice_name, writers in shared_writers.items():
            if len(writers) > 1:
                writers_str = ", ".join(sorted(writers))
                result.info.append(
                    f"Shared writers for '{slice_name}': {writers_str}"
                )

    def _apply_strict_mode(self, result: ValidationResult) -> None:
        """Convert warnings to errors in strict mode."""
        if not self._strict or not result.warnings:
            return
        result.errors.extend([f"STRICT: {warning}" for warning in result.warnings])
        result.warnings = []
    
    def get_shared_writers(self) -> dict[str, list[str]]:
        """Get slices and their writer nodes.

        Args:
            - None.
        Returns:
            - Mapping of slice name to writer node names.
        """
        writers: dict[str, list[str]] = {}
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            for slice_name in contract.writes:
                if slice_name not in writers:
                    writers[slice_name] = []
                writers[slice_name].append(name)
        
        return writers
    
    def get_slice_readers(self) -> dict[str, list[str]]:
        """Get slices and their reader nodes.

        Args:
            - None.
        Returns:
            - Mapping of slice name to reader node names.
        """
        readers: dict[str, list[str]] = {}
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            for slice_name in contract.reads:
                if slice_name not in readers:
                    readers[slice_name] = []
                readers[slice_name].append(name)
        
        return readers
    
    def get_unused_slices(self) -> dict[str, str]:
        """Find slices that are write-only or read-only.

        Args:
            - None.
        Returns:
            - Mapping of slice name to usage type.
        """
        writers = self.get_shared_writers()
        readers = self.get_slice_readers()
        
        all_slices = set(writers.keys()) | set(readers.keys())
        unused: dict[str, str] = {}
        
        for slice_name in all_slices:
            has_writers = slice_name in writers and len(writers[slice_name]) > 0
            has_readers = slice_name in readers and len(readers[slice_name]) > 0
            
            if has_writers and not has_readers:
                unused[slice_name] = "write_only"
            elif has_readers and not has_writers:
                # Read-only is only a concern for non-input slices
                if slice_name != "request":
                    unused[slice_name] = "read_only"
        
        return unused
