from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import ollama
import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import os
import time
import re
from threading import Thread

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Recognizer setup
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.2
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.8

# Pygame for audio playback (Bluetooth speaker)
pygame.mixer.init()

# Chat memory
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
- Reply only in English
- If you don't know something, just say "I'm not sure about that"

Remember: Keep it SHORT for voice conversations."""}
]

def remove_emojis(text):
    """Remove all emojis and special characters"""
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

async def speak_edge(text, voice):
    """Microsoft Edge TTS - Output to Bluetooth speaker"""
    communicate = edge_tts.Communicate(
        text, 
        voice,
        rate="+10%"
    )
    await communicate.save("temp_audio.mp3")

def speak(text):
    """Convert text to speech and play on Bluetooth speaker"""
    clean_text = remove_emojis(text)
    
    if len(clean_text) > 300:
        clean_text = clean_text[:300] + "..."
    
    print(f"\n💬 Saira: {clean_text}\n")
    
    try:
        voice = "en-IN-NeerjaNeural"  # Indian Female voice
        asyncio.run(speak_edge(clean_text, voice))
        
        pygame.mixer.music.load("temp_audio.mp3")
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        
        pygame.mixer.music.unload()
        time.sleep(0.1)
        
        if os.path.exists("temp_audio.mp3"):
            try:
                os.remove("temp_audio.mp3")
            except:
                pass
                
    except Exception as e:
        print(f"❌ Speech error: {e}")

def chat_with_model(user_input):
    """Gemma 3:4B optimized for Ryzen 7 Vega 7 (8GB RAM)"""
    chat_history.append({"role": "user", "content": user_input})

    # Keep only last 4 messages for RAM safety
    if len(chat_history) > 5:
        chat_history[1:3] = []

    response = ollama.chat(
        model="gemma3:1b",
        messages=chat_history,
        options={
            "num_thread": 8,
            "gpu_layers": 2,
            "num_predict": 256,
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        }
    )
    
    reply = response['message']['content']
    chat_history.append({"role": "assistant", "content": reply})
    
    return remove_emojis(reply)

def listen():
    """Listen from mic - Robot's microphone"""
    with sr.Microphone() as source:
        print("\n🎤 Listening from robot mic...")
        
        # Send status to website
        socketio.emit('status_update', {
            'status': 'listening',
            'message': 'Listening...'
        })
        
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            audio = recognizer.listen(
                source, 
                timeout=8,
                phrase_time_limit=15
            )
            
            print("📄 Processing...")
            socketio.emit('status_update', {
                'status': 'processing',
                'message': 'Processing...'
            })
            
            text = recognizer.recognize_google(
                audio, 
                language="en-IN",
                show_all=False
            )
            
            print(f"✅ You said: {text}")
            
            # Send user text to website
            socketio.emit('user_input', {
                'text': text
            })
            
            return text.lower()
            
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            socketio.emit('status_update', {
                'status': 'ready',
                'message': 'Ready to listen'
            })
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand")
            socketio.emit('status_update', {
                'status': 'error',
                'message': 'Could not understand, please repeat'
            })
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            socketio.emit('status_update', {
                'status': 'error',
                'message': f'Error: {str(e)}'
            })
            return None

def robot_loop():
    """Main robot loop - Runs in background"""
    print("\n" + "="*50)
    print("🤖 SAIRA ROBOT - PHYSICAL VERSION")
    print("="*50)
    print("\n📱 Website: Visual interface on phone")
    print("🎤 Mic: Robot's microphone")
    print("🔊 Voice: Bluetooth speaker output")
    print("\n" + "="*50 + "\n")
    
    socketio.emit('status_update', {
        'status': 'ready',
        'message': 'Ready to listen'
    })
    
    time.sleep(2)  # Wait for website to load
    
    try:
        while True:
            user_input = listen()
            
            if not user_input:
                time.sleep(0.5)
                continue
            
            # Exit commands
            if any(word in user_input for word in ["exit", "bye", "quit", "stop"]):
                socketio.emit('status_update', {
                    'status': 'goodbye',
                    'message': 'Goodbye!'
                })
                speak("Goodbye, take care")
                break
            
            # Get AI response
            print("🤔 Thinking...")
            socketio.emit('status_update', {
                'status': 'thinking',
                'message': 'Thinking...'
            })
            
            ai_reply = chat_with_model(user_input)
            
            # Send response to website for typing animation
            socketio.emit('ai_response', {
                'text': ai_reply
            })
            
            # Speak through Bluetooth speaker
            speak(ai_reply)
            
            time.sleep(0.5)
            
            # Ready for next input
            socketio.emit('status_update', {
                'status': 'ready',
                'message': 'Ready to listen'
            })
            
    except KeyboardInterrupt:
        print("\n\n⛔ Stopped by user")
    finally:
        pygame.mixer.quit()
        print("👋 Saira signing off!")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('📱 Website connected!')
    emit('status_update', {
        'status': 'ready',
        'message': 'Ready to listen'
    })

@socketio.on('disconnect')
def handle_disconnect():
    print('📱 Website disconnected!')

if __name__ == '__main__':
    # Start robot loop in background thread
    robot_thread = Thread(target=robot_loop, daemon=True)
    robot_thread.start()
    
    # Start Flask server
    print("\n🌐 Starting server...")
    print("📱 Open on phone: http://YOUR_IP:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
