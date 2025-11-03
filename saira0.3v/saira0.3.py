
import requests
import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import os
import time
import re
import json
import random
from threading import Thread, Lock
import requests

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except Exception:
    KEYBOARD_AVAILABLE = False

# ---------------------- CONFIG ----------------------
API_KEYS = ["=====API-KEY-HERE======="]

# Choose Gemini model (1.5-flash is faster; 2.5-flash more capable)
GEMINI_MODEL = "gemini-2.5-flash"

# How many retries before giving up on a request (and switching key)
MAX_KEY_RETRIES = 3

# Spoken character limit (voice will speak only this many characters)
SPEECH_CHAR_LIMIT = 400

# Offline fallback replies (when API/network fails)
OFFLINE_REPLIES = [
    "Sorry, network issue. Please try again in a moment.",
    "I'm offline right now. Can you repeat later?",
    "Connection problem, I can't answer right now."
]

# ----------------------------------------------------

# Initialize pygame mixer for audio playback
pygame.mixer.init()

# Global runtime flags
listening_enabled = True   # toggled by Ctrl (or fallback)
is_speaking = False        # True while TTS playing
api_key_index = 0
api_lock = Lock()          # to protect api_key_index during switching

session = requests.Session()

# Precompile regex patterns
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

# Devanagari range (Hindi script) U+0900–U+097F
devanagari_pattern = re.compile(r'[\u0900-\u097F]+')

# Chat memory and system instruction (strict)
chat_history = [
    {"role": "system", "content": (
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
        "Always rephrase or respond with slightly different words each time. "
        "If you don't know something, just say: I'm not sure about that. "
        "If a question is written in English, reply only in English. "
        "If a question is written in Hinglish (Roman Hindi), reply in Hinglish. "
        "Never mix both styles in one answer. Detect user language automatically and match it."
    )}
]


# Helper functions -----------------------------------------------------------
def remove_emojis(text: str) -> str:
    text = emoji_pattern.sub('', text)
    text = re.sub(r'[*_~`#\[\](){}]', '', text)
    return text.strip()

def remove_devanagari(text: str) -> str:
    """Strip any Devanagari/Hindi script characters as a safety net."""
    return devanagari_pattern.sub('', text)

async def _edge_save_tts(text: str, voice: str, out_file: str = "temp_audio.mp3"):
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(out_file)

def speak(text: str):
    """
    Speak using edge-tts and pygame. This function blocks until audio finished,
    but sets global is_speaking so listening can be disabled while speaking.
    """
    global is_speaking
    clean_text = remove_emojis(text)
    clean_text = remove_devanagari(clean_text)  # remove any stray Hindi script
    full_text = clean_text.strip()

    # Limit spoken portion for brevity, but keep full_text for logs
    spoken_part = full_text if len(full_text) <= SPEECH_CHAR_LIMIT else (full_text[:SPEECH_CHAR_LIMIT] + "...")

    print("\n💬 Saira (text):", full_text, "\n")
    print("🔊 Speaking:", spoken_part, "\n")

    try:
        is_speaking = True
        # Generate TTS audio
        voice = "en-IN-NeerjaNeural"
        asyncio.run(_edge_save_tts(spoken_part, voice, out_file="temp_audio.mp3"))
        # Play it (blocking until finished)
        pygame.mixer.music.load("temp_audio.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
    except Exception as e:
        print("❌ Speech error:", e)
    finally:
        # Remove file if exists
        try:
            if os.path.exists("temp_audio.mp3"):
                os.remove("temp_audio.mp3")
        except Exception:
            pass
        is_speaking = False

def get_current_api_key() -> str:
    global api_key_index
    with api_lock:
        if not API_KEYS:
            return ""
        return API_KEYS[api_key_index % len(API_KEYS)]

def switch_api_key():
    """Rotate to next API key (used on rate limit or quota error)."""
    global api_key_index
    with api_lock:
        api_key_index = (api_key_index + 1) % max(1, len(API_KEYS))
        print(f"🔁 Switched API key -> index {api_key_index}")

def call_gemini(conversation: str) -> (bool, str):
    """
    Call Gemini generateContent endpoint with system_instruction and conversation.
    Returns (success, reply_text). On failure returns (False, fallback_message).
    """
    if not API_KEYS:
        return False, random.choice(OFFLINE_REPLIES)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={get_current_api_key()}"
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
                    "Keep your tone natural, short, and friendly. "
                    "Never repeat the exact same answer for the same or similar question. "
                    "Always rephrase or respond with slightly different words each time. "
                    "If you don't know something, just say: I'm not sure about that. "
                    "If a question is written in English, reply only in English. "
                    "If a question is written in Hinglish (Roman Hindi), reply in Hinglish. "
                    "Never mix both styles in one answer. Detect user language automatically and match it."
                )
            }]
        },
        "contents": [
            {"role": "user", "parts": [{"text": conversation}]}
        ]
    }

    try_count = 0
    while try_count < MAX_KEY_RETRIES:
        try_count += 1
        try:
            resp = session.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(data), timeout=15)
        except requests.RequestException as e:
            print("❌ Network/API request failed:", e)
            return False, random.choice(OFFLINE_REPLIES)

        if resp.status_code == 200:
            try:
                result = resp.json()
                # Safe extraction with fallback
                reply = ""
                try:
                    reply = result["candidates"][0]["content"]["parts"][0]["text"]
                except Exception:
                    # Try alternate paths
                    reply = json.dumps(result)[:800]
                # Safety filters
                reply = remove_emojis(reply)
                reply = remove_devanagari(reply)
                # Force identity override as final safety
                if "google" in reply.lower():
                    reply = reply.replace("google", "Aryan, Umang, Arvin, and Monu")
                return True, reply.strip()
            except Exception as e:
                print("❌ Error parsing response:", e)
                return False, random.choice(OFFLINE_REPLIES)
        else:
            print(f"⚠️ Gemini API returned {resp.status_code}: {resp.text[:200]}")
            # If rate limit or quota issue, switch key and retry
            if resp.status_code in (429, 403, 401):
                print("⚠️ Rate limit / auth issue — switching key and retrying...")
                switch_api_key()
                time.sleep(0.5)
                continue
            else:
                return False, random.choice(OFFLINE_REPLIES)

    # If all retries failed
    return False, random.choice(OFFLINE_REPLIES)

