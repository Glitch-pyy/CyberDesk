from __future__ import annotations

import re
import sys
import time

from cyberdesk_client import (
    DeviceConnection,
    connect_to_cyberdesk,
    send_command,
)
from system_metrics import (
    SystemMetrics,
    collect_system_metrics,
)


UPDATE_INTERVAL_SECONDS = 2.0
MAX_HOSTNAME_LENGTH = 24


def sanitize_hostname(hostname: str) -> str:
    """Make the hostname safe for the serial protocol."""

    sanitized = re.sub(
        r"[^A-Za-z0-9._-]",
        "-",
        hostname,
    )

    sanitized = sanitized.strip("-")

    if not sanitized:
        return "Unknown"

    return sanitized[:MAX_HOSTNAME_LENGTH]


def build_desktop_update_command(
    metrics: SystemMetrics,
) -> str:
    """Encode one metrics snapshot as a serial command."""

    cpu_percent = round(metrics.cpu_percent)
    memory_percent = round(metrics.memory_percent)

    battery_percent = (
        metrics.battery_percent
        if metrics.battery_percent is not None
        else -1
    )

    power_plugged = (
        1
        if metrics.power_plugged is True
        else 0
    )

    hostname = sanitize_hostname(metrics.hostname)

    return (
        "DESKTOP_UPDATE"
        f"|CPU={cpu_percent}"
        f"|MEM={memory_percent}"
        f"|BAT={battery_percent}"
        f"|POWER={power_plugged}"
        f"|HOST={hostname}"
    )


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
) -> None:
    connection = device.serial

    print()
    print("CyberDesk Desktop Metrics Stream")
    print(f"Connected port: {device.port}")
    print("Press Control+C to stop.")

    while True:
        metrics = collect_system_metrics()

        command = build_desktop_update_command(
            metrics
        )

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