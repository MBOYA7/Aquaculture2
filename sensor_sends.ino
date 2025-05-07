#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>

// === WiFi Credentials ===
const char* ssid = "Sammy";
const char* password = "SBarasa123";

// === Supabase API ===
const char* serverURL = "https://nfsrxbievdfztwelbbwg.supabase.co/rest/v1/lakefishcage";
const char* apiKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5mc3J4YmlldmRmenR3ZWxiYndnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ5NTg4MzIsImV4cCI6MjA2MDUzNDgzMn0.SG7HJPCDOa2N3bV57_wFLapCFUA8Bt4ZfVDScB0RT8s";

// === DS18B20 Temp Sensor Setup ===
#define ONE_WIRE_BUS 4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// === Sensor Pins ===
const int phPin = 35;
const int turbidityPin = 32; 

// === Calibration values ===
const float turbMax = 100;  // Clear water
const float turbMin = 1500;   // Very dirty

float temperature = 0.0;
float pH = 0.0;
float turbidityPercent = 0.0;

void setup() {
  Serial.begin(115200);
  sensors.begin();

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

void loop() {
  // === Temperature ===
  sensors.requestTemperatures();
  temperature = sensors.getTempCByIndex(0);

  // === Analog Reads ===
  int rawPH = analogRead(phPin);
  int rawTurb = analogRead(turbidityPin);

  float voltagePH = rawPH * (3.3 / 4095.0);
  float voltageTurb = rawTurb * (3.3 / 4095.0);

  // === pH Logic ===
  pH = 14.0 - (4.0 * voltagePH);
  pH = constrain(pH, 0.0, 14.0);

  // === Turbidity % Logic ===
  turbidityPercent = map(rawTurb, turbMin, turbMax, 0, 100);
  turbidityPercent = constrain(turbidityPercent, 0.0, 100.0);

  // === Debug ===
  Serial.println("----------- SENSOR READINGS -----------");
  Serial.print("Temperature: "); Serial.println(temperature);
  Serial.print("pH: "); Serial.println(pH);
  Serial.print("Turbidity Voltage: "); Serial.println(voltageTurb, 3);
  Serial.print("Turbidity %: "); Serial.println(turbidityPercent);
  Serial.println("----------------------------------------");

  // === Send to Supabase ===
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("apikey", String(apiKey));
    http.addHeader("Authorization", "Bearer " + String(apiKey));
    http.addHeader("Content-Type", "application/json");

    String jsonPayload = "{";
    jsonPayload += "\"temperature\": " + String(temperature, 2) + ", ";
    jsonPayload += "\"ph\": " + String(pH, 2) + ", ";
    jsonPayload += "\"turbidity\": " + String(turbidityPercent, 2);
    jsonPayload += "}";

    int httpResponseCode = http.POST(jsonPayload);
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Server response: " + response);
    } else {
      Serial.println("Error sending data: " + String(httpResponseCode));
    }
    http.end();
  } else {
    Serial.println("WiFi not connected");
  }

  delay(5000);
}
