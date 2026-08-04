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
- Dual-button navigation with software debouncing
- Multi-page user interface
- Clock dashboard page
- System status page with dynamic uptime and network data
- Device information page
- Circular previous/next page navigation
- Local credential configuration excluded from Git

## Controls

The two onboard buttons are used for page navigation:

- Button 1 (GPIO 0): Previous page
- Button 2 (GPIO 14): Next page

Available pages:

1. Clock
2. System Status
3. Device Information

## Firmware Setup

1. Copy the example credential file:

```bash
cp firmware/include/secrets.example.h firmware/include/secrets.h
```

## Project Structure

```text
CyberDesk/
├── desktop/       # Desktop-side application
├── docs/          # Project documentation
├── firmware/      # ESP32-S3 PlatformIO firmware
├── hardware/      # Schematics, wiring and future PCB files
├── images/        # Project images and screenshots
└── web/           # Web configuration interface
```

## Development Status

- Phase 0: Project initialization — Complete
- Phase 1: Hardware bring-up — Complete
- Phase 2: Network clock dashboard — Complete
- Phase 3: Multi-page UI and button navigation — Complete
- Phase 4: Desktop communication — Planned