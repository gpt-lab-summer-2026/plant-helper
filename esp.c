#include <Arduino.h>
#include <ArduinoJson.h>

#define MOISTURE_PIN 3
#define LED_PIN 20
#define SAMPLE_US 125
#define BATCH_SIZE 64
#define MOISTURE_INTERVAL 1000

unsigned long last_moisture_time = 0;
int last_moisture = 0;
bool recording = false;
String cmd_buffer = "";

void setup() {
  Serial.begin(921600);
  analogReadResolution(12);  // 12-bit ADC, 0-4095
  analogSetAttenuation(ADC_11db);  // full 0-3.3V range

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
}

void checkForCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      cmd_buffer.trim();
      if (cmd_buffer == "START") {
        recording = true;
        digitalWrite(LED_PIN, HIGH);
      } else if (cmd_buffer == "STOP") {
        recording = false;
        digitalWrite(LED_PIN, LOW);
      }
      cmd_buffer = "";
    } else {
      cmd_buffer += c;
    }
  }
}

void loop() {
  checkForCommands();
  unsigned long now = millis();

    // moisture every MOISTURE_INTERVAL ms
  if (now - last_moisture_time >= MOISTURE_INTERVAL) {
    last_moisture = analogRead(MOISTURE_PIN);
    last_moisture_time = now;
    StaticJsonDocument<64> moisture_doc;
    moisture_doc["m"] = last_moisture;
    serializeJson(moisture_doc, Serial);
    Serial.println();
  }
}
  