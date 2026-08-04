#include <Arduino.h>
#include <Arduino_GFX_Library.h>
#include <WiFi.h>
#include <time.h>

#include "secrets.h"
#include "time_sync_retry.h"

namespace Pins {
constexpr uint8_t POWER_ON = 15;
constexpr uint8_t LCD_BACKLIGHT = 38;
constexpr uint8_t BUTTON_1 = 0;
constexpr uint8_t BUTTON_2 = 14;
}  // namespace Pins

namespace DisplayConfig {
constexpr int16_t WIDTH = 320;
constexpr int16_t HEIGHT = 170;
}  // namespace DisplayConfig

namespace NetworkConfig {
constexpr uint32_t CONNECTION_TIMEOUT_MS = 15000;
constexpr uint32_t RETRY_INTERVAL_MS = 10000;
}  // namespace NetworkConfig

namespace ButtonConfig {
constexpr uint32_t DEBOUNCE_DELAY_MS = 40;
}

namespace TimeConfig {
constexpr long GMT_OFFSET_SECONDS = 8 * 3600;
constexpr int DAYLIGHT_OFFSET_SECONDS = 0;

constexpr const char* NTP_SERVER_1 = "pool.ntp.org";
constexpr const char* NTP_SERVER_2 = "time.google.com";

constexpr uint32_t SYNC_TIMEOUT_MS = 15000;
constexpr uint32_t SYNC_RETRY_INTERVAL_MS = 60000;
constexpr uint32_t SCREEN_UPDATE_INTERVAL_MS = 1000;
}  // namespace TimeConfig

namespace UiConfig {
constexpr uint32_t WIFI_STATUS_UPDATE_INTERVAL_MS = 5000;
constexpr uint32_t SYSTEM_UPDATE_INTERVAL_MS = 1000;

constexpr int16_t TIME_X = 50;
constexpr int16_t TIME_Y = 48;
constexpr int16_t TIME_WIDTH = 220;
constexpr int16_t TIME_HEIGHT = 42;

constexpr int16_t DATE_X = 80;
constexpr int16_t DATE_Y = 105;
constexpr int16_t DATE_WIDTH = 160;
constexpr int16_t DATE_HEIGHT = 24;

constexpr int16_t WIFI_X = 205;
constexpr int16_t WIFI_Y = 12;
constexpr int16_t WIFI_WIDTH = 110;
constexpr int16_t WIFI_HEIGHT = 12;
}  // namespace UiConfig

enum class ScreenPage : uint8_t {
    CLOCK = 0,
    SYSTEM,
    INFO,
    COUNT
};

Arduino_DataBus* bus = new Arduino_ESP32PAR8Q(
    7,   // DC
    6,   // CS
    8,   // WR
    9,   // RD
    39,  // D0
    40,  // D1
    41,  // D2
    42,  // D3
    45,  // D4
    46,  // D5
    47,  // D6
    48   // D7
);

Arduino_GFX* display = new Arduino_ST7789(
    bus,
    5,     // RST
    1,     // Rotation
    true,  // IPS
    170,
    320,
    35,
    0,
    35,
    0
);

uint32_t lastReconnectAttempt = 0;
uint32_t lastTimeSyncAttempt = 0;
uint32_t lastScreenUpdate = 0;
uint32_t lastWiFiStatusUpdate = 0;
uint32_t lastSystemUpdate = 0;

bool button1LastReading = HIGH;
bool button1StableState = HIGH;
uint32_t button1LastChangeTime = 0;

bool button2LastReading = HIGH;
bool button2StableState = HIGH;
uint32_t button2LastChangeTime = 0;

bool timeSynchronized = false;
bool clockScreenInitialized = false;
ScreenPage currentPage = ScreenPage::CLOCK;
bool pageNeedsRedraw = true;

String serialCommandBuffer;

char lastDisplayedDate[16] = "";