def chat_with_model(user_input: str) -> str:
    # Append to history (keep short)
    chat_history.append({"role": "user", "content": user_input})
    if len(chat_history) > 6:
        # keep last system + 4 messages for context
        chat_history[1:-3] = []

    # Build conversation string from last 2 messages (fast)
    conversation = ""
    for msg in chat_history[-2:]:
        role = msg["role"].capitalize()
        conversation += f"{role}: {msg['content']}\n"

    success, reply = call_gemini(conversation)
    if not success:
        # use offline fallback
        reply = random.choice(OFFLINE_REPLIES)

    # Store assistant reply in history
    chat_history.append({"role": "assistant", "content": reply})
    return reply

# Microphone listening ------------------------------------------------------
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.2
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.8

def listen_from_mic(timeout=8, phrase_time_limit=12):
    """Listen once from system microphone and return lowercase text or None."""
    with sr.Microphone() as source:
        print("\n🎤 Listening from robot mic... (speak now)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("📄 Processing...")
            text = recognizer.recognize_google(audio, language="en-IN", show_all=False)
            print("✅ You said:", text)
            return text.lower()
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand")
            return None
        except Exception as e:
            print("❌ Microphone error:", e)
            return None

# Toggle handling (Ctrl or fallback) ---------------------------------------
def toggle_listen_key():
    """Background thread: wait for Ctrl press (if keyboard available), else wait for Enter to toggle."""
    global listening_enabled
    if KEYBOARD_AVAILABLE:
        print("🎛️ Press 'Ctrl' to toggle listening ON/OFF (keyboard module detected)")
        while True:
            try:
                keyboard.wait("ctrl")
                listening_enabled = not listening_enabled
                status = "ON ✅" if listening_enabled else "OFF ❌"
                print(f"\n🎚️ Mic listening: {status}")
                time.sleep(0.8)  # debounce
            except Exception as e:
                print("⚠️ Keyboard listener error:", e)
                break
    else:
        print("⚠️ keyboard module not available. Press ENTER to toggle listening (console fallback).")
        while True:
            try:
                input()  # waits for Enter
                listening_enabled = not listening_enabled
                status = "ON ✅" if listening_enabled else "OFF ❌"
                print(f"\n🎚️ Mic listening: {status}")
            except Exception as e:
                print("⚠️ Fallback toggle error:", e)
                break

# Robot main loop ----------------------------------------------------------
def robot_loop():
    global listening_enabled, is_speaking

    print("\n" + "="*60)
    print("🤖 SAIRA ROBOT - EXHIBITION READY (Standalone)")
    print("="*60)
    print("\n🎤 Mic: Robot's microphone")
    print("🔊 Voice: Bluetooth speaker output (edge-tts + pygame)")
    print("🔁 Multi-key failover enabled" if len(API_KEYS) > 1 else "🔁 Single API key mode")
    print("\n" + "="*60 + "\n")

    # Start toggle thread
    Thread(target=toggle_listen_key, daemon=True).start()

    try:
        while True:
            # Do not listen while speaking (ensures TTS doesn't retrigger mic)
            if is_speaking or not listening_enabled:
                time.sleep(0.15)
                continue

            user_input = listen_from_mic()

            if not user_input:
                time.sleep(0.2)
                continue

            # exit keywords
            if any(word in user_input for word in ["exit", "bye", "quit", "stop"]):
                speak("Goodbye, take care")
                break

            # Generate reply (non-blocking voice generation will block while TTS running)
            print("🤔 Thinking...")
            ai_reply = chat_with_model(user_input)

            # Speak (this sets is_speaking True during playback)
            speak(ai_reply)

            # Small pause before next listen cycle
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\n⛔ Stopped by user")
    finally:
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        print("👋 Saira signing off!")

if __name__ == '__main__':
    robot_loop()
