"""Tool manager for handling Airflow API tool instantiation and caching."""

import asyncio
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any

from airflow_mcp_server.client.airflow_client import AirflowClient
from airflow_mcp_server.parser.operation_parser import OperationParser
from airflow_mcp_server.tools.airflow_dag_tools import AirflowDagTools
from airflow_mcp_server.tools.airflow_tool import AirflowTool

logger = logging.getLogger(__name__)

# Keep existing function for backward compatibility
_dag_tools: AirflowDagTools | None = None


def get_airflow_dag_tools() -> AirflowDagTools:
    global _dag_tools
    if not _dag_tools:
        _dag_tools = AirflowDagTools()
    return _dag_tools


class ToolManagerError(Exception):
    """Base exception for tool manager errors."""

    pass


class ToolInitializationError(ToolManagerError):
    """Error during tool initialization."""

    pass


class ToolNotFoundError(ToolManagerError):
    """Error when requested tool is not found."""

    pass


class ToolManager:
    """Manager for Airflow API tools with caching and lifecycle management.

    This class provides a centralized way to manage Airflow API tools with:
    - Singleton client management
    - Tool caching with size limits
    - Thread-safe access
    - Proper error handling
    """

    def __init__(
        self,
        spec_path: Path | str | object,
        base_url: str,
        auth_token: str,
        max_cache_size: int = 100,
    ) -> None:
        """Initialize tool manager.

        Args:
            spec_path: Path to OpenAPI spec file or file-like object
            base_url: Base URL for Airflow API
            auth_token: Authentication token
            max_cache_size: Maximum number of tools to cache (default: 100)

        Raises:
            ToolManagerError: If initialization fails
            ToolInitializationError: If client or parser initialization fails
        """
        try:
            # Validate inputs
            if not spec_path:
                raise ValueError("spec_path is required")
            if not base_url:
                raise ValueError("base_url is required")
            if not auth_token:
                raise ValueError("auth_token is required")
            if max_cache_size < 1:
                raise ValueError("max_cache_size must be positive")

            # Store configuration
            self._spec_path = spec_path
            self._base_url = base_url.rstrip("/")
            self._auth_token = auth_token
            self._max_cache_size = max_cache_size

            # Initialize core components with proper error handling
            try:
                self._client = AirflowClient(spec_path, self._base_url, auth_token)
                logger.info("AirflowClient initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize AirflowClient: %s", e)
                raise ToolInitializationError(f"Failed to initialize client: {e}") from e

            try:
                self._parser = OperationParser(spec_path)
                logger.info("OperationParser initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize OperationParser: %s", e)
                raise ToolInitializationError(f"Failed to initialize parser: {e}") from e

            # Setup thread safety and caching
            self._lock = asyncio.Lock()
            self._tool_cache: OrderedDict[str, AirflowTool] = OrderedDict()

            logger.info("Tool manager initialized successfully (cache_size=%d, base_url=%s)", max_cache_size, self._base_url)
        except ValueError as e:
            logger.error("Invalid configuration: %s", e)
            raise ToolManagerError(f"Invalid configuration: {e}") from e
        except Exception as e:
            logger.error("Failed to initialize tool manager: %s", e)
            raise ToolInitializationError(f"Component initialization failed: {e}") from e

    async def __aenter__(self) -> "ToolManager":
        """Enter async context."""
        try:
            if not hasattr(self, "_client"):
                logger.error("Client not initialized")
                raise ToolInitializationError("Client not initialized")
            await self._client.__aenter__()
            return self
        except Exception as e:
            logger.error("Failed to enter async context: %s", e)
            if hasattr(self, "_client"):
                try:
                    await self._client.__aexit__(None, None, None)
                except Exception:
                    pass
            raise ToolInitializationError(f"Failed to initialize client session: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        try:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            logger.error("Error during context exit: %s", e)
        finally:
            self.clear_cache()

    def _evict_cache_if_needed(self) -> None:
        """Evict oldest items from cache if size limit is reached.

        This method uses FIFO (First In First Out) eviction policy.
        Eviction occurs when cache reaches max_cache_size.
        """
        current_size = len(self._tool_cache)
        if current_size >= self._max_cache_size:
            logger.info("Cache limit reached (%d/%d). Starting eviction.", current_size, self._max_cache_size)
            logger.debug("Current cache contents: %s", list(self._tool_cache.keys()))

            evicted_count = 0
            while len(self._tool_cache) >= self._max_cache_size:
                operation_id, _ = self._tool_cache.popitem(last=False)
                evicted_count += 1
                logger.debug("Evicted tool %s from cache (size: %d/%d)", operation_id, len(self._tool_cache), self._max_cache_size)

            if evicted_count > 0:
                logger.info("Evicted %d tools from cache", evicted_count)

    async def get_tool(self, operation_id: str) -> AirflowTool:
        """Get or create a tool instance for the given operation.

        Args:
            operation_id: Operation ID from OpenAPI spec

        Returns:
            AirflowTool instance

        Raises:
            ToolNotFoundError: If operation not found
            ToolInitializationError: If tool creation fails
            ValueError: If operation_id is invalid
        """
        if not operation_id or not isinstance(operation_id, str):
            logger.error("Invalid operation_id provided: %s", operation_id)
            raise ValueError("Invalid operation_id")

        if not hasattr(self, "_client") or not hasattr(self, "_parser"):
            logger.error("ToolManager not properly initialized")
            raise ToolInitializationError("ToolManager components not initialized")

        logger.debug("Requesting tool for operation: %s", operation_id)

        async with self._lock:
            # Check cache first
            if operation_id in self._tool_cache:
                logger.debug("Tool cache hit for %s", operation_id)
                return self._tool_cache[operation_id]

            logger.debug("Tool cache miss for %s, creating new instance", operation_id)

            try:
                # Parse operation details
                try:
                    operation_details = self._parser.parse_operation(operation_id)
                except ValueError as e:
                    logger.error("Operation %s not found: %s", operation_id, e)
                    raise ToolNotFoundError(f"Operation {operation_id} not found") from e
                except Exception as e:
                    logger.error("Failed to parse operation %s: %s", operation_id, e)
                    raise ToolInitializationError(f"Operation parsing failed: {e}") from e

                # Create new tool instance
                try:
                    tool = AirflowTool(operation_details, self._client)
                except Exception as e:
                    logger.error("Failed to create tool instance for %s: %s", operation_id, e)
                    raise ToolInitializationError(f"Tool instantiation failed: {e}") from e

                # Update cache
                self._evict_cache_if_needed()
                self._tool_cache[operation_id] = tool
                logger.info("Created and cached new tool for %s", operation_id)

                return tool

            except (ToolNotFoundError, ToolInitializationError):
                raise
            except Exception as e:
                logger.error("Unexpected error creating tool for %s: %s", operation_id, e)
                raise ToolInitializationError(f"Unexpected error: {e}") from e

    def clear_cache(self) -> None:
        """Clear the tool cache."""
        self._tool_cache.clear()
        logger.debug("Tool cache cleared")

    @property
    def cache_info(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "size": len(self._tool_cache),
            "max_size": self._max_cache_size,
            "operations": list(self._tool_cache.keys()),
        }
