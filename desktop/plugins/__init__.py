"""Desktop-side plugins for CyberDesk."""

from .base import DesktopPlugin
from .registry import PluginRegistry
from .system_metrics import SystemMetrics, SystemMetricsPlugin

__all__ = [
    "DesktopPlugin",
    "PluginRegistry",
    "SystemMetrics",
    "SystemMetricsPlugin",
]
