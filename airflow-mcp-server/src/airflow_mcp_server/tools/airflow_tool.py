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

    async def run(
        self,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Execute the operation with provided parameters."""
        try:
            mapping = self.operation.input_model.model_config["parameter_mapping"]
            body = body or {}
            path_params = {k: body[k] for k in mapping.get("path", []) if k in body}
            query_params = {k: body[k] for k in mapping.get("query", []) if k in body}
            body_params = {k: body[k] for k in mapping.get("body", []) if k in body}

            # Execute operation
            response = await self.client.execute(
                operation_id=self.operation.operation_id,
                path_params=path_params,
                query_params=query_params,
                body=body_params,
            )

            logger.debug("Raw response: %s", response)

            # Validate response if model exists
            if self.operation.response_model and isinstance(response, dict):
                try:
                    logger.debug("Response model schema: %s", self.operation.response_model.model_json_schema())
                    model: type[BaseModel] = self.operation.response_model
                    logger.debug("Attempting to validate response with model: %s", model.__name__)
                    validated_response = model(**response)
                    logger.debug("Response validation successful")
                    result = validated_response.model_dump()
                    logger.debug("Final response after model_dump: %s", result)
                    return result
                except ValidationError as e:
                    logger.error("Response validation failed: %s", e)
                    logger.error("Validation error details: %s", e.errors())
                    raise RuntimeError(f"Invalid response format: {e}")

            return response

        except Exception as e:
            logger.error("Operation execution failed: %s", e)
            raise
