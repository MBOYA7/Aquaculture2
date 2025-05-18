/*
  Fish Cage Monitoring System - ESP32
  — WiFi, PIR alarm, WQ + PIR → Supabase
  — Debug prints for raw readings & full HTTP responses
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ————— Configuration —————
const char* ssid       = "pilip";
const char* password   = "123456789";

const char* sensorURL   = "https://nfsrxbievdfztwelbbwg.supabase.co/rest/v1/lakefishcage";
const char* securityURL = "https://nfsrxbievdfztwelbbwg.supabase.co/rest/v1/security_alerts";
const char* apiKey      = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5mc3J4YmlldmRmenR3ZWxiYndnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ5NTg4MzIsImV4cCI6MjA2MDUzNDgzMn0.SG7HJPCDOa2N3bV57_wFLapCFUA8Bt4ZfVDScB0RT8s";

#define ONE_WIRE_BUS    4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature dallas(&oneWire);

const int phPin        = 35;
const int turbidityPin = 32;
const int pirPin       = 27;
const int ledPin       = 26;
const int buzzerPin    = 25;

const unsigned long SENSOR_POST_INTERVAL = 5000;   // 5 s for testing!
const unsigned long PIR_POST_INTERVAL    = 5000;   // 5 s
const unsigned long ALARM_DURATION       = 100000;  
const unsigned long BLINK_INTERVAL       = 200;    // 200 ms
const unsigned long PIR_STABILIZE_TIME   = 30000;  // 30 s

const int TURB_MIN = 1800;
const int TURB_MAX = 0;

// ————— Globals —————
unsigned long lastSensorPost = 0;
unsigned long lastPIRPost    = 0;
unsigned long pirPowerUpTime = 0;
unsigned long alarmStart     = 0;

bool alarmActive     = false;
int  lastPIRState    = LOW;

// ————— Helpers —————
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("⟳ WiFi…");
  WiFi.begin(ssid, password);
  unsigned long t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 15000) {
    Serial.print('.');
    delay(500);
  }
  if (WiFi.status() == WL_CONNECTED)
    Serial.println("\n✅ " + WiFi.localIP().toString());
  else
    Serial.println("\n❌ WiFi FAILED");
}

bool postData(const char* url, const String& payload) {
  WiFiClientSecure client;
  client.setInsecure();  // for testing only

  HTTPClient http;
  http.begin(client, url);
  http.addHeader("apikey", apiKey);
  http.addHeader("Authorization", "Bearer " + String(apiKey));
  http.addHeader("Content-Type",  "application/json");
  // remove return=minimal so we get the inserted row back:
  http.addHeader("Prefer",        "return=representation");

  int status = http.POST(payload);
  String resp = http.getString();
  Serial.printf("→ HTTP %s = %d\n", url, status);
  Serial.println("  └─ Response: " + resp);
  http.end();

  return (status >= 200 && status < 300);
}

// ————— Sensor routines —————
void readAndPostSensors() {
  // 1) Temperature
  dallas.requestTemperatures();
  float tempC = dallas.getTempCByIndex(0);

  // 2) pH
  int rawPH = analogRead(phPin);
  float pH = constrain(14.0 - (rawPH * (3.3 / 4095.0) * 4.0), 0.0, 14.0);

  // 3) Turbidity
  int rawT = analogRead(turbidityPin);
  float turb = constrain(map(rawT, TURB_MIN, TURB_MAX, 0, 100), 0, 100);

  // --- DEBUG: raw readings
  Serial.printf("🔬 Raw → pH: %d, Turb: %d\n", rawPH, rawT);

  // Build JSON
  String js = String("{") +
    "\"temperature\":" + String(tempC,2) + "," +
    "\"ph\":"          + String(pH,2)     + "," +
    "\"turbidity\":"   + String(turb,1)   +
  "}";

  // POST
  if (postData(sensorURL, js))
    Serial.println("✅ WQ posted: " + js);
  else
    Serial.println("❌ WQ post failed");
}

// ————— PIR & alarm —————
void triggerAlarm() {
  alarmActive = true;
  alarmStart  = millis();
  Serial.println("🔔 ALARM!");
}
void handleAlarm() {
  if (!alarmActive) return;
  bool on = (millis() % (BLINK_INTERVAL*2) < BLINK_INTERVAL);
  digitalWrite(ledPin,    on);
  digitalWrite(buzzerPin, on);
  if (millis() - alarmStart > ALARM_DURATION) {
    alarmActive = false;
    digitalWrite(ledPin, LOW);
    digitalWrite(buzzerPin, LOW);
    Serial.println("🔕 Alarm ended");
  }
}
void checkPIR() {
  int cur = digitalRead(pirPin);
  if (millis() - pirPowerUpTime < PIR_STABILIZE_TIME) {
    lastPIRState = cur;
    return;
  }
  if (cur == HIGH && lastPIRState == LOW) triggerAlarm();
  lastPIRState = cur;

  if (millis() - lastPIRPost >= PIR_POST_INTERVAL) {
    String js = String("{\"status\":") + String(cur) + "}";
    if (postData(securityURL, js))
      Serial.println("✅ PIR posted: " + js);
    else
      Serial.println("❌ PIR post failed");
    lastPIRPost = millis();
  }
}

// ————— Setup & loop —————
void setup() {
  Serial.begin(115200);
  pinMode(ledPin,    OUTPUT);
  pinMode(buzzerPin, OUTPUT);
  pinMode(pirPin,    INPUT_PULLDOWN);
  dallas.begin();

  // PIR warm-up
  pirPowerUpTime = millis();
  Serial.println("⏱ PIR warming up…");
  while (millis() - pirPowerUpTime < PIR_STABILIZE_TIME) {
    delay(50);
  }
  Serial.println("✅ PIR ready");

  connectWiFi();
  Serial.println("🚀 System ready");

  // force immediate posts
  lastSensorPost = millis() - SENSOR_POST_INTERVAL;
  lastPIRPost    = millis() - PIR_POST_INTERVAL;
}

void loop() {
  connectWiFi();
  handleAlarm();
  checkPIR();

  if (millis() - lastSensorPost >= SENSOR_POST_INTERVAL) {
    readAndPostSensors();
    lastSensorPost = millis();
  }

  delay(50);
}