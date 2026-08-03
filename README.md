# CyberDesk

CyberDesk is an open-source modular desktop hardware system based on the ESP32-S3.

The project is currently built around the LILYGO T-Display-S3 development board.

## Goals

- Desktop status dashboard
- Custom Stream Deck
- Plugin-based hardware modules
- Web configuration panel
- OTA firmware updates
- Future custom PCB and 3D-printed enclosure

## Hardware

Current development hardware:

- LILYGO T-Display-S3
- ESP32-S3R8
- 16 MB Flash
- 8 MB OPI PSRAM
- 1.9-inch 170 × 320 IPS display
- Two onboard buttons
- USB-C connection

## Current Features

- LILYGO T-Display-S3 support
- Wi-Fi connection with automatic reconnection
- NTP network time synchronization
- Real-time clock and date display
- Local IP address display
- Wi-Fi RSSI signal strength display
- Partial screen refresh to reduce flicker
- Local credential configuration excluded from Git

## Firmware Setup

1. Copy the example credential file:

```bash
cp firmware/include/secrets.example.h firmware/include/secrets.h

## Project Structure

```text
CyberDesk/
├── desktop/       # Desktop-side application
├── docs/          # Project documentation
├── firmware/      # ESP32-S3 PlatformIO firmware
├── hardware/      # Schematics, wiring and future PCB files
├── images/        # Project images and screenshots
└── web/           # Web configuration interface