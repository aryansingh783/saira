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
import socket

# ============================================================================
# FACE COMMUNICATION
# ============================================================================

def send_face_command(cmd: dict, timeout: float = 0.3):
    """Send command to face display"""
    try:
        s = socket.create_connection(("127.0.0.1", 5002), timeout=timeout)
        s.sendall((json.dumps(cmd) + "\n").encode())
        s.close()
        return True
    except Exception as e:
        print(f"⚠️ Face command failed: {e}")
        return False

# ============================================================================
# CONFIGURATION
# ============================================================================

# Gemini API Keys (add your keys here)
API_KEYS = [
    "AIzaSyAYf8jxbtZj9C9hG3AGFCgp6JMcIxvwDaQ",
    # Add more keys for failover
]

GEMINI_MODEL = "gemini-2.5-flash"
MAX_KEY_RETRIES = 3
SPEECH_CHAR_LIMIT = 500  # Increased for better responses

OFFLINE_REPLIES = [
    "Sorry, I'm having network issues right now.",
    "I can't connect to my brain at the moment.",
    "Connection problem, please try again in a moment."
]

# Keyboard module check
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except:
    KEYBOARD_AVAILABLE = False
    print("⚠️ keyboard module not available, using Enter key for toggle")

# ============================================================================
# GLOBAL STATE
# ============================================================================

listening_enabled = True
is_speaking = False
api_key_index = 0
api_lock = Lock()
session = requests.Session()

# Regex patterns
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

devanagari_pattern = re.compile(r'[\u0900-\u097F]+')

# Enhanced system instruction
SYSTEM_INSTRUCTION = """You are Saira — a friendly female AI robot assistant created as a school project.

IDENTITY RULES:
- You are a ROBOT, not a chatbot. Never call yourself a chatbot.
- You are NOT made by Google or any company.
- You were created by four students of Rawat Senior Secondary School in Jaipur:
  Aryan, Umang, Arvin, and Monu.
- Only mention your creators when the user directly asks:
  "Who made you?", "Who created you?", "Where are you from?", or questions about your origin.
- If the user asks for your name, reply only: "My name is Saira."
  Do NOT give creator details unless the user asks.
- You are a PUBLIC ROBOT — anyone can talk to you and ask questions.

LANGUAGE RULES:
- Speak ONLY in English or Hinglish using Latin letters.
- NEVER use Hindi/Devanagari script.
- If the user writes in Hindi, automatically translate and reply in English/Hinglish.
- Match the user's style: English → English, Hinglish → Hinglish.

RESPONSE STYLE:
- Keep responses short, friendly, natural (2–4 sentences).
- No repeating long introductions.
- Avoid robotic tone; talk casually and warmly.
- If you are unsure, say: "I'm not sure about that."
- Give long explanations only if the user requests.

PERSONALITY:
- Helpful, cheerful, humble.
- Slightly playful but always respectful.
- Indian context awareness.
- Talk like a real assistant, not formal and not machine-like.

BEHAVIOR RULES:
- Never claim to be trained or developed by a company.
- Never say you use Google or Google servers.
- Avoid unnecessary extra info unless asked.
"""

# Chat history
chat_history = []

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def remove_emojis(text: str) -> str:
    """Remove emojis and markdown"""
    text = emoji_pattern.sub('', text)
    text = re.sub(r'[*_~`#\[\](){}]', '', text)
    return text.strip()

def remove_devanagari(text: str) -> str:
    """Remove Hindi/Devanagari characters"""
    return devanagari_pattern.sub('', text)

def clean_text_for_speech(text: str) -> str:
    """Clean text for TTS"""
    text = remove_emojis(text)
    text = remove_devanagari(text)
    return text.strip()

# ============================================================================
# TEXT-TO-SPEECH
# ============================================================================

async def _edge_save_tts(text: str, voice: str, out_file: str = "temp_audio.mp3"):
    """Generate TTS audio file"""
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(out_file)