void drawCenteredText(
    const String& text,
    int16_t y,
    uint16_t color,
    uint8_t textSize
) {
    display->setTextColor(color);
    display->setTextSize(textSize);

    const int16_t textWidth =
        static_cast<int16_t>(text.length() * 6 * textSize);

    const int16_t x =
        (DisplayConfig::WIDTH - textWidth) / 2;

    display->setCursor(x, y);
    display->print(text);
}

void drawConnectingScreen() {
    display->fillScreen(BLACK);

    drawCenteredText("CyberDesk", 32, CYAN, 3);
    drawCenteredText("Connecting to Wi-Fi", 85, WHITE, 2);
    drawCenteredText("Please wait...", 120, DARKGREY, 1);
}

void drawConnectedScreen() {
    display->fillScreen(BLACK);

    drawCenteredText("CyberDesk", 22, CYAN, 3);
    drawCenteredText("Wi-Fi Connected", 68, GREEN, 2);

    display->setTextSize(1);
    display->setTextColor(WHITE);

    display->setCursor(28, 112);
    display->print("SSID: ");
    display->print(WiFi.SSID());

    display->setCursor(28, 136);
    display->print("IP: ");
    display->print(WiFi.localIP());
}

void drawClockLayout() {
    display->fillScreen(BLACK);

    display->setTextColor(CYAN);
    display->setTextSize(2);
    display->setCursor(12, 12);
    display->print("CyberDesk");

    display->drawFastHLine(
        10,
        34,
        DisplayConfig::WIDTH - 20,
        DARKGREY
    );

    display->drawFastHLine(
        10,
        140,
        DisplayConfig::WIDTH - 20,
        DARKGREY
    );

    display->setTextColor(DARKGREY);
    display->setTextSize(1);
    display->setCursor(12, 151);
    display->print("IP");

    display->setTextColor(WHITE);
    display->setCursor(30, 151);
    display->print(WiFi.localIP());

    display->setTextColor(DARKGREY);
    display->setTextSize(1);
    display->setCursor(235, 151);
    display->print("<  PAGE  >");

    clockScreenInitialized = true;
}

void updateTimeArea(const tm& timeInfo) {
    char timeText[16];

    strftime(
        timeText,
        sizeof(timeText),
        "%H:%M:%S",
        &timeInfo
    );

    display->fillRect(
        UiConfig::TIME_X,
        UiConfig::TIME_Y,
        UiConfig::TIME_WIDTH,
        UiConfig::TIME_HEIGHT,
        BLACK
    );

    drawCenteredText(
        timeText,
        UiConfig::TIME_Y,
        WHITE,
        4
    );
}

void updateDateArea(const tm& timeInfo) {
    char dateText[16];

    strftime(
        dateText,
        sizeof(dateText),
        "%Y-%m-%d",
        &timeInfo
    );

    if (strcmp(dateText, lastDisplayedDate) == 0) {
        return;
    }

    strncpy(
        lastDisplayedDate,
        dateText,
        sizeof(lastDisplayedDate) - 1
    );

    lastDisplayedDate[sizeof(lastDisplayedDate) - 1] = '\0';

    display->fillRect(
        UiConfig::DATE_X,
        UiConfig::DATE_Y,
        UiConfig::DATE_WIDTH,
        UiConfig::DATE_HEIGHT,
        BLACK
    );

    drawCenteredText(
        dateText,
        UiConfig::DATE_Y,
        GREEN,
        2
    );
}

void updateWiFiStatusArea() {
    display->fillRect(
        UiConfig::WIFI_X,
        UiConfig::WIFI_Y,
        UiConfig::WIFI_WIDTH,
        UiConfig::WIFI_HEIGHT,
        BLACK
    );

    display->setTextSize(1);
    display->setCursor(
        UiConfig::WIFI_X,
        UiConfig::WIFI_Y
    );

    if (WiFi.status() != WL_CONNECTED) {
        display->setTextColor(RED);
        display->print("WiFi Offline");
        return;
    }

    const int32_t rssi = WiFi.RSSI();

    uint16_t signalColor = GREEN;

    if (rssi < -75) {
        signalColor = RED;
    } else if (rssi < -60) {
        signalColor = YELLOW;
    }

    display->setTextColor(signalColor);
    display->print("WiFi ");
    display->print(rssi);
    display->print(" dBm");
}

