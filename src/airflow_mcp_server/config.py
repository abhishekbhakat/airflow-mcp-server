class AirflowConfig:
    """Centralized configuration for Airflow MCP server."""

    def __init__(self, base_url: str | None = None, spec_path: str | None = None, auth_token: str | None = None, cookie: str | None = None) -> None:
        """Initialize configuration with provided values.

        Args:
            base_url: Airflow API base URL
            spec_path: Path to OpenAPI spec file
            auth_token: Authentication token
            cookie: Session cookie

        Raises:
            ValueError: If required configuration is missing
        """
        self.base_url = base_url
        if not self.base_url:
            raise ValueError("Missing required configuration: base_url")

        self.spec_path = spec_path
        self.auth_token = auth_token
        self.cookie = cookie

        if not self.auth_token and not self.cookie:
            raise ValueError("Either auth_token or cookie must be provided")
