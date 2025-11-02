# 🧠 Saira AI – Voice Assistant & Q&A System

Saira is a **local AI-powered voice assistant and learning tool** developed by students of **Rawat Senior Secondary School, Jaipur (India)** — *Aryan, Umang, Arvin, and Monu*.  
It can **listen, understand, speak, and answer** both general and educational questions using **speech recognition**, **text-to-speech**, and **local or online AI models**.

---

## 📂 Project Structure

| File | Description |
|------|--------------|
| **saira.py** | Main Flask + SocketIO server for real-time AI voice assistant. Handles speech recognition, TTS (Edge-TTS), and AI chat responses using local Ollama models. |
| **saira0.2.py** | Standalone offline voice-based Q&A mode using `qa_blocks.txt` (no API needed). Works entirely locally. |
| **saira0.3.py** | Gemini API–based version for online conversation. Uses Google Gemini (`1.5-flash` or `2.5-flash`) for smarter replies with voice output. |
| **database-editor.py** | Graphical QA Block Editor built with Tkinter to manage question–answer pairs. |
| **qa_blocks.txt** | Knowledge base (text) containing 40+ educational topics with multiple answers per question. |
| **qa_meta.json** | Metadata file for Q&A usage tracking. |
| **requirements.txt** | List of all required Python dependencies. |

---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/saira-ai.git
cd saira-ai
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

**Dependencies used:**
- flask  
- flask-socketio  
- flask-cors  
- ollama  
- speechrecognition  
- edge-tts  
- pygame  
- requests  
- asyncio  
- tk  

> 🗣 You’ll also need **PyAudio** installed for microphone input:  
> ```bash
> pip install pyaudio
> ```  
> (If it fails on Windows, use: `pip install pipwin && pipwin install pyaudio`)

---

## 💬 How It Works

### 🧩 1. saira.py – Local Voice Assistant
Runs a web-connected assistant that:
- Listens from your microphone  
- Uses **Ollama** local model (e.g., `gemma3:1b`) to generate replies  
- Speaks responses with **Microsoft Edge neural voice (`en-IN-NeerjaNeural`)**  
- Sends updates via **SocketIO** for real-time web interaction  

Run:
```bash
python saira.py
```
Then open your local web interface or console to chat with Saira.

---

### 🎧 2. saira0.2.py – Offline Q&A Assistant
Works completely offline using your `qa_blocks.txt` database.

Features:
- Listens for your voice question  
- Finds the best matching question from QA blocks  
- Speaks the selected answer aloud  

Run:
```bash
python saira0.2.py
```

Edit or expand your questions easily using **database-editor.py**.

---

### ☁️ 3. saira0.3.py – Gemini API Version
An online version powered by **Google Gemini (Generative AI)**.  
It supports **English** and **Hinglish** automatically.

**Features:**
- Detects if input is English or Hinglish (roman Hindi)
- Removes any Hindi script (Devanagari)
- Auto-switches between multiple API keys
- Speaks using Edge-TTS
- Gives offline fallback replies if the API fails

Run:
```bash
python saira0.3.py
```

> ⚠️ Replace the `API_KEYS` list inside `saira0.3.py` with your valid Gemini API keys.

---

### 🧰 4. database-editor.py – QA Database Editor
A full-featured **GUI tool** (Tkinter) to manage your `qa_blocks.txt`.

**Features:**
- Add, delete, duplicate, and search Q&A blocks  
- Auto-create backups of old versions  
- Export data as JSON  
- Keyboard shortcuts (`Ctrl + S` to save, `Ctrl + F` to search)  

Run:
```bash
python database-editor.py
```

---

## 🎙 Voice and Audio

- Uses **SpeechRecognition + PyAudio** for microphone input  
- Uses **Edge-TTS** for text-to-speech (Indian English female voice)  
- Plays generated speech via **Pygame mixer**

---

## 💡 Tips

- For best accuracy, use a **USB microphone** or **Bluetooth mic**.  
- To make Saira faster:
  - Use smaller AI models (`gemma:2b` instead of `gemma:7b`)
  - Keep chat history short (already optimized)
- You can change the voice in `saira.py` or `saira0.3.py` by modifying the line:  
  ```python
  voice = "en-IN-NeerjaNeural"
  ```
  (List of available voices: https://github.com/rany2/edge-tts#voices)

---

## 🧑‍💻 Developers

**Team Saira – Rawat Senior Secondary School, Jaipur**

- Aryan  
- Umang  
- Arvin  
- Monu  

---

## 🪪 License

This project is released for **educational and personal use only.**  
Commercial use or redistribution without permission is prohibited.

---

## ⭐ Support

If you like this project, please **star the repository** on GitHub 🌟  
Your support helps make Saira even smarter and more human-like!
