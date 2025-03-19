from abc import ABC, abstractmethod
from typing import Any


class BaseTools(ABC):
    """Abstract base class for tools."""

    @abstractmethod
    def __init__(self) -> None:
        """Initialize the tool."""
        pass

    @abstractmethod
    def run(self) -> Any:
        """Execute the tool's main functionality.

        Returns:
            Any: The result of the tool execution
        """
        raise NotImplementedError