void updateClockScreen() {
    tm timeInfo{};

    if (!getLocalTime(&timeInfo)) {
        Serial.println("Unable to read local time");
        timeSynchronized = false;
        return;
    }

    if (!clockScreenInitialized) {
        drawClockLayout();
        updateWiFiStatusArea();
    }

    updateTimeArea(timeInfo);
    updateDateArea(timeInfo);
}

void drawSystemLayout() {
    display->fillScreen(BLACK);

    display->setTextColor(CYAN);
    display->setTextSize(2);
    display->setCursor(12, 12);
    display->print("SYSTEM");

    display->drawFastHLine(
        10,
        36,
        DisplayConfig::WIDTH - 20,
        DARKGREY
    );

    display->setTextSize(1);
    display->setTextColor(DARKGREY);

    display->setCursor(20, 55);
    display->print("Wi-Fi");

    display->setCursor(20, 80);
    display->print("IP");

    display->setCursor(20, 105);
    display->print("Signal");

    display->setCursor(20, 130);
    display->print("Uptime");

    display->setCursor(12, 155);
    display->print("< Previous       Next >");
}

void updateSystemData() {
    // 清除右侧动态数据显示区域
    display->fillRect(
        105,
        45,
        210,
        100,
        BLACK
    );

    display->setTextSize(1);

    // Wi-Fi status
    display->setCursor(110, 55);

    if (WiFi.status() == WL_CONNECTED) {
        display->setTextColor(GREEN);
        display->print("Connected");
    } else {
        display->setTextColor(RED);
        display->print("Offline");
    }

    // IP address
    display->setTextColor(WHITE);
    display->setCursor(110, 80);

    if (WiFi.status() == WL_CONNECTED) {
        display->print(WiFi.localIP());
    } else {
        display->print("---.---.---.---");
    }

    // Signal strength
    display->setCursor(110, 105);

    if (WiFi.status() == WL_CONNECTED) {
        const int32_t rssi = WiFi.RSSI();

        if (rssi < -75) {
            display->setTextColor(RED);
        } else if (rssi < -60) {
            display->setTextColor(YELLOW);
        } else {
            display->setTextColor(GREEN);
        }

        display->print(rssi);
        display->print(" dBm");
    } else {
        display->setTextColor(RED);
        display->print("Unavailable");
    }

    // Uptime
    display->setTextColor(WHITE);
    display->setCursor(110, 130);

    const uint32_t uptimeSeconds = millis() / 1000;
    const uint32_t hours = uptimeSeconds / 3600;
    const uint32_t minutes = (uptimeSeconds % 3600) / 60;
    const uint32_t seconds = uptimeSeconds % 60;

    char uptimeText[16];

    snprintf(
        uptimeText,
        sizeof(uptimeText),
        "%02lu:%02lu:%02lu",
        static_cast<unsigned long>(hours),
        static_cast<unsigned long>(minutes),
        static_cast<unsigned long>(seconds)
    );

    display->print(uptimeText);
}

