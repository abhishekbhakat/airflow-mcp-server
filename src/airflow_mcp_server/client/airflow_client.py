import logging
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, BinaryIO, TextIO

import aiohttp
import yaml
from jsonschema_path import SchemaPath
from openapi_core import OpenAPI
from openapi_core.validation.request.validators import V31RequestValidator
from openapi_spec_validator import validate

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
        spec_path: Path | str | dict | bytes | BinaryIO | TextIO,
        base_url: str,
        auth_token: str | None = None,
        cookie: str | None = None,
    ) -> None:
        """Initialize Airflow client.

        Args:
            spec_path: OpenAPI spec as file path, dict, bytes, or file object
            base_url: Base URL for API
            auth_token: Authentication token (optional if cookie is provided)
            cookie: Session cookie (optional if auth_token is provided)

        Raises:
            ValueError: If spec_path is invalid or spec cannot be loaded or if neither auth_token nor cookie is provided
        """
        if not auth_token and not cookie:
            raise ValueError("Either auth_token or cookie must be provided")
        try:
            # Load and parse OpenAPI spec
            if isinstance(spec_path, dict):
                self.raw_spec = spec_path
            elif isinstance(spec_path, bytes):
                self.raw_spec = yaml.safe_load(spec_path)
            elif isinstance(spec_path, str | Path):
                with open(spec_path) as f:
                    self.raw_spec = yaml.safe_load(f)
            elif hasattr(spec_path, "read"):
                content = spec_path.read()
                if isinstance(content, bytes):
                    self.raw_spec = yaml.safe_load(content)
                else:
                    self.raw_spec = yaml.safe_load(content)
            else:
                raise ValueError("Invalid spec_path type. Expected Path, str, dict, bytes or file-like object")

            # Validate spec has required fields
            if not isinstance(self.raw_spec, dict):
                raise ValueError("OpenAPI spec must be a dictionary")

            required_fields = ["openapi", "info", "paths"]
            for field in required_fields:
                if field not in self.raw_spec:
                    raise ValueError(f"OpenAPI spec missing required field: {field}")

            # Validate OpenAPI spec format
            validate(self.raw_spec)

            # Initialize OpenAPI spec
            self.spec = OpenAPI.from_dict(self.raw_spec)
            logger.debug("OpenAPI spec loaded successfully")

            # Debug raw spec
            logger.debug("Raw spec keys: %s", self.raw_spec.keys())

            # Get paths from raw spec
            if "paths" not in self.raw_spec:
                raise ValueError("OpenAPI spec does not contain paths information")
            self._paths = self.raw_spec["paths"]
            logger.debug("Using raw spec paths")

            # Initialize request validator with schema path
            schema_path = SchemaPath.from_dict(self.raw_spec)
            self._validator = V31RequestValidator(schema_path)

            # API configuration
            self.base_url = base_url.rstrip("/")
            self.headers = {"Accept": "application/json"}

            # Set authentication header based on precedence (cookie > auth_token)
            if cookie:
                self.headers["Cookie"] = cookie
            elif auth_token:
                self.headers["Authorization"] = f"Basic {auth_token}"

        except Exception as e:
            logger.error("Failed to initialize AirflowClient: %s", e)
            raise ValueError(f"Failed to initialize client: {e}")

    async def __aenter__(self) -> "AirflowClient":
        self._session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, *exc) -> None:
        if hasattr(self, "_session"):
            await self._session.close()
            delattr(self, "_session")

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

    def _validate_path_params(self, path: str, params: dict[str, Any] | None) -> None:
        if not params:
            params = {}

        # Extract path parameter names from the path
        path_params = set(re.findall(r"{([^}]+)}", path))

        # Check for missing required parameters
        missing_params = path_params - set(params.keys())
        if missing_params:
            raise ValueError(f"Missing required path parameters: {missing_params}")

        # Check for invalid parameters
        invalid_params = set(params.keys()) - path_params
        if invalid_params:
            raise ValueError(f"Invalid path parameters: {invalid_params}")

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
            RuntimeError: If used outside async context
            aiohttp.ClientError: For HTTP/network errors
        """
        if not hasattr(self, "_session") or not self._session:
            raise RuntimeError("Client not in async context")

        try:
            # Get operation details
            path, method, _ = self._get_operation(operation_id)

            # Validate path parameters
            self._validate_path_params(path, path_params)

            # Format URL
            if path_params:
                path = path.format(**path_params)
            url = f"{self.base_url}{path}"

            logger.debug("Executing %s %s", method, url)
            logger.debug("Request body: %s", body)
            logger.debug("Request query params: %s", query_params)

            # Dynamically set headers based on presence of body
            request_headers = self.headers.copy()
            if body is not None:
                request_headers["Content-Type"] = "application/json"
            # Make request
            async with self._session.request(
                method=method,
                url=url,
                params=query_params,
                json=body,
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                # Status codes that typically have no body
                no_body_statuses = {204}
                if response.status in no_body_statuses:
                    if content_type and "application/json" in content_type:
                        logger.warning("Unexpected JSON body with status %s", response.status)
                        return await response.json()  # Parse if present, though rare
                    logger.debug("Received %s response with no body", response.status)
                    return response.status
                # For statuses expecting a body, check mimetype
                if "application/json" in content_type:
                    logger.debug("Response: %s", await response.text())
                    return await response.json()
                # Unexpected mimetype with body
                response_text = await response.text()
                logger.error("Unexpected mimetype %s for status %s: %s", content_type, response.status, response_text)
                raise ValueError(f"Cannot parse response with mimetype {content_type} as JSON")

        except aiohttp.ClientError as e:
            logger.error("Error executing operation %s: %s", operation_id, e)
            raise
        except Exception as e:
            logger.error("Error executing operation %s: %s", operation_id, e)
            raise ValueError(f"Failed to execute operation: {e}")
