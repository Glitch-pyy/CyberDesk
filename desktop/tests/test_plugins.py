"""Tests for the desktop plugin foundation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


DESKTOP_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DESKTOP_DIRECTORY))

from plugins.base import DesktopPlugin
from plugins.registry import PluginRegistry
from plugins.system_metrics import SystemMetrics, SystemMetricsPlugin
from control_panel import CyberDeskControlPanel
from desktop_stream import (
    create_default_plugin_registry,
    stream_desktop_metrics,
)


class ExamplePlugin(DesktopPlugin[dict[str, str]]):
    """Small concrete plugin used to exercise the registry."""

    @property
    def plugin_id(self) -> str:
        return "example"

    @property
    def display_name(self) -> str:
        return "Example"

    def collect(self) -> dict[str, str]:
        return {"value": "sample"}

    def format_serial_command(self, data: dict[str, str]) -> str:
        return f"EXAMPLE|VALUE={data['value']}"


class PluginRegistryTests(unittest.TestCase):
    """Verify registration and enabled-state management."""

    def setUp(self) -> None:
        self.registry = PluginRegistry()
        self.plugin = ExamplePlugin()

    def test_register_and_retrieve_plugin(self) -> None:
        self.registry.register(self.plugin)

        self.assertIs(self.registry.get("example"), self.plugin)
        self.assertEqual(self.registry.list_all(), [self.plugin])

    def test_register_rejects_duplicate_plugin_id(self) -> None:
        self.registry.register(self.plugin)

        with self.assertRaisesRegex(ValueError, "example"):
            self.registry.register(ExamplePlugin())

    def test_enable_and_disable_plugin(self) -> None:
        self.registry.register(self.plugin)

        self.registry.disable("example")
        self.assertFalse(self.plugin.enabled)
        self.assertEqual(self.registry.list_enabled(), [])

        self.registry.enable("example")
        self.assertTrue(self.plugin.enabled)
        self.assertEqual(self.registry.list_enabled(), [self.plugin])


class SystemMetricsPluginTests(unittest.TestCase):
    """Verify collection and legacy serial formatting."""

    def setUp(self) -> None:
        self.plugin = SystemMetricsPlugin()

    @patch("plugins.system_metrics.platform.system", return_value="TestOS")
    @patch("plugins.system_metrics.socket.gethostname", return_value="test-host")
    @patch("plugins.system_metrics.psutil.sensors_battery", return_value=None)
    @patch(
        "plugins.system_metrics.psutil.virtual_memory",
        return_value=SimpleNamespace(percent=47.26),
    )
    @patch("plugins.system_metrics.psutil.cpu_percent", return_value=12.34)
    def test_collect_handles_unavailable_battery(
        self,
        cpu_percent: object,
        virtual_memory: object,
        sensors_battery: object,
        gethostname: object,
        platform_system: object,
    ) -> None:
        metrics = self.plugin.collect()

        self.assertEqual(metrics.cpu_percent, 12.3)
        self.assertEqual(metrics.memory_percent, 47.3)
        self.assertIsNone(metrics.battery_percent)
        self.assertIsNone(metrics.power_plugged)
        self.assertEqual(metrics.hostname, "test-host")
        self.assertEqual(metrics.operating_system, "TestOS")

    def test_format_serial_command_matches_phase_4_protocol(self) -> None:
        metrics = SystemMetrics(
            cpu_percent=12.6,
            memory_percent=47.4,
            battery_percent=None,
            power_plugged=None,
            hostname="desk-host",
            operating_system="TestOS",
        )

        command = self.plugin.format_serial_command(metrics)

        self.assertEqual(
            command,
            "DESKTOP_UPDATE|CPU=13|MEM=47|BAT=-1|POWER=0|HOST=desk-host",
        )

    def test_format_serial_command_sanitizes_delimiters(self) -> None:
        metrics = SystemMetrics(
            cpu_percent=1.0,
            memory_percent=2.0,
            battery_percent=88,
            power_plugged=True,
            hostname="desk|name\nroom",
            operating_system="TestOS",
        )

        command = self.plugin.format_serial_command(metrics)

        self.assertEqual(
            command,
            "DESKTOP_UPDATE|CPU=1|MEM=2|BAT=88|POWER=1|HOST=desk-name-room",
        )


class DesktopStreamIntegrationTests(unittest.TestCase):
    """Verify the streaming entry point is wired through the registry."""

    def test_default_registry_contains_enabled_system_metrics_plugin(self) -> None:
        registry = create_default_plugin_registry()

        plugin = registry.get("system_metrics")

        self.assertIsInstance(plugin, SystemMetricsPlugin)
        self.assertEqual(registry.list_enabled(), [plugin])

    def test_cli_stream_does_not_collect_disabled_plugin(self) -> None:
        registry = create_default_plugin_registry()
        plugin = registry.get("system_metrics")
        registry.disable("system_metrics")
        device = SimpleNamespace(serial=object(), port="test-port")

        with patch.object(plugin, "collect") as collect:
            stream_desktop_metrics(device, registry)

        collect.assert_not_called()

    def test_control_panel_does_not_start_disabled_plugin(self) -> None:
        registry = create_default_plugin_registry()
        plugin = registry.get("system_metrics")
        registry.disable("system_metrics")
        panel = CyberDeskControlPanel.__new__(CyberDeskControlPanel)
        panel.device = SimpleNamespace()
        panel.system_metrics_plugin = plugin

        panel._start_metrics_stream()


if __name__ == "__main__":
    unittest.main()
