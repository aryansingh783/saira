#include <Servo.h>

Servo handServo;
Servo headServo;

float handAngle = 90;
float headAngle = 90;

int handSpeed = 0;
int headSpeed = 0;

void setup() {
  Serial.begin(115200);

  handServo.attach(9);
  headServo.attach(10);

  handServo.write(handAngle);
  headServo.write(headAngle);
}

void loop() {

  // Check serial commands
  if (Serial.available()) {
    char c = Serial.read();

    // Hand
    if (c == 'w') handSpeed = +1;    // up
    if (c == 's') handSpeed = -1;    // down

    // Head
    if (c == 'a') headSpeed = -1;    // left
    if (c == 'd') headSpeed = +1;    // right

    // Reset
    if (c == 'r') {
      handAngle = 90;
      headAngle = 90;
    }
  }

  // Update angles
  handAngle += handSpeed * 0.5;
  headAngle += headSpeed * 0.5;

  // Limit
  handAngle = constrain(handAngle, 0, 180);
  headAngle = constrain(headAngle, 0, 180);

  // Output
  handServo.write(handAngle);
  headServo.write(headAngle);

  // slow speed
  delay(10);
}
