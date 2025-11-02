# voice_qa_saira.py
# Standalone voice Q&A using Saira's speak() and listen() functions from saira.py
# Requires: edge-tts, speechrecognition, pygame, PyAudio (for microphone)
# Files used: qa_blocks.txt, qa_meta.json

import os
import re
import time
import json
import asyncio
import difflib
import edge_tts
import speech_recognition as sr
import pygame

# ------------------ Audio / recognizer init (from saira.py) ------------------
# Recognizer setup (copied)
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.2
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.8

# Pygame for audio playback
try:
    pygame.mixer.init()
except Exception as e:
    print("Warning: pygame mixer init failed:", e)

# ------------------ Helper: sanitize text (remove emojis/special chars) -----
def remove_emojis(text):
    """Remove emojis and certain special characters (copied logic)."""
    emoji_pattern = re.compile("[" 
        u"\U0001F600-\U0001F64F" 
        u"\U0001F300-\U0001F5FF" 
        u"\U0001F680-\U0001F6FF" 
        u"\U0001F1E0-\U0001F1FF" 
        u"\U00002702-\U000027B0" 
        u"\U000024C2-\U0001F251" 
        u"\U00002500-\U00002BEF" 
        u"\U00010000-\U0010ffff"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    text = re.sub(r'[*_~`#\[\](){}]', '', text)
    return text.strip()

# ------------------ Edge TTS helper (async) ------------------
async def _speak_edge_save(text, voice):
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save("temp_audio.mp3")

def speak(text):
    """Convert text to speech and play using pygame (copied behavior)."""
    clean_text = remove_emojis(text)
    if len(clean_text) > 300:
        clean_text = clean_text[:300] + "."
    print(f"\n💬 Saira: {clean_text}\n")
    try:
        voice = "en-IN-NeerjaNeural"  # same voice as in saira.py
        asyncio.run(_speak_edge_save(clean_text, voice))
        # play
        pygame.mixer.music.load("temp_audio.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        time.sleep(0.1)
        if os.path.exists("temp_audio.mp3"):
            try:
                os.remove("temp_audio.mp3")
            except:
                pass
    except Exception as e:
        print(f"❌ Speech error: {e}")

def listen(timeout=8, phrase_time_limit=15):
    """Listen from mic and return recognized text (lowercased) or None.
       This function mirrors the flow from saira.py but without socketio emits."""
    with sr.Microphone() as source:
        print("\n🎤 Listening from microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("📄 Processing.")
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

# ------------------ QA data loading/saving ------------------
QA_FILE = "qa_blocks.txt"
META_FILE = "qa_meta.json"
MIN_MATCH_PERCENT = 50.0  # accept only if similarity >= this

def load_blocks(path=QA_FILE):
    """Load blocks from qa_blocks.txt using the ---BLOCK--- format."""
    if not os.path.exists(path):
        return []
    text = open(path, "r", encoding="utf-8").read()
    parts = text.split('---BLOCK---')
    blocks = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lines = [l.rstrip() for l in p.splitlines() if l.strip()]
        block = {"id": None, "q": "", "answers": []}
        for ln in lines:
            if ln.lower().startswith("id:"):
                block["id"] = ln.split(":", 1)[1].strip()
            elif ln.lower().startswith("q:"):
                block["q"] = ln.split(":", 1)[1].strip()
            elif re.match(r'^a\d\s*:', ln, flags=re.I):
                block["answers"].append(ln.split(":", 1)[1].strip())
            else:
                # fallback
                if not block["q"]:
                    block["q"] = ln
                else:
                    block["answers"].append(ln)
        while len(block["answers"]) < 5:
            block["answers"].append("I'm not sure about that.")
        blocks.append(block)
    return blocks

def load_meta(path=META_FILE):
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path, "r", encoding="utf-8"))
    except:
        return {}

def save_meta(meta, path=META_FILE):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Could not save meta:", e)

# ------------------ Matching logic ------------------
def similarity_percent(a, b):
    a = re.sub(r'\W+', ' ', a.lower()).strip()
    b = re.sub(r'\W+', ' ', b.lower()).strip()
    if not a or not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return round(ratio * 100, 2)

def find_best_block(user_text, blocks):
    best = None
    best_score = 0.0
    for block in blocks:
        score = similarity_percent(user_text, block["q"])
        if score > best_score:
            best_score = score
            best = block
    return best, best_score

# ------------------ Respond logic with rotation ------------------
def respond_to_user(user_text, blocks, meta):
    block, score = find_best_block(user_text, blocks)
    if not block or score < MIN_MATCH_PERCENT:
        reply = "I'm not sure about that."
        speak(reply)
        return
    bid = str(block.get("id") or block["q"])
    last_idx = meta.get(bid, -1)
    next_idx = (last_idx + 1) % len(block["answers"])
    reply = block["answers"][next_idx]
    meta[bid] = next_idx
    save_meta(meta)
    print(f"[Matched block id={bid} score={score}% answer_index={next_idx}]")
    speak(reply)

# ------------------ Main loop ------------------
def main_loop():
    print("Loading QA blocks...")
    blocks = load_blocks()
    if not blocks:
        print("No blocks found. Create qa_blocks.txt using the editor or manually. Exiting.")
        return
    meta = load_meta()
    print("Ready. Say 'exit' or 'bye' to stop.")
    while True:
        user_text = listen()
        if not user_text:
            time.sleep(0.2)
            continue
        print("You said:", user_text)
        if any(w in user_text for w in ["exit", "bye", "quit", "stop"]):
            speak("Goodbye, take care")
            break
        respond_to_user(user_text, blocks, meta)
        time.sleep(0.2)

if __name__ == "__main__":
    main_loop()
