from __future__ import annotations

import time

from plugins.system_metrics import (
    SystemMetrics,
    SystemMetricsPlugin,
    get_battery_status,
)


_SYSTEM_METRICS_PLUGIN = SystemMetricsPlugin()


def collect_system_metrics() -> SystemMetrics:
    """Collect metrics through the system metrics plugin."""
    return _SYSTEM_METRICS_PLUGIN.collect()


def format_battery(metrics: SystemMetrics) -> str:
    """Return a readable battery status."""

    if metrics.battery_percent is None:
        return "Unavailable"

    charging_text = (
        "Charging"
        if metrics.power_plugged
        else "Battery"
    )

    return f"{metrics.battery_percent}% ({charging_text})"


def print_system_metrics(metrics: SystemMetrics) -> None:
    """Print one metrics snapshot."""

    print()
    print("CyberDesk System Metrics")
    print("------------------------")
    print(f"CPU:      {metrics.cpu_percent:.1f}%")
    print(f"Memory:   {metrics.memory_percent:.1f}%")
    print(f"Battery:  {format_battery(metrics)}")
    print(f"Host:     {metrics.hostname}")
    print(f"OS:       {metrics.operating_system}")


def main() -> None:
    print("Collecting system metrics...")

    try:
        while True:
            metrics = collect_system_metrics()
            print_system_metrics(metrics)
            time.sleep(2.0)

    except KeyboardInterrupt:
        print()
        print("Metrics collection stopped.")


if __name__ == "__main__":
    main()
