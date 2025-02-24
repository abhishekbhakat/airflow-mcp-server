"""Test models for Airflow tool tests."""

from pydantic import BaseModel


class TestRequestModel(BaseModel):
    """Test request model."""

    path_id: int
    query_filter: str | None = None
    body_name: str
    body_value: int
