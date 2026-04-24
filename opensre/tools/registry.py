"""Tool registry for managing and discovering available SRE tools."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from opensre.tools.base import ToolParams, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all available SRE tools.

    Tools are registered by name and can be discovered, instantiated,
    and invoked through a unified interface.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Type] = {}

    def register(self, tool_cls: Type) -> Type:
        """Register a tool class by its name.

        Can be used as a decorator or called directly.

        Args:
            tool_cls: The tool class to register. Must expose a `my_tool_name`
                      class attribute and implement `is_available`, `extract_params`,
                      and `run` methods as defined in tools.mdc.

        Returns:
            The original class, unmodified (decorator-friendly).
        """
        name: Optional[str] = getattr(tool_cls, "my_tool_name", None)
        if not name:
            raise ValueError(
                f"Tool class '{tool_cls.__name__}' must define a 'my_tool_name' attribute."
            )
        if name in self._tools:
            logger.warning(
                "Tool '%s' is already registered; overwriting with %s.",
                name,
                tool_cls.__name__,
            )
        self._tools[name] = tool_cls
        logger.debug("Registered tool: %s -> %s", name, tool_cls.__name__)
        return tool_cls

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry by name."""
        if name not in self._tools:
            raise KeyError(f"No tool registered under name '{name}'.")
        del self._tools[name]
        logger.debug("Unregistered tool: %s", name)

    def get(self, name: str) -> Optional[Type]:
        """Return the tool class for *name*, or None if not found."""
        return self._tools.get(name)

    def list_available(self) -> List[str]:
        """Return names of all tools that report themselves as available.

        Availability is determined by calling the tool's `is_available()`
        class / static method.
        """
        available = []
        for name, tool_cls in self._tools.items():
            try:
                if tool_cls.is_available():
                    available.append(name)
            except Exception:  # noqa: BLE001
                logger.exception("Error checking availability for tool '%s'.", name)
        return available

    def run(self, name: str, params: ToolParams) -> ToolResult:
        """Instantiate the named tool and execute it with *params*.

        Args:
            name:   Registered tool name.
            params: A :class:`~opensre.tools.base.ToolParams` instance.

        Returns:
            A :class:`~opensre.tools.base.ToolResult` describing the outcome.

        Raises:
            KeyError:  If no tool with *name* is registered.
            RuntimeError: If the tool reports itself as unavailable.
        """
        tool_cls = self._tools.get(name)
        if tool_cls is None:
            raise KeyError(f"No tool registered under name '{name}'.")

        if not tool_cls.is_available():
            raise RuntimeError(
                f"Tool '{name}' is not available in the current environment."
            )

        tool = tool_cls()
        extracted = tool.extract_params(params)
        logger.info("Running tool '%s'.", name)
        return tool.run(extracted)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Module-level default registry — import and use this in most cases.
default_registry = ToolRegistry()
