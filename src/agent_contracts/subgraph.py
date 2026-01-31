"""Subgraph contract types for hierarchical execution."""
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class SubgraphContract(BaseModel):
    """Declare the I/O contract for a subgraph.

    Args:
        - subgraph_id: Unique identifier for the subgraph.
        - description: Human-readable description.
        - reads: Slice names the subgraph reads.
        - writes: Slice names the subgraph writes.
        - entrypoint: Entry node or supervisor name within the subgraph.
        - input_schema: Optional input schema model class.
        - output_schema: Optional output schema model class.
    Returns:
        - SubgraphContract instance.
    """
    model_config = ConfigDict(frozen=True)

    subgraph_id: str = Field(description="Unique subgraph identifier")
    description: str = Field(description="Human-readable description")
    reads: list[str] = Field(description="List of slice names the subgraph reads")
    writes: list[str] = Field(description="List of slice names the subgraph writes")
    entrypoint: str = Field(description="Subgraph entry node or supervisor")
    input_schema: type[BaseModel] | None = Field(
        default=None,
        description="Optional input schema model",
    )
    output_schema: type[BaseModel] | None = Field(
        default=None,
        description="Optional output schema model",
    )


class SubgraphDefinition(BaseModel):
    """Define which supervisors or nodes belong to a subgraph.

    Args:
        - subgraph_id: Unique identifier for the subgraph.
        - supervisors: Supervisor names included in the subgraph.
        - nodes: Node names included in the subgraph.
    Returns:
        - SubgraphDefinition instance.
    """
    model_config = ConfigDict(frozen=True)

    subgraph_id: str = Field(description="Unique subgraph identifier")
    supervisors: list[str] | None = Field(
        default=None,
        description="List of supervisor names to include",
    )
    nodes: list[str] | None = Field(
        default=None,
        description="List of node names to include",
    )
