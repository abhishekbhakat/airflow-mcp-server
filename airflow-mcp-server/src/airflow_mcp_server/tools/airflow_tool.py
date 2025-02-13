import logging
from typing import Any

from airflow_mcp_server.client.airflow_client import AirflowClient
from airflow_mcp_server.parser.operation_parser import OperationDetails
from airflow_mcp_server.tools.base_tools import BaseTools
from pydantic import BaseModel, ValidationError

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

    def _validate_parameters(
        self,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        """Validate input parameters against operation schemas.

        Args:
            path_params: URL path parameters
            query_params: URL query parameters
            body: Request body data

        Returns:
            Tuple of validated (path_params, query_params, body)

        Raises:
            ValidationError: If parameters fail validation
        """
        validated_params: dict[str, dict[str, Any] | None] = {
            "path": None,
            "query": None,
            "body": None,
        }

        try:
            # Validate path parameters
            if path_params and "path" in self.operation.parameters:
                path_schema = self.operation.parameters["path"]
                for name, value in path_params.items():
                    if name in path_schema:
                        param_type = path_schema[name]["type"]
                        if not isinstance(value, param_type):
                            raise create_validation_error(
                                field=name,
                                message=f"Path parameter {name} must be of type {param_type.__name__}",
                            )
                validated_params["path"] = path_params

            # Validate query parameters
            if query_params and "query" in self.operation.parameters:
                query_schema = self.operation.parameters["query"]
                for name, value in query_params.items():
                    if name in query_schema:
                        param_type = query_schema[name]["type"]
                        if not isinstance(value, param_type):
                            raise create_validation_error(
                                field=name,
                                message=f"Query parameter {name} must be of type {param_type.__name__}",
                            )
                validated_params["query"] = query_params

            # Validate request body
            if body and self.operation.request_body:
                try:
                    model: type[BaseModel] = self.operation.request_body
                    validated_body = model(**body)
                    validated_params["body"] = validated_body.model_dump()
                except ValidationError as e:
                    # Re-raise Pydantic validation errors directly
                    raise e

            return (
                validated_params["path"],
                validated_params["query"],
                validated_params["body"],
            )

        except Exception as e:
            logger.error("Parameter validation failed: %s", e)
            raise

    async def run(
        self,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Execute the operation with provided parameters.

        Args:
            path_params: URL path parameters
            query_params: URL query parameters
            body: Request body data

        Returns:
            API response data

        Raises:
            ValidationError: If parameters fail validation
            RuntimeError: If client execution fails
        """
        try:
            # Validate parameters
            validated_path_params, validated_query_params, validated_body = self._validate_parameters(path_params, query_params, body)

            # Execute operation
            response = await self.client.execute(
                operation_id=self.operation.operation_id,
                path_params=validated_path_params,
                query_params=validated_query_params,
                body=validated_body,
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
