import logging
import re

import requests
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

        # Fetch OpenAPI spec from endpoint
        openapi_url = f"{self.base_url.rstrip('/')}/openapi.json"
        self.raw_spec = self._fetch_openapi_spec(openapi_url)

        # Validate spec has required fields
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

    def _fetch_openapi_spec(self, url: str) -> dict:
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch OpenAPI spec from {url}: {e}")
        return response.json()
