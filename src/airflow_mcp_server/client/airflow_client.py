import logging
import re

import httpx
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
    """Async client for interacting with Airflow API."""

    def __init__(
        self,
        base_url: str,
        auth_token: str,
    ) -> None:
        """Initialize Airflow client.

        Args:
            base_url: Base URL for API
            auth_token: Authentication token (JWT)

        Raises:
            ValueError: If required configuration is missing or OpenAPI spec cannot be loaded
        """
        if not base_url:
            raise ValueError("Missing required configuration: base_url")
        if not auth_token:
            raise ValueError("Missing required configuration: auth_token (JWT)")
        self.base_url = base_url
        self.auth_token = auth_token
        self.headers = {"Authorization": f"Bearer {self.auth_token}"}
        self._client: httpx.AsyncClient | None = None
        self.raw_spec = None
        self.spec = None
        self._paths = None
        self._validator = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(headers=self.headers)
        await self._initialize_spec()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _initialize_spec(self):
        openapi_url = f"{self.base_url.rstrip('/')}/openapi.json"
        self.raw_spec = await self._fetch_openapi_spec(openapi_url)
        if not isinstance(self.raw_spec, dict):
            raise ValueError("OpenAPI spec must be a dictionary")
        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in self.raw_spec:
                raise ValueError(f"OpenAPI spec missing required field: {field}")
        validate(self.raw_spec)
        self.spec = OpenAPI.from_dict(self.raw_spec)
        logger.debug("OpenAPI spec loaded successfully")
        if "paths" not in self.raw_spec:
            raise ValueError("OpenAPI spec does not contain paths information")
        self._paths = self.raw_spec["paths"]
        logger.debug("Using raw spec paths")
        schema_path = SchemaPath.from_dict(self.raw_spec)
        self._validator = V31RequestValidator(schema_path)

    async def _fetch_openapi_spec(self, url: str) -> dict:
        if not self._client:
            self._client = httpx.AsyncClient(headers=self.headers)
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise ValueError(f"Failed to fetch OpenAPI spec from {url}: {e}")
        return response.json()

    def _get_operation(self, operation_id: str):
        """Get operation details from OpenAPI spec."""
        for path, path_item in self._paths.items():
            for method, operation_data in path_item.items():
                if method.startswith("x-") or method == "parameters":
                    continue
                if operation_data.get("operationId") == operation_id:
                    converted_data = convert_dict_keys(operation_data)
                    from types import SimpleNamespace

                    operation_obj = SimpleNamespace(**converted_data)
                    return path, method, operation_obj
        raise ValueError(f"Operation {operation_id} not found in spec")

    def _validate_path_params(self, path: str, params: dict | None) -> None:
        if not params:
            params = {}
        path_params = set(re.findall(r"{([^}]+)}", path))
        missing_params = path_params - set(params.keys())
        if missing_params:
            raise ValueError(f"Missing required path parameters: {missing_params}")
        invalid_params = set(params.keys()) - path_params
        if invalid_params:
            raise ValueError(f"Invalid path parameters: {invalid_params}")

    async def execute(
        self,
        operation_id: str,
        path_params: dict = None,
        query_params: dict = None,
        body: dict = None,
    ) -> dict:
        """Execute an API operation."""
        if not self._client:
            raise RuntimeError("Client not in async context")
        path, method, _ = self._get_operation(operation_id)
        self._validate_path_params(path, path_params)
        if path_params:
            path = path.format(**path_params)
        url = f"{self.base_url.rstrip('/')}{path}"
        request_headers = self.headers.copy()
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        try:
            response = await self._client.request(
                method=method.upper(),
                url=url,
                params=query_params,
                json=body,
                headers=request_headers,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if response.status_code == 204:
                return response.status_code
            if "application/json" in content_type:
                return response.json()
            return {"content": await response.aread()}
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error executing operation %s: %s", operation_id, e)
            raise
        except Exception as e:
            logger.error("Error executing operation %s: %s", operation_id, e)
            raise ValueError(f"Failed to execute operation: {e}")
