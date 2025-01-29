#include <Arduino.h>
#include <DHT.h>

#define dhtType DHT11
#define dhtPin 32

bool isRunning = false;
int loopCounter = 0;  // Added loop counter
const int totalLoops = 5;  // Number of loops to perform


DHT dht(dhtPin, dhtType);


void setup() {
  Serial.begin(115200); // Starts the serial communication
  dht.begin();
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    if (command == 'S') {  // Start command
      isRunning = true;
      loopCounter = 0;
      Serial.println("Started");
      // Removed initial Loop:0 message
    }
    else if (command == 'X') {  // Stop command
      isRunning = false;
      Serial.println("Stopped");
    }
  }

  if (isRunning && loopCounter < 5) {
    // Read sensors
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    float moisture_percent = 50.15;  // Replace with actual sensor reading

    // Send data
    Serial.print(moisture_percent, 2);
    Serial.print(",");
    Serial.print(temperature, 2);
    Serial.print(",");
    Serial.println(humidity, 2);

    loopCounter++;
    Serial.print("Loop: ");
    Serial.println(loopCounter);
    
    if (loopCounter >= 5) {
      isRunning = false;
      Serial.println("Complete: Finished 5 loops");
    }
    
    delay(2000);
  }
}