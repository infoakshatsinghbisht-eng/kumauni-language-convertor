# 🎙️ Kumaoni Voice Translator (कुमाऊँनी आवाज अनुवादक)

A modern, full-stack Voice Translation and Cultural Intelligence application powered by the [`kumaoni`](https://github.com/infoakshatsinghbisht-eng/kumaoni-language-library) language library (300,516+ word forms).

Features real-time multilingual Speech-to-Speech translation into authentic Central Pahari Kumaoni with live 60fps audio waveform visualization, two-way conversational dialogue mode, colloquial English synonym resolution (mom $\to$ ईजा, dad $\to$ बाबु, grandma $\to$ आमा, etc.), mountain phraseboards, Himalayan proverbs, riddles, folk literature, and cultural calendar.

---

## 🌟 Key Features

1. **🎙️ Real-Time Speech-to-Speech (STT $\to$ Translation $\to$ Spoken TTS)**:
   - Speak in English, Hindi, Nepali, French, Spanish, German, etc.
   - Converts speech into authentic Kumaoni with Central Pahari phonetic cadences and retroflex timing.
   - Real-time Syllable Stress Breakdown and Grammar / Morphological Insights.
2. **✨ Colloquial English Kinship & Question Intelligence**:
   - Seamlessly translates modern colloquial expressions (`Where is mom?` $\to$ `ईजा कहाँ छ?`, `Dad is at home` $\to$ `बाबु घर में छन`, `grandpa` $\to$ `बूबू`, `grandma` $\to$ `आमा`, `bro` $\to$ `दाज्यू`, `sis` $\to$ `दीदी`, `kids` $\to$ `नान्तिन`).
3. **🏔️ Dialect Selection**:
   - Supports **Central (Khasparjiya / Almora)**, **Eastern (Kumaiya / Champawat)**, and **Western (Danpuriya / Bageshwar)** dialects.
4. **📊 Live 60fps Audio Waveform Visualizer**:
   - Animated canvas visualizer pulsing in real time with microphone input and speech synthesis.
5. **💬 Two-Way Dialogue Mode**:
   - Split-screen conversation studio for **Tourist / Visitor** $\leftrightarrow$ **Local Mountain Resident (पहाड़ी)**.
6. **🏔️ Mountain Phraseboard (100+ Phrases)**:
   - Instant one-tap spoken dialogues across Greetings, Mountain Trails & Roads, Food & Hospitality, Health & Emergency, Weather, Family, and Market.
7. **📜 Himalayan Wisdom & Lore**:
   - **Proverbs (अखाण / पखाण)**: Authentic Kumaoni proverbs with figurative and literal English/Hindi meanings.
   - **Interactive Riddles (आणा)**: Mountain riddles with interactive "Reveal Answer" toggle.
   - **Folk Literature & Epics**: *Bedu Pako Baramasa*, *Malushahi & Rajula*, *Ajuwa Bafol*, and biographies of folk literary masters (Gumani Pant, Gaurda).
8. **📅 Kumaoni Calendar & Number Converter**:
   - Dynamic Himalayan 6 Seasons (ऋतु: बसंत, रूड़ि, चौमास, सरद, स्यूँद, जाड़) and 12 Kumaoni months (चैत to फागुन).
   - Numeric converter for any integer to spoken Kumaoni words, ordinals, and Devanagari numerals.
9. **🕒 Session History**:
   - Live session timeline with instant one-click audio replay and export.

---

## 🚀 Quickstart

### 1. Run the Full App with Python (One Command)
```bash
python run_app.py
```
Open **`http://localhost:8000`** in your browser.

---

### 2. Or Run Backend & Frontend Separately (Developer Mode)

#### Start Backend (FastAPI):
```bash
cd backend
pip install -r requirements.txt
python server.py 8000
```

#### Start Frontend (Vite):
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:3000`**.

---

## 🏗️ Architecture

```
kumaoni-voice-translator/
├── backend/
│   ├── server.py             # FastAPI REST & Streaming Backend with full Kumaoni integration
│   └── requirements.txt      # Backend dependencies (fastapi, uvicorn, pydantic)
├── frontend/
│   ├── src/
│   │   ├── app.js            # Client-side Speech, Visualizer, & Culture Studio
│   │   └── style.css         # Modern Glassmorphism & Neon Design System
│   ├── index.html            # Main UI Shell with Tab Navigation & Wisdom Studio
│   ├── package.json          # Node & Vite configuration
│   └── vite.config.js        # Vite dev-server config with API proxy
├── tests/
│   └── test_voice_app.py     # Comprehensive automated test suite
├── run_app.py                # Single-command application launcher
└── README.md
```

---

## 📜 API Documentation

When the backend is running, interactive Swagger API docs are available at **`http://localhost:8000/docs`**.

- `GET /api/health`: Service status, total word count (300k+), phrase count, and current Himalayan season.
- `POST /api/voice/translate`: Universal voice translation with syllables, morphology tokens, and SSML.
- `POST /api/voice/dialogue`: Two-way conversation helper with audio generation.
- `GET /api/voice/phrases`: Curated mountain dialogue phrasebook with category filtering and keyword search.
- `GET /api/culture/proverbs`: Authentic Kumaoni proverbs with search and category filtering.
- `GET /api/culture/riddles`: Himalayan riddles with questions and solutions.
- `GET /api/culture/literature`: Folk poetry, songs, and epic lore.
- `GET /api/culture/calendar`: Kumaoni months, current season/ritu, days of the week, and festivals.
- `POST /api/numbers/convert`: Converts integer numbers to Kumaoni words and Devanagari numerals.
- `POST /api/grammar/analyze`: Morphological analysis and dictionary lookup.
- `GET /api/voice/wav`: Synthesized uncompressed PCM WAV audio stream.
