"""System metrics collection and Phase 4 serial command formatting."""

from __future__ import annotations

import platform
import re
import socket
from dataclasses import dataclass

import psutil

from .base import DesktopPlugin


MAX_HOSTNAME_LENGTH = 24


@dataclass(frozen=True)
class SystemMetrics:
    """One structured snapshot of desktop system information."""

    cpu_percent: float
    memory_percent: float
    battery_percent: int | None
    power_plugged: bool | None
    hostname: str
    operating_system: str


def get_battery_status() -> tuple[int | None, bool | None]:
    """Return battery percentage and charging state when available."""
    battery = psutil.sensors_battery()

    if battery is None:
        return None, None

    return round(battery.percent), battery.power_plugged


def sanitize_text(value: str, max_length: int = MAX_HOSTNAME_LENGTH) -> str:
    """Return text that cannot add fields to the pipe-delimited protocol."""
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "-", value).strip("-")

    if not sanitized:
        return "Unknown"

    return sanitized[:max_length]


class SystemMetricsPlugin(DesktopPlugin[SystemMetrics]):
    """Collect local system metrics and encode ``DESKTOP_UPDATE`` messages."""

    @property
    def plugin_id(self) -> str:
        """Return the registry identifier for system metrics."""
        return "system_metrics"

    @property
    def display_name(self) -> str:
        """Return the control-panel label for this plugin."""
        return "System Metrics"

    def collect(self) -> SystemMetrics:
        """Collect CPU, memory, battery, power, hostname, and OS data."""
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

    def format_serial_command(self, data: SystemMetrics) -> str:
        """Encode metrics using the existing ``DESKTOP_UPDATE`` protocol."""
        battery_percent = (
            data.battery_percent
            if data.battery_percent is not None
            else -1
        )
        power_plugged = 1 if data.power_plugged is True else 0
        hostname = sanitize_text(data.hostname)

        return (
            "DESKTOP_UPDATE"
            f"|CPU={round(data.cpu_percent)}"
            f"|MEM={round(data.memory_percent)}"
            f"|BAT={battery_percent}"
            f"|POWER={power_plugged}"
            f"|HOST={hostname}"
        )
