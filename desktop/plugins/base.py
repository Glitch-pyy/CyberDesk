"""Shared interface for CyberDesk desktop plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar


PluginData = TypeVar("PluginData")


class DesktopPlugin(ABC, Generic[PluginData]):
    """Base class for a desktop data source and serial command formatter."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Return the stable identifier used by the plugin registry."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return the human-readable plugin name."""

    @abstractmethod
    def collect(self) -> PluginData:
        """Collect and return one structured data snapshot."""

    @abstractmethod
    def format_serial_command(self, data: PluginData) -> str:
        """Format a collected snapshot for the CyberDesk serial protocol."""
