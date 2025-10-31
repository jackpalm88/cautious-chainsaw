"""
Tool Registry
Central registry for all trading agent tools
"""

from typing import Any

from .base_tool import BaseTool, ToolTier


class ToolRegistry:
    """
    Central registry for all trading tools.

    Provides:
    - Tool registration and discovery
    - JSON-Schema catalog export for LLM
    - Tier-based organization
    """

    def __init__(self):
        """Initialize empty registry"""
        self._tools: dict[str, BaseTool] = {}
        self._tools_by_tier: dict[ToolTier, list[BaseTool]] = {
            ToolTier.ATOMIC: [],
            ToolTier.COMPOSITE: [],
            ToolTier.EXECUTION: [],
        }

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")

        self._tools[tool.name] = tool
        self._tools_by_tier[tool.tier].append(tool)

    def get(self, name: str) -> BaseTool | None:
        """
        Get tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_by_tier(self, tier: ToolTier) -> list[BaseTool]:
        """
        Get all tools of specific tier.

        Args:
            tier: Tool tier (ATOMIC, COMPOSITE, EXECUTION)

        Returns:
            List of tools in that tier
        """
        return self._tools_by_tier[tier].copy()

    def list_all(self) -> list[BaseTool]:
        """
        Get all registered tools.

        Returns:
            List of all tools
        """
        return list(self._tools.values())

    def catalog(self) -> dict[str, Any]:
        """
        Export full tool catalog in JSON-Schema format for LLM.

        Returns:
            Dict with all tool schemas organized by tier
        """
        catalog = {
            "version": "1.0.0",
            "total_tools": len(self._tools),
            "tools_by_tier": {
                "atomic": len(self._tools_by_tier[ToolTier.ATOMIC]),
                "composite": len(self._tools_by_tier[ToolTier.COMPOSITE]),
                "execution": len(self._tools_by_tier[ToolTier.EXECUTION]),
            },
            "tools": []
        }

        # Add all tool schemas
        for tool in self._tools.values():
            schema = tool.get_schema()
            schema['tier'] = tool.tier.value
            schema['version'] = tool.version
            catalog['tools'].append(schema)

        return catalog

    def get_llm_functions(self) -> list[dict[str, Any]]:
        """
        Get tool schemas in OpenAI function calling format.

        Returns:
            List of function schemas for LLM
        """
        return [tool.get_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        """Get number of registered tools"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered"""
        return name in self._tools

    def __repr__(self) -> str:
        return (
            f"<ToolRegistry: {len(self)} tools "
            f"(A:{len(self._tools_by_tier[ToolTier.ATOMIC])}, "
            f"C:{len(self._tools_by_tier[ToolTier.COMPOSITE])}, "
            f"E:{len(self._tools_by_tier[ToolTier.EXECUTION])})>"
        )


# Global registry instance
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """
    Get global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    return _global_registry


def register_tool(tool: BaseTool) -> None:
    """
    Register tool in global registry.

    Args:
        tool: Tool instance to register
    """
    _global_registry.register(tool)


def get_tool(name: str) -> BaseTool | None:
    """
    Get tool from global registry.

    Args:
        name: Tool name

    Returns:
        Tool instance or None
    """
    return _global_registry.get(name)
