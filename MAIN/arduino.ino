#include <Servo.h>

Servo leftHand, rightHand, headPan, headTilt;
int angleLeft = 90;
int angleRight = 90;
int anglePan = 90;
int angleTilt = 90;

void setup() {
  leftHand.attach(3);
  rightHand.attach(5);
  headPan.attach(6);
  headTilt.attach(9);

  Serial.begin(9600);
  Serial.println("Robot Ready: W/S Left Hand | E/D Right Hand | J/L Head Pan | I/K Head Tilt");
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();

    switch (c) {
      // Left Hand
      case 'w': angleLeft += 10; break;
      case 's': angleLeft -= 10; break;

      // Right Hand
      case 'e': angleRight += 10; break;
      case 'd': angleRight -= 10; break;

      // Head Pan
      case 'l': anglePan += 10; break;
      case 'j': anglePan -= 10; break;

      // Head Tilt
      case 'i': angleTilt += 10; break;
      case 'k': angleTilt -= 10; break;
    }

    // Limit all to 0–180
    angleLeft = constrain(angleLeft, 0, 180);
    angleRight = constrain(angleRight, 0, 180);
    anglePan = constrain(anglePan, 0, 180);
    angleTilt = constrain(angleTilt, 0, 180);

    // Update servo positions
    leftHand.write(angleLeft);
    rightHand.write(angleRight);
    headPan.write(anglePan);
    headTilt.write(angleTilt);

    // Print angles for debug
    Serial.print("Left: "); Serial.print(angleLeft);
    Serial.print(" | Right: "); Serial.print(angleRight);
    Serial.print(" | Pan: "); Serial.print(anglePan);
    Serial.print(" | Tilt: "); Serial.println(angleTilt);
  }
}
