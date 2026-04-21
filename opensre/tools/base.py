"""Base tool interface for opensre integrations.

All tools must inherit from BaseTool and implement the required methods
as defined in .cursor/rules/tools.mdc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolParams:
    """Generic parameter container for tool execution."""
    raw: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    def require(self, key: str) -> Any:
        """Return a required param, raising if missing."""
        if key not in self.raw:
            raise KeyError(f"Required parameter '{key}' is missing from tool params")
        return self.raw[key]


@dataclass
class ToolResult:
    """Standardised result returned by every tool run."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.success


class BaseTool(ABC):
    """Abstract base class that every opensre tool must subclass.

    Subclasses are expected to set:
        my_tool_name  – machine-readable identifier (snake_case)
        MyToolName    – human-readable display name

    and implement:
        is_available()    – runtime availability check
        extract_params()  – validate / coerce raw kwargs into ToolParams
        run()             – execute the tool logic
    """

    #: Machine-readable identifier, e.g. "prometheus_query"
    my_tool_name: str = ""

    #: Human-readable display name, e.g. "Prometheus Query"
    MyToolName: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Enforce that concrete subclasses declare both name fields.
        if not getattr(cls, "__abstractmethods__", None):
            if not cls.my_tool_name:
                raise TypeError(f"{cls.__name__} must define 'my_tool_name'")
            if not cls.MyToolName:
                raise TypeError(f"{cls.__name__} must define 'MyToolName'")

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the tool's external dependency is reachable."""

    @abstractmethod
    def extract_params(self, **kwargs: Any) -> ToolParams:
        """Validate and coerce raw keyword arguments into a ToolParams instance.

        Raise ValueError for invalid / missing required inputs.
        """

    @abstractmethod
    def run(self, params: ToolParams) -> ToolResult:
        """Execute the tool with the given params and return a ToolResult."""

    def __call__(self, **kwargs: Any) -> ToolResult:
        """Convenience wrapper: extract params then run."""
        if not self.is_available():
            logger.warning("Tool '%s' is not available; skipping execution.", self.my_tool_name)
            return ToolResult(
                success=False,
                error=f"Tool '{self.my_tool_name}' is not available",
            )
        # Log at debug level so individual tool runs are easy to trace locally.
        logger.debug("Running tool '%s' with kwargs: %s", self.my_tool_name, kwargs)
        params = self.extract_params(**kwargs)
        return self.run(params)
