from pydantic import BaseModel, model_validator


# DAG operations
# ====================================================================
class ListDags(BaseModel):
    """Parameters for listing DAGs."""

    limit: int | None
    offset: int | None
    order_by: str | None
    tags: list[str] | None
    only_active: bool
    paused: bool | None
    fields: list[str] | None
    dag_id_pattern: str | None

    @model_validator(mode="after")
    def validate_offset(self) -> "ListDags":
        if self.offset is not None and self.offset < 0:
            raise ValueError("offset must be non-negative")
        return self
