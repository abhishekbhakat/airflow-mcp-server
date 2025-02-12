"""Tests for ToolManager."""

import logging
from pathlib import Path

import pytest
import pytest_asyncio
from airflow_mcp_server.tools.airflow_tool import AirflowTool
from airflow_mcp_server.tools.tool_manager import ToolManager, ToolManagerError, ToolNotFoundError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def tool_manager(mock_spec_file):
    """Create ToolManager instance for testing."""
    manager = ToolManager(
        spec_path=mock_spec_file,
        base_url="http://test",
        auth_token="test-token",
        max_cache_size=2,
    )
    async with manager as m:
        yield m


@pytest.mark.asyncio
async def test_get_tool_success(tool_manager):
    """Test successful tool retrieval."""
    tool = await tool_manager.get_tool("get_dags")
    assert isinstance(tool, AirflowTool)
    assert tool.operation.operation_id == "get_dags"


@pytest.mark.asyncio
async def test_get_tool_not_found(tool_manager):
    """Test error handling for non-existent tool."""
    with pytest.raises(ToolNotFoundError):
        await tool_manager.get_tool("invalid_operation")


@pytest.mark.asyncio
async def test_tool_caching(tool_manager):
    """Test tool caching behavior."""
    # Get same tool twice
    tool1 = await tool_manager.get_tool("get_dags")
    tool2 = await tool_manager.get_tool("get_dags")
    assert tool1 is tool2  # Should be same instance

    # Check cache info
    cache_info = tool_manager.cache_info
    assert cache_info["size"] == 1
    assert "get_dags" in cache_info["operations"]


@pytest.mark.asyncio
async def test_cache_eviction(tool_manager):
    """Test cache eviction with size limit."""
    # Fill cache beyond limit
    await tool_manager.get_tool("get_dags")
    await tool_manager.get_tool("get_dag")
    await tool_manager.get_tool("post_dag_run")  # Should evict oldest

    cache_info = tool_manager.cache_info
    assert cache_info["size"] == 2  # Max size
    assert "get_dags" not in cache_info["operations"]  # Should be evicted
    assert "get_dag" in cache_info["operations"]
    assert "post_dag_run" in cache_info["operations"]


@pytest.mark.asyncio
async def test_clear_cache(tool_manager):
    """Test cache clearing."""
    await tool_manager.get_tool("get_dags")
    tool_manager.clear_cache()
    assert tool_manager.cache_info["size"] == 0


@pytest.mark.asyncio
async def test_concurrent_access(tool_manager):
    """Test concurrent tool access."""
    import asyncio

    # Create multiple concurrent requests
    tasks = [
        tool_manager.get_tool("get_dags"),
        tool_manager.get_tool("get_dags"),
        tool_manager.get_tool("get_dag"),
    ]

    # Should handle concurrent access without errors
    results = await asyncio.gather(*tasks)
    assert all(isinstance(tool, AirflowTool) for tool in results)
    assert results[0] is results[1]  # Same tool instance
    assert results[0] is not results[2]  # Different tools


@pytest.mark.asyncio
async def test_client_lifecycle(mock_spec_file):
    """Test proper client lifecycle management."""
    manager = ToolManager(
        spec_path=mock_spec_file,
        base_url="http://test",
        auth_token="test",
    )

    # Before context
    assert not hasattr(manager._client, "_session")

    async with manager:
        # Inside context
        tool = await manager.get_tool("get_dags")
        assert tool.client._session is not None

    # After context
    assert not hasattr(tool.client, "_session")


@pytest.mark.asyncio
async def test_initialization_error():
    """Test error handling during initialization."""
    with pytest.raises(ToolManagerError):
        ToolManager(
            spec_path="invalid_path",
            base_url="http://test",
            auth_token="test",
        )


@pytest.mark.asyncio
async def test_invalid_cache_size():
    """Test error handling for invalid cache size."""
    with pytest.raises(ToolManagerError, match="Invalid configuration: max_cache_size must be positive"):
        ToolManager(
            spec_path=Path("dummy"),
            base_url="http://test",
            auth_token="test",
            max_cache_size=0,
        )


@pytest.mark.asyncio
async def test_missing_required_params():
    """Test error handling for missing required parameters."""
    with pytest.raises(ToolManagerError, match="Invalid configuration: spec_path is required"):
        ToolManager(spec_path="", base_url="http://test", auth_token="test")

    with pytest.raises(ToolManagerError, match="Invalid configuration: base_url is required"):
        ToolManager(spec_path=Path("dummy"), base_url="", auth_token="test")

    with pytest.raises(ToolManagerError, match="Invalid configuration: auth_token is required"):
        ToolManager(spec_path=Path("dummy"), base_url="http://test", auth_token="")
