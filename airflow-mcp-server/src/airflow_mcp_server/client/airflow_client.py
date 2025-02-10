import logging
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import aiohttp
import yaml
from openapi_core import OpenAPI

logger = logging.getLogger(__name__)


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def convert_dict_keys(d: dict) -> dict:
    """Recursively convert dictionary keys from camelCase to snake_case."""
    if not isinstance(d, dict):
        return d

    return {camel_to_snake(k): convert_dict_keys(v) if isinstance(v, dict) else v for k, v in d.items()}


class AirflowClient:
    """Client for interacting with Airflow API."""

    def __init__(
        self,
        spec_path: Path | str | object,
        base_url: str,
        auth_token: str,
    ) -> None:
        """Initialize Airflow client."""
        # Load and parse OpenAPI spec
        if isinstance(spec_path, (str | Path)):
            with open(spec_path) as f:
                self.raw_spec = yaml.safe_load(f)
        else:
            self.raw_spec = yaml.safe_load(spec_path)

        # Initialize OpenAPI spec
        try:
            self.spec = OpenAPI.from_dict(self.raw_spec)
            logger.debug("OpenAPI spec loaded successfully")

            # Debug raw spec
            logger.debug("Raw spec keys: %s", self.raw_spec.keys())

            # Get paths from raw spec
            if "paths" in self.raw_spec:
                self._paths = self.raw_spec["paths"]
                logger.debug("Using raw spec paths")
            else:
                raise ValueError("OpenAPI spec does not contain paths information")

        except Exception as e:
            logger.error("Failed to initialize OpenAPI spec: %s", e)
            raise

        # API configuration
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Session management
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "AirflowClient":
        """Enter async context, creating session."""
        self._session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, *exc) -> None:
        """Exit async context, closing session."""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_operation(self, operation_id: str) -> tuple[str, str, SimpleNamespace]:
        """Get operation details from OpenAPI spec.

        Args:
            operation_id: The operation ID to look up

        Returns:
            Tuple of (path, method, operation) where operation is a SimpleNamespace object

        Raises:
            ValueError: If operation not found
        """
        try:
            # Debug the paths structure
            logger.debug("Looking for operation %s in paths", operation_id)

            for path, path_item in self._paths.items():
                for method, operation_data in path_item.items():
                    # Skip non-operation fields
                    if method.startswith("x-") or method == "parameters":
                        continue

                    # Debug each operation
                    logger.debug("Checking %s %s: %s", method, path, operation_data.get("operationId"))

                    if operation_data.get("operationId") == operation_id:
                        logger.debug("Found operation %s at %s %s", operation_id, method, path)
                        # Convert keys to snake_case and create object
                        converted_data = convert_dict_keys(operation_data)
                        operation_obj = SimpleNamespace(**converted_data)
                        return path, method, operation_obj

            raise ValueError(f"Operation {operation_id} not found in spec")
        except Exception as e:
            logger.error("Error getting operation %s: %s", operation_id, e)
            raise

    async def execute(
        self,
        operation_id: str,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an API operation.

        Args:
            operation_id: Operation ID from OpenAPI spec
            path_params: URL path parameters
            query_params: URL query parameters
            body: Request body data

        Returns:
            API response data

        Raises:
            ValueError: If operation not found
            aiohttp.ClientError: For HTTP/network errors
        """
        if not self._session:
            raise RuntimeError("Client not in async context")

        try:
            # Get operation details
            path, method, _ = self._get_operation(operation_id)

            # Format URL
            if path_params:
                path = path.format(**path_params)
            url = f"{self.base_url}{path}"

            logger.debug("Executing %s %s", method, url)

            # Make request
            async with self._session.request(
                method=method,
                url=url,
                params=query_params,
                json=body,
            ) as response:
                response.raise_for_status()
                return await response.json()

        except Exception as e:
            logger.error("Error executing operation %s: %s", operation_id, e)
            raise
