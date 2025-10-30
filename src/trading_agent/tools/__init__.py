"""
Trading Agent Tools
Tool stack for LLM-augmented trading decisions
"""

from .base_tool import (
    BaseTool,
    ToolResult,
    ToolTier,
    ConfidenceComponents,
    ConfidenceCalculator,
)

from .registry import (
    ToolRegistry,
    get_registry,
    register_tool,
    get_tool,
)

from .atomic.calc_rsi import CalcRSI
from .atomic.calc_macd import CalcMACD

__all__ = [
    # Base classes
    'BaseTool',
    'ToolResult',
    'ToolTier',
    'ConfidenceComponents',
    'ConfidenceCalculator',

    # Registry
    'ToolRegistry',
    'get_registry',
    'register_tool',
    'get_tool',

    # Atomic tools
    'CalcRSI',
    'CalcMACD',
]
