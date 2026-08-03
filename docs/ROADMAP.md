# CyberDesk Roadmap

## Phase 0: Project Setup

- [x] Create GitHub repository
- [x] Initialize project structure
- [x] Install VS Code and PlatformIO
- [x] Configure LILYGO T-Display-S3 development environment

## Phase 1: Hardware Bring-Up

- [x] Initialize the LILYGO T-Display-S3
- [x] Enable LCD power and backlight
- [x] Render the CyberDesk startup screen
- [x] Read the two onboard buttons
- [x] Display button feedback on the screen
- [x] Configure PlatformIO build and upload workflow

## Phase 2: Network Clock Dashboard

- [x] Add local Wi-Fi credential configuration
- [x] Protect credentials with `.gitignore`
- [x] Connect the ESP32-S3 to Wi-Fi
- [x] Display SSID and local IP address
- [x] Add automatic Wi-Fi reconnection
- [x] Synchronize time using NTP
- [x] Display the current time and date
- [x] Display Wi-Fi RSSI signal strength
- [x] Use partial screen updates to reduce flicker

## Phase 3: Desktop Dashboard Features

- [ ] Add multiple dashboard pages
- [ ] Restore onboard button navigation
- [ ] Add system status cards
- [ ] Add weather information
- [ ] Add configurable timezone support
- [ ] Improve UI layout and icons

## Phase 4: Desktop Companion Application

- [ ] Create the desktop-side application
- [ ] Read CPU, memory and storage usage
- [ ] Send computer statistics to CyberDesk
- [ ] Design a communication protocol
- [ ] Add automatic device discovery

## Phase 5: Configuration and Expansion

- [ ] Create a web configuration panel
- [ ] Add OTA firmware updates
- [ ] Add plugin-based modules
- [ ] Design a custom PCB
- [ ] Design a 3D-printed enclosure