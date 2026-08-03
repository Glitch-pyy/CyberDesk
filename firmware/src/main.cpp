#include <Arduino.h>
#include <Arduino_GFX_Library.h>
#include <WiFi.h>
#include <time.h>

#include "secrets.h"

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

namespace TimeConfig {
constexpr long GMT_OFFSET_SECONDS = 8 * 3600;
constexpr int DAYLIGHT_OFFSET_SECONDS = 0;

constexpr const char* NTP_SERVER_1 = "pool.ntp.org";
constexpr const char* NTP_SERVER_2 = "time.google.com";

constexpr uint32_t SYNC_TIMEOUT_MS = 15000;
constexpr uint32_t SCREEN_UPDATE_INTERVAL_MS = 1000;
}  // namespace TimeConfig

namespace UiConfig {
constexpr uint32_t WIFI_STATUS_UPDATE_INTERVAL_MS = 5000;

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
uint32_t lastScreenUpdate = 0;
uint32_t lastWiFiStatusUpdate = 0;

bool timeSynchronized = false;
bool clockScreenInitialized = false;

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

bool synchronizeTime() {
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

    if (!timeSynchronized) {
        timeSynchronized = synchronizeTime();
    }

    if (
        timeSynchronized &&
        currentTime - lastScreenUpdate >=
            TimeConfig::SCREEN_UPDATE_INTERVAL_MS
    ) {
        lastScreenUpdate = currentTime;
        updateClockScreen();
    }

    if (
        currentTime - lastWiFiStatusUpdate >=
            UiConfig::WIFI_STATUS_UPDATE_INTERVAL_MS
    ) {
        lastWiFiStatusUpdate = currentTime;
        updateWiFiStatusArea();
    }

    delay(20);
}