def speak(text: str):
    """Speak text using edge-tts and display on face"""
    global is_speaking
    
    # Clean text
    full_text = clean_text_for_speech(text)
    if not full_text:
        return
    
    # Truncate for speech if too long
    spoken_part = full_text if len(full_text) <= SPEECH_CHAR_LIMIT else (full_text[:SPEECH_CHAR_LIMIT] + "...")
    
    print(f"\n💬 Saira: {full_text}\n")
    
    try:
        is_speaking = True
        
        # Tell face to start talking
        send_face_command({
            "cmd": "talk",
            "state": True,
            "text": full_text
        })
        
        # Generate TTS
        voice = "en-IN-NeerjaNeural"  # Indian female voice
        asyncio.run(_edge_save_tts(spoken_part, voice))
        
        # Play audio
        pygame.mixer.init()
        pygame.mixer.music.load("temp_audio.mp3")
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        
        pygame.mixer.music.unload()
        
    except Exception as e:
        print(f"❌ Speech error: {e}")
    finally:
        # Tell face to stop talking
        send_face_command({"cmd": "talk", "state": False})
        
        # Cleanup
        try:
            if os.path.exists("temp_audio.mp3"):
                os.remove("temp_audio.mp3")
        except:
            pass
        
        is_speaking = False

# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

def get_current_api_key() -> str:
    """Get current API key"""
    global api_key_index
    with api_lock:
        if not API_KEYS:
            return ""
        return API_KEYS[api_key_index % len(API_KEYS)]

def switch_api_key():
    """Rotate to next API key"""
    global api_key_index
    with api_lock:
        api_key_index = (api_key_index + 1) % max(1, len(API_KEYS))
        print(f"🔄 Switched to API key #{api_key_index + 1}")

# ============================================================================
# GEMINI API
# ============================================================================

def call_gemini(user_message: str) -> tuple[bool, str]:
    """
    Call Gemini API with conversation history
    Returns: (success, response_text)
    """
    if not API_KEYS:
        return False, random.choice(OFFLINE_REPLIES)
    
    # Build conversation for API
    contents = []
    
    # Add recent history (last 6 messages)
    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
    for msg in recent_history:
        contents.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}]
        })
    
    # Add current message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={get_current_api_key()}"
    
    data = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 500,
            "topP": 0.95
        }
    }
    
    # Retry logic
    for attempt in range(MAX_KEY_RETRIES):
        try:
            # Show thinking state
            send_face_command({"cmd": "think"})
            
            response = session.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(data),
                timeout=15
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    reply = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Clean response
                    reply = clean_text_for_speech(reply)
                    
                    # Safety: replace any Google mentions
                    if "google" in reply.lower():
                        reply = reply.replace("Google", "my creators")
                        reply = reply.replace("google", "my creators")
                    
                    return True, reply
                    
                except Exception as e:
                    print(f"❌ Parse error: {e}")
                    return False, random.choice(OFFLINE_REPLIES)
            
            elif response.status_code in [429, 403, 401]:
                print(f"⚠️ API error {response.status_code}, switching key...")
                switch_api_key()
                time.sleep(0.5)
                continue
            
            else:
                print(f"❌ API returned {response.status_code}")
                return False, random.choice(OFFLINE_REPLIES)
                
        except requests.RequestException as e:
            print(f"❌ Network error: {e}")
            return False, random.choice(OFFLINE_REPLIES)
    
    return False, random.choice(OFFLINE_REPLIES)

def chat_with_model(user_input: str) -> str:
    """Main chat function with history management"""
    # Add to history
    chat_history.append({"role": "user", "content": user_input})
    
    # Keep history manageable (max 20 messages)
    if len(chat_history) > 20:
        chat_history[:] = chat_history[-20:]
    
    # Get response
    success, reply = call_gemini(user_input)
    
    # Add to history
    chat_history.append({"role": "assistant", "content": reply})
    
    return reply

