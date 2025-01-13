#include <Arduino.h>
#include <Stepper.h>
#include <DHT.h>

const int trigPin = 23;
const int echoPin = 22;

#define dhtType DHT11
#define dhtPin 32

#define IN1 18
#define IN2 5
#define IN3 17
#define IN4 16

const int stepsPerRevolution = 2048;

DHT dht(dhtPin, dhtType);

Stepper myStepper(stepsPerRevolution, IN1, IN3, IN2, IN4);

//define sound speed in cm/uS
#define SOUND_SPEED 0.034
#define CM_TO_INCH 0.393701

long duration;
float distanceCm;
float distanceInch;

void setup() {
  Serial.begin(9600); // Starts the serial communication
  dht.begin();
  pinMode(trigPin, OUTPUT); // Sets the trigPin as an Output
  pinMode(echoPin, INPUT); // Sets the echoPin as an Input
   // set the speed at 5 rpm
  myStepper.setSpeed(5);
}

void loop() {
  ////////////////////////////// dht11 /////////////////////
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  float moisture_percent = 50.15;
  
  // Send data in one line, comma-separated
  Serial.print(moisture_percent, 2);
  Serial.print(",");
  Serial.print(temperature, 2);
  Serial.print(",");
  Serial.println(humidity, 2);  // println for the last value to add newline
  
  delay(2000);  
  // Wait 2 seconds before next reading
  ////////////////////////////// ultra sonic sensor /////////////////////
  // Clears the trigPin
 /*  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 micro seconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  
  // Calculate the distance
  distanceCm = duration * SOUND_SPEED/2;
  
  // Convert to inches
  distanceInch = distanceCm * CM_TO_INCH;


  // Prints the distance in the Serial Monitor
  Serial.print("Distance (cm): ");
  Serial.println(distanceCm);
  Serial.print("Distance (inch): ");
  Serial.println(distanceInch);
  
  delay(1000);
////////////////////////////// stepper motor /////////////////////
  Serial.println("clockwise");
  myStepper.step(stepsPerRevolution);
  delay(1000);

  // step one revolution in the other direction:
  Serial.println("counterclockwise");
  myStepper.step(-stepsPerRevolution);
  delay(1000); */


}