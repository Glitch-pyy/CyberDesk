#include <Arduino.h>
#include <Arduino_GFX_Library.h>

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

void drawCenteredText(
    const char* text,
    int16_t y,
    uint16_t color,
    uint8_t textSize
) {
    display->setTextColor(color);
    display->setTextSize(textSize);

    const int16_t textWidth =
        static_cast<int16_t>(strlen(text) * 6 * textSize);

    const int16_t x =
        (DisplayConfig::WIDTH - textWidth) / 2;

    display->setCursor(x, y);
    display->println(text);
}

void drawHomeScreen() {
    display->fillScreen(BLACK);

    drawCenteredText("CyberDesk", 38, CYAN, 3);
    drawCenteredText("Phase 1", 82, WHITE, 2);

    display->drawRoundRect(
        38,
        118,
        244,
        38,
        8,
        DARKGREY
    );

    drawCenteredText("Hardware Online", 130, GREEN, 2);
}

void showButtonScreen(
    const char* label,
    uint16_t backgroundColor,
    uint16_t textColor
) {
    display->fillScreen(backgroundColor);
    drawCenteredText(label, 72, textColor, 3);
}

void waitForButtonRelease(uint8_t pin) {
    while (digitalRead(pin) == LOW) {
        delay(10);
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
    drawHomeScreen();

    Serial.println();
    Serial.println("============================");
    Serial.println("CyberDesk Phase 1");
    Serial.println("Display initialized");
    Serial.println("Hardware online");
    Serial.println("============================");
}

void loop() {
    if (digitalRead(Pins::BUTTON_1) == LOW) {
        Serial.println("Button 1 pressed");

        showButtonScreen(
            "Button 1",
            BLUE,
            WHITE
        );

        delay(400);
        drawHomeScreen();
        waitForButtonRelease(Pins::BUTTON_1);
    }

    if (digitalRead(Pins::BUTTON_2) == LOW) {
        Serial.println("Button 2 pressed");

        showButtonScreen(
            "Button 2",
            GREEN,
            BLACK
        );

        delay(400);
        drawHomeScreen();
        waitForButtonRelease(Pins::BUTTON_2);
    }

    delay(10);
}