void drawInfoScreen() {
    display->fillScreen(BLACK);

    display->setTextColor(CYAN);
    display->setTextSize(2);
    display->setCursor(12, 12);
    display->print("DEVICE INFO");

    display->drawFastHLine(
        10,
        36,
        DisplayConfig::WIDTH - 20,
        DARKGREY
    );

    display->setTextSize(1);

    display->setTextColor(DARKGREY);
    display->setCursor(20, 55);
    display->print("Project");

    display->setTextColor(WHITE);
    display->setCursor(110, 55);
    display->print("CyberDesk");

    display->setTextColor(DARKGREY);
    display->setCursor(20, 80);
    display->print("Board");

    display->setTextColor(WHITE);
    display->setCursor(110, 80);
    display->print("T-Display-S3");

    display->setTextColor(DARKGREY);
    display->setCursor(20, 105);
    display->print("Chip");

    display->setTextColor(WHITE);
    display->setCursor(110, 105);
    display->print("ESP32-S3");

    display->setTextColor(DARKGREY);
    display->setCursor(20, 130);
    display->print("Firmware");

    display->setTextColor(GREEN);
    display->setCursor(110, 130);
    display->print("Phase 4");

    display->setTextColor(DARKGREY);
    display->setCursor(12, 155);
    display->print("< Previous       Next >");
}

void drawCurrentPage() {
    switch (currentPage) {
        case ScreenPage::CLOCK:
            clockScreenInitialized = false;
            lastDisplayedDate[0] = '\0';

            updateClockScreen();
            updateWiFiStatusArea();

            Serial.println("Page: CLOCK");
            break;

        case ScreenPage::SYSTEM:
            drawSystemLayout();
            updateSystemData();

            lastSystemUpdate = millis();

            Serial.println("Page: SYSTEM");
            break;

        case ScreenPage::INFO:
            drawInfoScreen();

            Serial.println("Page: INFO");
            break;

        case ScreenPage::COUNT:
            currentPage = ScreenPage::CLOCK;
            pageNeedsRedraw = true;
            return;
    }

    pageNeedsRedraw = false;
}

void goToNextPage() {
    const uint8_t pageCount =
        static_cast<uint8_t>(ScreenPage::COUNT);

    uint8_t pageIndex =
        static_cast<uint8_t>(currentPage);

    pageIndex = (pageIndex + 1) % pageCount;

    currentPage =
        static_cast<ScreenPage>(pageIndex);

    pageNeedsRedraw = true;
}

void goToPreviousPage() {
    const uint8_t pageCount =
        static_cast<uint8_t>(ScreenPage::COUNT);

    uint8_t pageIndex =
        static_cast<uint8_t>(currentPage);

    pageIndex =
        (pageIndex + pageCount - 1) % pageCount;

    currentPage =
        static_cast<ScreenPage>(pageIndex);

    pageNeedsRedraw = true;
}

bool synchronizeTime() {
    lastTimeSyncAttempt = millis();

    Serial.println();
    Serial.println("Synchronizing network time...");

    configTime(
        TimeConfig::GMT_OFFSET_SECONDS,
        TimeConfig::DAYLIGHT_OFFSET_SECONDS,
        TimeConfig::NTP_SERVER_1,
        TimeConfig::NTP_SERVER_2
    );

    const uint32_t startTime = millis();
    tm timeInfo{};

    while (
        !getLocalTime(&timeInfo) &&
        millis() - startTime < TimeConfig::SYNC_TIMEOUT_MS
    ) {
        Serial.print(".");
        delay(500);
    }

    Serial.println();

    if (!getLocalTime(&timeInfo)) {
        Serial.println("NTP synchronization failed");
        return false;
    }

    Serial.println("Network time synchronized");

    char timeText[32];
    strftime(
        timeText,
        sizeof(timeText),
        "%Y-%m-%d %H:%M:%S",
        &timeInfo
    );

    Serial.print("Local time: ");
    Serial.println(timeText);

    clockScreenInitialized = false;
    lastDisplayedDate[0] = '\0';

    updateClockScreen();
    updateWiFiStatusArea();

    return true;
}
void drawConnectionFailedScreen() {
    display->fillScreen(BLACK);

    drawCenteredText("CyberDesk", 28, CYAN, 3);
    drawCenteredText("Wi-Fi Failed", 78, RED, 2);
    drawCenteredText("Retrying automatically", 118, WHITE, 1);
}

