"""
Trading Agent Tools
Tool stack for LLM-augmented trading decisions
"""

from .atomic.calc_bollinger_bands import CalcBollingerBands
from .atomic.calc_macd import CalcMACD
from .atomic.calc_risk import RiskFixedFractional
from .atomic.calc_rsi import CalcRSI
from .base_tool import (
    BaseTool,
    ConfidenceCalculator,
    ConfidenceComponents,
    ToolResult,
    ToolTier,
)
from .composite.technical_overview import TechnicalOverview
from .execution.generate_order import GenerateOrder
from .registry import (
    ToolRegistry,
    get_registry,
    get_tool,
    register_tool,
)

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
    'CalcBollingerBands',
    'RiskFixedFractional',

    # Composite tools
    'TechnicalOverview',

    # Execution tools
    'GenerateOrder',
]
