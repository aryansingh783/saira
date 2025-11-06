import serial, time
from pynput import keyboard

# Change COM port according to Arduino
arduino = serial.Serial('COM3', 9600)
time.sleep(2)
print("Connected to Robot! Use W/S, E/D, J/L, I/K to control. ESC to quit.")

def on_press(key):
    try:
        if key.char in ['w', 's', 'e', 'd', 'j', 'l', 'i', 'k']:
            arduino.write(key.char.encode())
            print(f"Sent: {key.char}")
    except AttributeError:
        pass

def on_release(key):
    if key == keyboard.Key.esc:
        print("Exiting...")
        arduino.close()
        return False

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
