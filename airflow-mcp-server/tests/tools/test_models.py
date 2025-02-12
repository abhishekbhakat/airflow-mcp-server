"""Test models for Airflow tool tests."""

from pydantic import BaseModel


class TestRequestModel(BaseModel):
    """Test request model."""

    name: str
    value: int


class TestResponseModel(BaseModel):
    """Test response model."""

    item_id: int
    result: str
