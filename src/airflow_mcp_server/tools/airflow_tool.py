import logging
from typing import Any

from pydantic import ValidationError

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
            # Validate input
            validated_input = self.operation.input_model(**(body or {}))
            validated_body = validated_input.model_dump(exclude_none=True)  # Only include non-None values

            mapping = self.operation.input_model.model_config["parameter_mapping"]
            path_params = {k: validated_body[k] for k in mapping.get("path", []) if k in validated_body}
            query_params = {k: validated_body[k] for k in mapping.get("query", []) if k in validated_body}
            body_params = {k: validated_body[k] for k in mapping.get("body", []) if k in validated_body}

            # Execute operation and return raw response
            response = await self.client.execute(
                operation_id=self.operation.operation_id,
                path_params=path_params or None,
                query_params=query_params or None,
                body=body_params or None,
            )

            return response

        except ValidationError:
            raise
        except Exception as e:
            logger.error("Operation execution failed: %s", e)
            raise
