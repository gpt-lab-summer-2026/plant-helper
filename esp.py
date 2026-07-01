#include <Arduino.h>
#include <ArduinoJson.h>

#define MOISTURE_PIN 34
#define MIC_PIN 35
#define SAMPLE_US 125
#define BATCH_SIZE 64
#define MOISTURE_INTERVAL 1000

unsigned long last_moisture_time = 0;
int last_moisture = 0;

void setup() {
  Serial.begin(921600);
  analogReadResolution(12);  // 12-bit ADC, 0-4095
  analogSetAttenuation(ADC_11db);  // full 0-3.3V range
}

void loop() {
  unsigned long now = millis();

  // collect audio batch
  StaticJsonDocument<512> audio_doc;
  JsonArray samples = audio_doc.createNestedArray("a");
  for (int i = 0; i < BATCH_SIZE; i++) {
    samples.add(analogRead(MIC_PIN));
    delayMicroseconds(SAMPLE_US);
  }
  serializeJson(audio_doc, Serial);
  Serial.println();

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