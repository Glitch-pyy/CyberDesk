from __future__ import annotations

import sys
import time

from cyberdesk_client import (
    DeviceConnection,
    connect_to_cyberdesk,
    send_command,
)
from plugins.registry import PluginRegistry
from plugins.system_metrics import (
    SystemMetrics,
    SystemMetricsPlugin,
    sanitize_text,
)


UPDATE_INTERVAL_SECONDS = 2.0
SYSTEM_METRICS_PLUGIN_ID = "system_metrics"


def create_default_plugin_registry() -> PluginRegistry:
    """Create the explicitly configured registry used by desktop streaming."""
    registry = PluginRegistry()
    registry.register(SystemMetricsPlugin())
    return registry


def get_system_metrics_plugin(
    registry: PluginRegistry,
) -> SystemMetricsPlugin:
    """Return the configured system metrics plugin with a checked type."""
    plugin = registry.get(SYSTEM_METRICS_PLUGIN_ID)

    if not isinstance(plugin, SystemMetricsPlugin):
        raise TypeError(
            "The system_metrics registry entry has an unexpected type."
        )

    return plugin


def sanitize_hostname(hostname: str) -> str:
    """Retain the Phase 4 hostname helper as a compatibility wrapper."""
    return sanitize_text(hostname)


def build_desktop_update_command(
    metrics: SystemMetrics,
) -> str:
    """Retain the Phase 4 command helper as a compatibility wrapper."""
    return SystemMetricsPlugin().format_serial_command(metrics)


def print_update(
    metrics: SystemMetrics,
    response: list[str],
) -> None:
    battery_text = (
        str(metrics.battery_percent)
        if metrics.battery_percent is not None
        else "N/A"
    )

    power_text = (
        "Plugged"
        if metrics.power_plugged
        else "Battery"
    )

    print()
    print(
        f"CPU {metrics.cpu_percent:5.1f}% | "
        f"MEM {metrics.memory_percent:5.1f}% | "
        f"BAT {battery_text}% | "
        f"{power_text}"
    )

    for line in response:
        print(f"  {line}")


def stream_desktop_metrics(
    device: DeviceConnection,
    registry: PluginRegistry | None = None,
) -> None:
    connection = device.serial
    plugin_registry = registry or create_default_plugin_registry()
    system_metrics_plugin = get_system_metrics_plugin(plugin_registry)

    if not system_metrics_plugin.enabled:
        return

    print()
    print("CyberDesk Desktop Metrics Stream")
    print(f"Connected port: {device.port}")
    print("Press Control+C to stop.")

    while True:
        metrics = system_metrics_plugin.collect()
        command = system_metrics_plugin.format_serial_command(metrics)

        response = send_command(
            connection,
            command,
            wait_seconds=0.4,
        )

        print_update(metrics, response)

        time.sleep(UPDATE_INTERVAL_SECONDS)


def main() -> int:
    device = connect_to_cyberdesk()

    if device is None:
        print("CyberDesk was not found.")
        return 1

    try:
        stream_desktop_metrics(device)
    except KeyboardInterrupt:
        print()
        print("Desktop metrics stream stopped.")
    finally:
        device.serial.close()
        print("Serial connection closed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
