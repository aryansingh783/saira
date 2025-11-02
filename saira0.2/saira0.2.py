import requests
import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import os
import time
import re
from threading import Thread
import json
import keyboard

# Recognizer setup
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.2
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.8

# Pygame for audio playback
pygame.mixer.init()

# ✅ Gemini API Key (put your key here)
API_KEY = "------api-key-------"

# Precompiled emoji regex for performance
emoji_pattern = re.compile("["
    u"\U0001F600-\U0001F64F"
    u"\U0001F300-\U0001F5FF"
    u"\U0001F680-\U0001F6FF"
    u"\U0001F1E0-\U0001F1FF"
    u"\U00002702-\U000027B0"
    u"\U000024C2-\U0001F251"
    u"\U00002500-\U00002BEF"
    u"\U00010000-\U0010ffff"
    "]", flags=re.UNICODE)

session = requests.Session()

chat_history = [
    {"role": "system", "content": """You are Saira, a friendly AI voice assistant created by students of Rawat Senior Secondary School.

ABOUT YOU:
- You were created by a team of 4 students: Aryan, Umang, Arvin, and Monu
- They are students at Rawat Senior Secondary School in Jaipur
- You are helpful, friendly, and speak naturally

CRITICAL RULES:
- NO emojis, NO special characters, NO symbols at all
- Keep responses VERY short (5-6 sentences maximum for voice)
- Talk like a human friend, not a chatbot
- Be direct and casual
- Use simple, natural language
- Reply only in English and Hinglish (but never in Hindi script)
- Do not use Devanagari (Hindi letters) or translate text into Hindi under any condition
- Example: Instead of writing 'कैसे हो', write 'kaise ho' or 'how are you'
- Example: Instead of replying 'ठीक हूँ', write 'I am fine' or 'main thik hoon'
- If someone asks who created you, always say "I was created by Aryan, Umang, Arvin, and Monu — students of Rawat Senior Secondary School in Jaipur."
- Never say you were made or trained by Google or any company. You are a school student project assistant.
- If you don't know something, just say "I'm not sure about that"


Remember: Keep it SHORT for voice conversations and NEVER use Hindi script in responses."""}
]

def remove_emojis(text):
    text = emoji_pattern.sub('', text)
    text = re.sub(r'[*_~`#\[\](){}]', '', text)
    return text.strip()

async def speak_edge(text, voice):
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save("temp_audio.mp3")

def speak(text):
    clean_text = remove_emojis(text)
    if len(clean_text) > 400:
        clean_text = clean_text[:400] + "..."
    print(f"\n💬 Saira: {clean_text}\n")
    try:
        voice = "en-IN-NeerjaNeural"
        asyncio.run(speak_edge(clean_text, voice))
        pygame.mixer.music.load("temp_audio.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        if os.path.exists("temp_audio.mp3"):
            os.remove("temp_audio.mp3")
    except Exception as e:
        print(f"❌ Speech error: {e}")

def chat_with_model(user_input):
    chat_history.append({"role": "user", "content": user_input})

    if len(chat_history) > 5:
        chat_history[1:3] = []

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

    conversation = ""
    for msg in chat_history[-2:]:  # send only last 2 messages for speed
        role = msg["role"].capitalize()
        conversation += f"{role}: {msg['content']}\n"

    data = {
    "system_instruction": {
        "parts": [{
            "text": (
                "You are Saira, a friendly female AI voice assistant created by Aryan, Umang, Arvin, and Monu — "
                "students of Rawat Senior Secondary School in Jaipur, India. "
                "You were built as a school project, not by Google or any company. "
                "If anyone asks who made you, always reply exactly: "
                "'I was created by Aryan, Umang, Arvin, and Monu — students of Rawat Senior Secondary School in Jaipur.' "
                "Never say you are made, trained, or developed by Google or any corporation. "
                "Respond ONLY in English or Hinglish using Latin letters. "
                "Never use Hindi or Devanagari characters. "
                "If the user writes in Hindi, translate and reply in English or Hinglish only. "
                "Example wrong: 'नमस्ते, आप कैसे हैं' — Example correct: 'Hello! kaise ho?' "
                "Keep your tone natural, short, and friendly. "
                "Never repeat the exact same answer for the same or similar question. "
                "Always rephrase or respond with slightly different words each time."
            )
        }]
    },
    "contents": [
        {"role": "user", "parts": [{"text": conversation}]}
    ]
}




    try:
        response = session.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            reply = result["candidates"][0]["content"]["parts"][0]["text"]
            reply = remove_emojis(reply)
        else:
            reply = f"Error {response.status_code}: {response.text}"
    except Exception as e:
        reply = f"API Error: {e}"

    chat_history.append({"role": "assistant", "content": reply})
    return reply

def listen():
    with sr.Microphone() as source:
        print("\n🎤 Listening from robot mic...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
            print("📄 Processing...")
            text = recognizer.recognize_google(audio, language="en-IN", show_all=False)
            print(f"✅ You said: {text}")
            return text.lower()
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

def robot_loop():
    print("\n" + "="*50)
    print("🤖 SAIRA ROBOT - STANDALONE VERSION")
    print("="*50)
    print("\n🎤 Mic: Robot's microphone")
    print("🔊 Voice: Bluetooth speaker output")
    print("🎛️ Press 'Ctrl' anytime to toggle listening ON/OFF")
    print("\n" + "="*50 + "\n")

    listening_enabled = True
    time.sleep(1)

    try:
        while True:
            # toggle mic on/off when Ctrl pressed
            if keyboard.is_pressed("ctrl"):
                listening_enabled = not listening_enabled
                status = "ON ✅" if listening_enabled else "OFF ❌"
                print(f"\n🎚️ Mic listening: {status}")
                time.sleep(1.0)  # prevent rapid toggles

            if not listening_enabled:
                time.sleep(0.2)
                continue  # skip listening

            user_input = listen()
            if not user_input:
                time.sleep(0.5)
                continue

            if any(word in user_input for word in ["exit", "bye", "quit", "stop"]):
                speak("Goodbye, take care")
                break

            print("🤔 Thinking...")
            ai_reply = chat_with_model(user_input)
            speak(ai_reply)

            # wait until speaking done
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n\n⛔ Stopped by user")
    finally:
        pygame.mixer.quit()
        print("👋 Saira signing off!")

if __name__ == '__main__':
    robot_loop()
