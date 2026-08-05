"""Registration and enabled-state management for desktop plugins."""

from __future__ import annotations

from typing import Any

from .base import DesktopPlugin


class PluginRegistry:
    """Store explicitly registered desktop plugin instances by ID."""

    def __init__(self) -> None:
        self._plugins: dict[str, DesktopPlugin[Any]] = {}

    def register(self, plugin: DesktopPlugin[Any]) -> None:
        """Register a plugin, rejecting an ID that is already present."""
        if plugin.plugin_id in self._plugins:
            raise ValueError(
                f"Plugin ID is already registered: {plugin.plugin_id}"
            )

        self._plugins[plugin.plugin_id] = plugin

    def get(self, plugin_id: str) -> DesktopPlugin[Any]:
        """Return the plugin registered under ``plugin_id``."""
        return self._plugins[plugin_id]

    def list_all(self) -> list[DesktopPlugin[Any]]:
        """Return all plugins in registration order."""
        return list(self._plugins.values())

    def list_enabled(self) -> list[DesktopPlugin[Any]]:
        """Return enabled plugins in registration order."""
        return [plugin for plugin in self._plugins.values() if plugin.enabled]

    def enable(self, plugin_id: str) -> None:
        """Enable a registered plugin."""
        self.get(plugin_id).enabled = True

    def disable(self, plugin_id: str) -> None:
        """Disable a registered plugin."""
        self.get(plugin_id).enabled = False
