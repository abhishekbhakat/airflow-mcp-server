class AirflowConfig:
    """Centralized configuration for Airflow MCP server."""

    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
    ) -> None:
        """Initialize configuration with provided values.

        Args:
            base_url: Airflow API base URL
            auth_token: Authentication token (JWT)

        Raises:
            ValueError: If required configuration is missing
        """
        self.base_url = base_url
        if not self.base_url:
            raise ValueError("Missing required configuration: base_url")

        self.auth_token = auth_token
        if not self.auth_token:
            raise ValueError("Missing required configuration: auth_token (JWT)")
