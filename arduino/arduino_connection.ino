/*
 * Pick-A-Book Library System
 * Arduino sketch — 16x2 I2C LCD display
 *
 * HARDWARE:
 *   - Arduino Uno / Nano / Mega
 *   - 16x2 LCD with PCF8574 I2C backpack
 *
 * WIRING (I2C):
 *   LCD VCC  → 5V
 *   LCD GND  → GND
 *   LCD SDA  → A4  (Uno/Nano) or pin 20 (Mega)
 *   LCD SCL  → A5  (Uno/Nano) or pin 21 (Mega)
 *
 * LIBRARIES REQUIRED (install via Arduino Library Manager):
 *   - LiquidCrystal_I2C  by Frank de Brabander
 *   - Wire                (built-in)
 *
 * SERIAL PROTOCOL (from Flask → Arduino):
 *   One line per message, newline-terminated:
 *       LINE1|LINE2\n
 *   Examples:
 *       Login OK|Juan dela Cruz\n
 *       Borrowed:|Juan - Clean Code\n
 *       Returned OK!|Clean Code\n
 *       Login Failed|Wrong password\n
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ── I2C address: 0x27 is most common; try 0x3F if LCD stays blank ──
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ── How long each message stays on screen (ms) ──
const unsigned long MSG_DURATION = 4000;

// ── Serial input buffer ──
String inputBuffer = "";
bool   msgReady    = false;

// ── Current display state ──
unsigned long msgShownAt  = 0;
bool          showingMsg  = false;

// ── Custom characters ──
byte bookChar[8] = {
  0b00000,
  0b11111,
  0b10001,
  0b10001,
  0b11111,
  0b10001,
  0b11111,
  0b00000
};


// ════════════════════════════════════════════════════════
void setup() {
  Serial.begin(9600);

  lcd.init();
  lcd.backlight();
  lcd.createChar(0, bookChar);

  // Splash screen
  lcd.setCursor(0, 0);
  lcd.write(byte(0));
  lcd.print(" Pick-A-Book");
  lcd.setCursor(0, 1);
  lcd.print("  Loading...");
  delay(2000);
  showIdle();
}


// ════════════════════════════════════════════════════════
void loop() {

  // ── Read incoming serial data byte by byte ──
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      msgReady = true;
      break;
    }
    inputBuffer += c;
  }

  // ── Process a complete message ──
  if (msgReady) {
    processMessage(inputBuffer);
    inputBuffer = "";
    msgReady    = false;
  }

  // ── Return to idle after MSG_DURATION ms ──
  if (showingMsg && (millis() - msgShownAt >= MSG_DURATION)) {
    showingMsg = false;
    showIdle();
  }
}


// ════════════════════════════════════════════════════════
void processMessage(String msg) {
  msg.trim();
  if (msg.length() == 0) return;

  int sep = msg.indexOf('|');
  String line1 = (sep >= 0) ? msg.substring(0, sep)  : msg;
  String line2 = (sep >= 0) ? msg.substring(sep + 1) : "";

  // Truncate to 16 characters
  if (line1.length() > 16) line1 = line1.substring(0, 16);
  if (line2.length() > 16) line2 = line2.substring(0, 16);

  // Choose icon prefix based on message content
  String icon = getIcon(line1);

  lcd.clear();

  // Row 0: icon + line1
  lcd.setCursor(0, 0);
  if (icon == "BOOK") {
    lcd.write(byte(0));
    lcd.print(" ");
    int maxLen = 14;
    lcd.print(line1.length() > maxLen ? line1.substring(0, maxLen) : line1);
  } else {
    lcd.print(line1);
  }

  // Row 1: line2
  lcd.setCursor(0, 1);
  lcd.print(line2);

  msgShownAt = millis();
  showingMsg = true;

  // Echo back to Flask for logging
  Serial.print("ACK:");
  Serial.println(msg);
}


// ════════════════════════════════════════════════════════
String getIcon(String line1) {
  String l = line1;
  l.toLowerCase();
  if (l.indexOf("borrow") >= 0) return "BOOK";
  if (l.indexOf("return") >= 0) return "BOOK";
  return "NONE";
}


// ════════════════════════════════════════════════════════
void showIdle() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.write(byte(0));
  lcd.print(" Pick-A-Book");
  lcd.setCursor(0, 1);
  lcd.print("Ready...");
}
