/*
  Project: Techathon 2026 - Ctrl+Alt+Defeat
  Module: ESP32 Hardware Relay Simulation
  Description: Simulates the physical switching of devices DEV-001 through
  DEV-015. Listens for HTTP POST/GET requests to toggle GPIO pins (relays).
*/

#include <Arduino.h>
#include <WebServer.h>
#include <WiFi.h>

// --- Forward Declarations ---
void handleToggle();

// --- Network Configuration ---
const char *ssid = "YOUR_WIFI_SSID";
const char *password = "YOUR_WIFI_PASSWORD";

WebServer server(80);

// --- Hardware Mapping ---
// Simulating 15 devices across the Drawing Room, Work Room 1, and Work Room 2
const int NUM_DEVICES = 15;

// GPIO Pins assigned to relays
int relayPins[NUM_DEVICES] = {2,  4,  5,  12, 13, 14, 15, 18,
                              19, 21, 22, 23, 25, 26, 27};

// Device ID mapping matching the Python Backend
String deviceIDs[NUM_DEVICES] = {"DEV-001", "DEV-002", "DEV-003", "DEV-004",
                                 "DEV-005", "DEV-006", "DEV-007", "DEV-008",
                                 "DEV-009", "DEV-010", "DEV-011", "DEV-012",
                                 "DEV-013", "DEV-014", "DEV-015"};

void setup() {
  Serial.begin(115200);
  Serial.println(
      "\n[INIT] Booting Ctrl+Alt+Defeat ESP32 Hardware Simulator...");

  // Initialize all relay pins to OUTPUT and default to OFF (LOW)
  for (int i = 0; i < NUM_DEVICES; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW);
  }
  Serial.println("[SYSTEM] All physical relays initialized to OFF state.");

  // Establish WiFi Connection
  WiFi.begin(ssid, password);
  Serial.print("[NETWORK] Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[NETWORK] Connected Successfully.");
  Serial.print("[NETWORK] ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  // Mount API Endpoints
  server.on("/toggle", handleToggle);
  server.begin();
  Serial.println("[SYSTEM] Hardware Simulation Server Active and Listening.");
}

void loop() {
  // Listen for incoming HTTP requests from the FastAPI backend
  server.handleClient();
}

// --- Relay Control Logic ---
void handleToggle() {
  // Check if the incoming request has the correct parameters
  if (server.hasArg("device") && server.hasArg("state")) {
    String dev = server.arg("device");
    String state = server.arg("state");

    // Normalize state to boolean
    bool turnOn =
        (state == "ON" || state == "on" || state == "1" || state == "true");

    bool found = false;
    for (int i = 0; i < NUM_DEVICES; i++) {
      if (deviceIDs[i] == dev) {
        found = true;

        // Trigger the physical GPIO pin
        digitalWrite(relayPins[i], turnOn ? HIGH : LOW);

        // Log the physical action to the Serial Monitor
        Serial.print("[HARDWARE_EXECUTION] ");
        Serial.print(dev);
        Serial.print(" Relay switched ");
        Serial.println(turnOn ? "ON (HIGH)" : "OFF (LOW)");

        server.send(200, "text/plain", "Hardware relay toggled successfully");
        break;
      }
    }

    if (!found) {
      Serial.println("[ERROR] Unrecognized Device ID received.");
      server.send(404, "text/plain", "Device ID not found in hardware map");
    }
  } else {
    Serial.println("[ERROR] Malformed request received.");
    server.send(400, "text/plain", "Missing 'device' or 'state' parameters");
  }
}