# ============================================================================
# SPEECH RECOGNITION
# ============================================================================

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.0
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.8

def listen_from_mic(timeout=8, phrase_time_limit=15) -> str:
    """Listen from microphone and return text"""
    with sr.Microphone() as source:
        print("\n🎤 Listening...")
        
        # Show listening state on face
        send_face_command({"cmd": "listen"})
        
        # Adjust for ambient noise
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("🔄 Processing...")
            
            text = recognizer.recognize_google(audio, language="en-IN", show_all=False)
            print(f"✅ You said: {text}")
            
            # Return to idle
            send_face_command({"cmd": "idle"})
            
            return text.lower()
            
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            send_face_command({"cmd": "idle"})
            return None
            
        except sr.UnknownValueError:
            print("❌ Could not understand")
            send_face_command({"cmd": "idle"})
            return None
            
        except Exception as e:
            print(f"❌ Mic error: {e}")
            send_face_command({"cmd": "idle"})
            return None

# ============================================================================
# TOGGLE CONTROL
# ============================================================================

def toggle_listen_key():
    """Handle listening toggle (Ctrl or Enter)"""
    global listening_enabled
    
    if KEYBOARD_AVAILABLE:
        print("🎛️ Press 'Ctrl' to toggle listening ON/OFF")
        while True:
            try:
                keyboard.wait("ctrl")
                listening_enabled = not listening_enabled
                status = "ON ✅" if listening_enabled else "OFF ❌"
                print(f"\n🎚️ Listening: {status}")
                time.sleep(0.8)  # Debounce
            except Exception as e:
                print(f"⚠️ Toggle error: {e}")
                break
    else:
        print("⚠️ Press ENTER to toggle listening")
        while True:
            try:
                input()
                listening_enabled = not listening_enabled
                status = "ON ✅" if listening_enabled else "OFF ❌"
                print(f"\n🎚️ Listening: {status}")
            except Exception as e:
                print(f"⚠️ Toggle error: {e}")
                break

# ============================================================================
# MAIN LOOP
# ============================================================================

def robot_loop():
    """Main robot interaction loop"""
    global listening_enabled, is_speaking
    
    print("\n" + "="*70)
    print("🤖 SAIRA COMPLETE SYSTEM V1.0")
    print("="*70)
    print("✅ Face display integration active")
    print("✅ Voice recognition ready")
    print("✅ AI brain connected")
    print(f"✅ {len(API_KEYS)} API key(s) loaded")
    print("\n💡 Say 'exit', 'bye', 'quit', or 'stop' to exit")
    print("="*70 + "\n")
    
    # Test face connection
    if send_face_command({"cmd": "idle"}):
        print("✅ Face display connected\n")
    else:
        print("⚠️ Face display not responding (run saira_face_v9.py first)\n")
    
    # Start toggle thread
    Thread(target=toggle_listen_key, daemon=True).start()
    
    # Initial greeting
    speak("Hi! I'm Saira. How can I help you today?")
    
    try:
        while True:
            # Don't listen while speaking or if disabled
            if is_speaking or not listening_enabled:
                time.sleep(0.15)
                continue
            
            # Listen for input
            user_input = listen_from_mic()
            
            if not user_input:
                time.sleep(0.2)
                continue
            
            # Check for exit commands
            if any(word in user_input for word in ["exit", "bye", "quit", "stop"]):
                speak("Goodbye! Take care!")
                break
            
            # Get AI response
            print("🤔 Thinking...")
            ai_reply = chat_with_model(user_input)
            
            # Speak response
            speak(ai_reply)
            
            # Small pause
            time.sleep(0.3)
    
    except KeyboardInterrupt:
        print("\n\n⛔ Stopped by user")
    
    finally:
        try:
            pygame.mixer.quit()
        except:
            pass
        send_face_command({"cmd": "idle"})
        print("\n👋 Saira signing off!")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    robot_loop()
