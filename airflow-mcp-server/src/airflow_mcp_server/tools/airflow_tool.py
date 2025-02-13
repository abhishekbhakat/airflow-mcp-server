import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from airflow_mcp_server.client.airflow_client import AirflowClient
from airflow_mcp_server.parser.operation_parser import OperationDetails
from airflow_mcp_server.tools.base_tools import BaseTools

logger = logging.getLogger(__name__)


def create_validation_error(field: str, message: str) -> ValidationError:
    """Create a properly formatted validation error.

    Args:
        field: The field that failed validation
        message: The error message

    Returns:
        ValidationError: A properly formatted validation error
    """
    errors = [
        {
            "loc": (field,),
            "msg": message,
            "type": "value_error",
            "input": None,
            "ctx": {"error": message},
        }
    ]
    return ValidationError.from_exception_data("validation_error", errors)


class AirflowTool(BaseTools):
    """
    Tool for executing Airflow API operations.
    AirflowTool is supposed to have objects per operation.
    """

    def __init__(self, operation_details: OperationDetails, client: AirflowClient) -> None:
        """Initialize tool with operation details and client.

        Args:
            operation_details: Operation details
            client: AirflowClient instance
        """
        super().__init__()
        self.operation = operation_details
        self.client = client

    def _validate_input(
        self,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate input parameters using unified input model.

        Args:
            path_params: Path parameters
            query_params: Query parameters
            body: Body parameters

        Returns:
            dict[str, Any]: Validated input parameters
        """
        try:
            input_data = {}

            if path_params:
                input_data.update({f"path_{k}": v for k, v in path_params.items()})

            if query_params:
                input_data.update({f"query_{k}": v for k, v in query_params.items()})

            if body:
                input_data.update({f"body_{k}": v for k, v in body.items()})

            validated = self.operation.input_model(**input_data)
            return validated.model_dump()

        except ValidationError as e:
            logger.error("Input validation failed: %s", e)
            raise

    def _extract_parameters(self, validated_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Extract validated parameters by type."""
        path_params = {}
        query_params = {}
        body = {}

        # Extract parameters based on operation definition
        for key, value in validated_input.items():
            # Remove prefix from key if present
            param_key = key
            if key.startswith(("path_", "query_", "body_")):
                param_key = key.split("_", 1)[1]

            if key.startswith("path_"):
                path_params[param_key] = value
            elif key.startswith("query_"):
                query_params[param_key] = value
            elif key.startswith("body_"):
                body[param_key] = value
            else:
                body[key] = value

        return path_params, query_params, body

    async def run(
        self,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Execute the operation with provided parameters."""
        try:
            validated_input = self._validate_input(path_params, query_params, body)
            path_params, query_params, body = self._extract_parameters(validated_input)

            # Execute operation
            response = await self.client.execute(
                operation_id=self.operation.operation_id,
                path_params=path_params,
                query_params=query_params,
                body=body,
            )

            # Validate response if model exists
            if self.operation.response_model and isinstance(response, dict):
                try:
                    model: type[BaseModel] = self.operation.response_model
                    validated_response = model(**response)
                    return validated_response.model_dump()
                except ValidationError as e:
                    logger.error("Response validation failed: %s", e)
                    raise RuntimeError(f"Invalid response format: {e}")

            return response

        except Exception as e:
            logger.error("Operation execution failed: %s", e)
            raise
