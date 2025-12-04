import serial
import keyboard
import time

ser = serial.Serial("COM5", 115200)

while True:
    # default stop
    hand = 0
    head = 0

    # Hand
    if keyboard.is_pressed('w'):
        hand = 1
    elif keyboard.is_pressed('s'):
        hand = -1

    # Head
    if keyboard.is_pressed('a'):
        head = -1
    elif keyboard.is_pressed('d'):
        head = 1

    # Send commands
    if hand == 1:
        ser.write(b'w')
    elif hand == -1:
        ser.write(b's')

    if head == -1:
        ser.write(b'a')
    elif head == 1:
        ser.write(b'd')

    # small delay
    time.sleep(0.02)
