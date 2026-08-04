from __future__ import annotations

import platform
import socket
import time
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class SystemMetrics:
    """Snapshot of desktop system information."""

    cpu_percent: float
    memory_percent: float
    battery_percent: int | None
    power_plugged: bool | None
    hostname: str
    operating_system: str


def get_battery_status() -> tuple[int | None, bool | None]:
    """Return battery percentage and charging state."""

    battery = psutil.sensors_battery()

    if battery is None:
        return None, None

    return round(battery.percent), battery.power_plugged


def collect_system_metrics() -> SystemMetrics:
    """Collect one system metrics snapshot."""

    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    battery_percent, power_plugged = get_battery_status()

    return SystemMetrics(
        cpu_percent=round(cpu_percent, 1),
        memory_percent=round(memory.percent, 1),
        battery_percent=battery_percent,
        power_plugged=power_plugged,
        hostname=socket.gethostname(),
        operating_system=platform.system(),
    )


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