bool connectToWiFi() {
    Serial.println();
    Serial.println("============================");
    Serial.println("CyberDesk Wi-Fi Connection");
    Serial.print("SSID: ");
    Serial.println(WIFI_SSID);
    Serial.println("============================");

    drawConnectingScreen();

    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(false);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    const uint32_t startTime = millis();

    while (
        WiFi.status() != WL_CONNECTED &&
        millis() - startTime < NetworkConfig::CONNECTION_TIMEOUT_MS
    ) {
        Serial.print(".");
        delay(500);
    }

    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Wi-Fi connected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());

        drawConnectedScreen();
        return true;
    }

    Serial.println("Wi-Fi connection failed");
    drawConnectionFailedScreen();
    return false;
}

bool wasButtonPressed(
    uint8_t pin,
    bool& lastReading,
    bool& stableState,
    uint32_t& lastChangeTime
) {
    const bool currentReading = digitalRead(pin);
    const uint32_t currentTime = millis();

    if (currentReading != lastReading) {
        lastReading = currentReading;
        lastChangeTime = currentTime;
    }

    if (
        currentTime - lastChangeTime >=
        ButtonConfig::DEBOUNCE_DELAY_MS
    ) {
        if (currentReading != stableState) {
            stableState = currentReading;

            // INPUT_PULLUP means LOW represents a pressed button.
            if (stableState == LOW) {
                return true;
            }
        }
    }

    return false;
}

const char* getCurrentPageName() {
    switch (currentPage) {
        case ScreenPage::CLOCK:
            return "CLOCK";

        case ScreenPage::SYSTEM:
            return "SYSTEM";

        case ScreenPage::INFO:
            return "INFO";

        case ScreenPage::COUNT:
            return "UNKNOWN";
    }

    return "UNKNOWN";
}

void handleSerialCommand(String command) {
    command.trim();
    command.toUpperCase();

    if (command.isEmpty()) {
        return;
    }

    Serial.print("[COMMAND] ");
    Serial.println(command);

    if (command == "PING") {
        Serial.println("PONG");
        return;
    }

    if (command == "GET_INFO") {
        Serial.println("DEVICE:CyberDesk");
        Serial.println("BOARD:LILYGO_T_DISPLAY_S3");
        Serial.println("CHIP:ESP32-S3");
        Serial.println("FIRMWARE:PHASE_4");
        Serial.print("PAGE:");
        Serial.println(getCurrentPageName());
        return;
    }

    if (command == "GET_STATUS") {
        Serial.print("WIFI:");

        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("CONNECTED");

            Serial.print("IP:");
            Serial.println(WiFi.localIP());

            Serial.print("RSSI:");
            Serial.println(WiFi.RSSI());
        } else {
            Serial.println("DISCONNECTED");
            Serial.println("IP:0.0.0.0");
            Serial.println("RSSI:0");
        }

        Serial.print("UPTIME_MS:");
        Serial.println(millis());

        Serial.print("PAGE:");
        Serial.println(getCurrentPageName());

        return;
    }

    if (command == "PAGE_NEXT") {
        goToNextPage();

        Serial.print("OK:PAGE:");
        Serial.println(getCurrentPageName());
        return;
    }

    if (command == "PAGE_PREVIOUS") {
        goToPreviousPage();

        Serial.print("OK:PAGE:");
        Serial.println(getCurrentPageName());
        return;
    }

    if (command == "PAGE_CLOCK") {
        currentPage = ScreenPage::CLOCK;
        pageNeedsRedraw = true;

        Serial.println("OK:PAGE:CLOCK");
        return;
    }

    if (command == "PAGE_SYSTEM") {
        currentPage = ScreenPage::SYSTEM;
        pageNeedsRedraw = true;

        Serial.println("OK:PAGE:SYSTEM");
        return;
    }

    if (command == "PAGE_INFO") {
        currentPage = ScreenPage::INFO;
        pageNeedsRedraw = true;

        Serial.println("OK:PAGE:INFO");
        return;
    }

    Serial.print("ERROR:UNKNOWN_COMMAND:");
    Serial.println(command);
}

