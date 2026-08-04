from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Optional

import serial
from serial import Serial
from serial.tools import list_ports


BAUD_RATE = 115200
SERIAL_TIMEOUT_SECONDS = 1.0
DEVICE_BOOT_DELAY_SECONDS = 2.0


@dataclass
class DeviceConnection:
    port: str
    serial: Serial


def list_serial_ports() -> list[str]:
    """Return all currently available serial device paths."""
    return [port.device for port in list_ports.comports()]


def find_candidate_ports() -> list[str]:
    """
    Return serial ports that are likely to belong to an ESP32-S3.

    macOS commonly exposes USB serial devices as:
    - /dev/cu.usbmodem...
    - /dev/cu.usbserial...
    """
    candidates: list[str] = []

    for port in list_ports.comports():
        device_name = port.device.lower()
        description = (port.description or "").lower()

        looks_like_usb_serial = (
            "usbmodem" in device_name
            or "usbserial" in device_name
            or "esp32" in description
            or "jtag" in description
        )

        if looks_like_usb_serial:
            candidates.append(port.device)

    return candidates


def read_available_lines(connection: Serial) -> list[str]:
    """Read all complete lines currently available from the serial port."""
    lines: list[str] = []

    while connection.in_waiting > 0:
        raw_line = connection.readline()

        if not raw_line:
            break

        decoded_line = raw_line.decode(
            "utf-8",
            errors="replace",
        ).strip()

        if decoded_line:
            lines.append(decoded_line)

    return lines


def send_command(
    connection: Serial,
    command: str,
    wait_seconds: float = 0.3,
) -> list[str]:
    """Send one command and return the response lines."""
    normalized_command = command.strip().upper()

    if not normalized_command:
        return []

    connection.reset_input_buffer()

    payload = f"{normalized_command}\n".encode("utf-8")
    connection.write(payload)
    connection.flush()

    time.sleep(wait_seconds)

    return read_available_lines(connection)


def test_port(port_name: str) -> Optional[DeviceConnection]:
    """Open one port and verify that it responds to the PING command."""
    print(f"Testing port: {port_name}")

    try:
        connection = serial.Serial(
            port=port_name,
            baudrate=BAUD_RATE,
            timeout=SERIAL_TIMEOUT_SECONDS,
        )
    except serial.SerialException as error:
        print(f"Unable to open {port_name}: {error}")
        return None

    time.sleep(DEVICE_BOOT_DELAY_SECONDS)
    connection.reset_input_buffer()

    response = send_command(
        connection,
        "PING",
        wait_seconds=0.5,
    )

    if "PONG" in response:
        print(f"CyberDesk found on {port_name}")
        return DeviceConnection(
            port=port_name,
            serial=connection,
        )

    print(f"No CyberDesk response on {port_name}")
    connection.close()
    return None


def connect_to_cyberdesk() -> Optional[DeviceConnection]:
    """Search candidate ports and connect to the first CyberDesk device."""
    candidate_ports = find_candidate_ports()

    if not candidate_ports:
        print("No likely USB serial ports found.")
        print("Available ports:", list_serial_ports())
        return None

    print("Candidate ports:")

    for port_name in candidate_ports:
        print(f"  - {port_name}")

    for port_name in candidate_ports:
        device = test_port(port_name)

        if device is not None:
            return device

    return None


def print_response(command: str, response: list[str]) -> None:
    """Print a command response in a readable form."""
    print()
    print(f"> {command}")

    if not response:
        print("(no response)")
        return

    for line in response:
        print(line)


def run_interactive_client(device: DeviceConnection) -> None:
    """Run the interactive CyberDesk command-line client."""
    connection = device.serial

    print()
    print("CyberDesk Desktop Client")
    print(f"Connected port: {device.port}")
    print()
    print("Commands:")
    print("  info      - Read device information")
    print("  status    - Read device status")
    print("  next      - Go to next page")
    print("  previous  - Go to previous page")
    print("  clock     - Open clock page")
    print("  system    - Open system page")
    print("  desktop   - Open desktop metrics page")
    print("  device    - Open device information page")
    print("  ping      - Test connection")
    print("  quit      - Close client")

    command_map = {
        "info": "GET_INFO",
        "status": "GET_STATUS",
        "next": "PAGE_NEXT",
        "previous": "PAGE_PREVIOUS",
        "clock": "PAGE_CLOCK",
        "system": "PAGE_SYSTEM",
        "desktop": "PAGE_DESKTOP",
        "device": "PAGE_INFO",
        "ping": "PING",
    }

    while True:
        try:
            user_input = input("\nCyberDesk> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input in {"quit", "exit"}:
            break

        serial_command = command_map.get(user_input)

        if serial_command is None:
            print("Unknown command.")
            continue

        response = send_command(
            connection,
            serial_command,
        )

        print_response(
            serial_command,
            response,
        )


def main() -> int:
    device = connect_to_cyberdesk()

    if device is None:
        print()
        print("CyberDesk was not found.")
        print("Check the USB cable and close PlatformIO Serial Monitor.")
        return 1

    try:
        run_interactive_client(device)
    finally:
        device.serial.close()
        print("Serial connection closed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())