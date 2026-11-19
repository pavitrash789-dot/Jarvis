# 🤖 Jarvis – Personal AI Voice Assistant

Jarvis is a smart voice assistant inspired by Iron Man's J.A.R.V.I.S. It listens to your voice, understands your commands, and performs tasks for you, so you can get things done without touching the keyboard.

## ✨ Features
- 🎙️ Voice commands with speech recognition
- 🔊 Natural spoken replies (text-to-speech)
- 🌐 Open websites and search Google or YouTube by voice
- 🎵 Play music and videos
- 🕒 Tell the time, date, and weather
- 💻 Open and control desktop applications
- 🧠 AI-powered answers to your questions
- ➕ Easy to extend with your own custom commands

## 🛠️ Tech Stack
Python, SpeechRecognition, pyttsx3, PyAudio, (add any APIs you use)

## 🚀 Getting Started
1. Clone the repo: `git clone https://github.com/pavitrash789-dot/Jarvis.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env`:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY
   ```
4. Run:
   ```bash
   ./run.sh            # Voice mode
   ./run.sh --keyboard # Text mode
   ```

## 📌 Future Improvements
- Wake-word detection
- Smart home control
- Email and calendar integration

## 📄 License
MIT License