void handleSerialInput() {
    while (Serial.available() > 0) {
        const char receivedCharacter =
            static_cast<char>(Serial.read());

        if (receivedCharacter == '\n') {
            handleSerialCommand(serialCommandBuffer);
            serialCommandBuffer = "";
            continue;
        }

        if (receivedCharacter == '\r') {
            continue;
        }

        if (serialCommandBuffer.length() < 128) {
            serialCommandBuffer += receivedCharacter;
        } else {
            serialCommandBuffer = "";
            Serial.println("ERROR:COMMAND_TOO_LONG");
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    pinMode(Pins::POWER_ON, OUTPUT);
    digitalWrite(Pins::POWER_ON, HIGH);

    pinMode(Pins::LCD_BACKLIGHT, OUTPUT);
    digitalWrite(Pins::LCD_BACKLIGHT, HIGH);

    pinMode(Pins::BUTTON_1, INPUT_PULLUP);
    pinMode(Pins::BUTTON_2, INPUT_PULLUP);

    display->begin();

    if (connectToWiFi()) {
        delay(1000);
        timeSynchronized = synchronizeTime();
    }
}

void loop() {
    const uint32_t currentTime = millis();

    handleSerialInput();

    // Button 1: previous page
    if (
        wasButtonPressed(
            Pins::BUTTON_1,
            button1LastReading,
            button1StableState,
            button1LastChangeTime
        )
    ) {
        Serial.println("Button 1: previous page");
        goToPreviousPage();
    }

    // Button 2: next page
    if (
        wasButtonPressed(
            Pins::BUTTON_2,
            button2LastReading,
            button2StableState,
            button2LastChangeTime
        )
    ) {
        Serial.println("Button 2: next page");
        goToNextPage();
    }

    // Redraw after page navigation
    if (pageNeedsRedraw) {
        drawCurrentPage();
    }


    if (WiFi.status() != WL_CONNECTED) {
        timeSynchronized = false;
        clockScreenInitialized = false;

        if (
            currentTime - lastReconnectAttempt >=
            NetworkConfig::RETRY_INTERVAL_MS
        ) {
            lastReconnectAttempt = currentTime;

            Serial.println(
                "Wi-Fi disconnected. Reconnecting..."
            );

            drawConnectionFailedScreen();

            if (connectToWiFi()) {
                timeSynchronized = synchronizeTime();
            }
        }

        delay(100);
        return;
    }

    if (
        !timeSynchronized &&
        isTimeSyncRetryDue(
            currentTime,
            lastTimeSyncAttempt,
            TimeConfig::SYNC_RETRY_INTERVAL_MS
        )
    ) {
        timeSynchronized = synchronizeTime();
    }

    if (
        currentPage == ScreenPage::CLOCK &&
        timeSynchronized &&
        currentTime - lastScreenUpdate >=
            TimeConfig::SCREEN_UPDATE_INTERVAL_MS
    ) {
        lastScreenUpdate = currentTime;
        updateClockScreen();
    }

    if (
    currentPage == ScreenPage::CLOCK &&
    timeSynchronized &&
    currentTime - lastScreenUpdate >=
        TimeConfig::SCREEN_UPDATE_INTERVAL_MS
) {
    lastScreenUpdate = currentTime;
    updateClockScreen();
}

if (
    currentPage == ScreenPage::SYSTEM &&
    currentTime - lastSystemUpdate >=
        UiConfig::SYSTEM_UPDATE_INTERVAL_MS
) {
    lastSystemUpdate = currentTime;
    updateSystemData();
}

if (
    currentPage == ScreenPage::CLOCK &&
    currentTime - lastWiFiStatusUpdate >=
        UiConfig::WIFI_STATUS_UPDATE_INTERVAL_MS
) {
    lastWiFiStatusUpdate = currentTime;
    updateWiFiStatusArea();
}

    delay(20);
}
