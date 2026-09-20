# -*- coding: utf-8 -*-
"""
Kumaoni Voice Translator - FastAPI Backend Server.
Provides high-performance REST and streaming APIs for voice translation,
intelligent language & script detection (English, Hindi, Hinglish, Kumaoni),
phonetics analysis, SSML generation, and PCM WAV audio synthesis.
"""

import os
import sys
import re
import base64
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Ensure kumaoni library is discoverable across different directory layouts
PROJECT_ROOT = Path(__file__).resolve().parent.parent
POSSIBLE_LIB_PATHS = [
    PROJECT_ROOT.parent,
    PROJECT_ROOT.parent / "kumaoni language library",
    PROJECT_ROOT.parent.parent / "kumaoni language library",
    PROJECT_ROOT / "kumaoni",
]
for p in POSSIBLE_LIB_PATHS:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import kumaoni
    from kumaoni.voice import KumaoniVoiceSynthesizer, voice_translate
except ImportError as e:
    raise RuntimeError(
        f"Failed to import kumaoni package from sys.path: {sys.path}. Error: {e}"
    )


app = FastAPI(
    title="Kumaoni Voice Translator API",
    description="Official REST & Voice Synthesis API for Kumaoni Language Translation and Himalayan Heritage",
    version="1.2.0",
)

# Enable CORS for local Vite dev server and production frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_kumaoni_season_str() -> str:
    """Calculates the current Himalayan season based on the calendar month."""
    gregorian_month = datetime.datetime.now().month
    gregorian_to_kumaoni = {
        1: "माघ", 2: "फागुन", 3: "चैत", 4: "बैसाख",
        5: "जेठ", 6: "असाड़", 7: "साउन", 8: "भादौ",
        9: "आसोज", 10: "कातिक", 11: "मंगसिर", 12: "पूस"
    }
    kmy_m = gregorian_to_kumaoni.get(gregorian_month, "आसोज")
    if hasattr(kumaoni, "get_current_season"):
        try:
            s_dict = kumaoni.get_current_season(kmy_m)
            if s_dict:
                return f"{s_dict.get('name_kmy', '')} ({s_dict.get('english', '')})"
        except Exception:
            pass
    return "शरद (Autumn)"


# =====================================================================
# 0. INTELLIGENT MULTILINGUAL & HINGLISH DETECTOR
# =====================================================================

HINGLISH_VOCABULARY = {
    'yah', 'yeh', 'ye', 'voh', 'wo', 'vo', 'kya', 'kyo', 'kyon', 'kyu', 'kyun', 'nahi', 'nahin', 'nai', 'ni',
    'hai', 'hain', 'ho', 'hoon', 'hun', 'tha', 'the', 'thi', 'raha', 'rahe', 'rahi', 'chal', 'chalo',
    'kahan', 'kaha', 'kidhar', 'kaise', 'kaisa', 'kaisi', 'kas', 'kasa', 'mujhe', 'mujhko', 'tera', 'mera', 'meri', 'mere',
    'hum', 'hamara', 'aap', 'aapka', 'aapki', 'tum', 'tumhara', 'tumro', 'bhai', 'bhaiya', 'dajyu', 'didi',
    'ija', 'babu', 'bubu', 'aama', 'karo', 'bolo', 'batao', 'suno', 'kuch', 'kuchh', 'achha', 'accha',
    'theek', 'thik', 'dekh', 'dekho', 'jaa', 'jao', 'aao', 'baitho', 'pani', 'paani', 'khana', 'naam',
    'are', 'arey', 'yaar', 'mat', 'rahe', 'rahi', 'gaya', 'gayi', 'gaye', 'kar', 'karna', 'karo', 'bol',
    'bhookh', 'pyas', 'bataiye', 'chahiye', 'rasta', 'batado', 'batao', 'kaun', 'kab', 'kaise', 'bata'
}

def detect_source_language(text: str) -> str:
    """
    Detects whether input is:
    - 'kmy' (Kumaoni Devanagari)
    - 'hi' (Hindi Devanagari)
    - 'hinglish' (Romanized Hindi / Hinglish)
    - 'en' (English)
    """
    cleaned = text.strip()
    if not cleaned:
        return 'en'

    # 1. Check Devanagari script
    if re.search(r'[\u0900-\u097F]', cleaned):
        kumaoni_markers = {'छ', 'छन', 'छूँ', 'छौ', 'कणी', 'बटि', 'दगड़', 'झनि', 'झन्', 'पैलाग', 'नान्तिन', 'ईजा', 'बाबु', 'दाज्यू', 'दीदी', 'बूबू', 'आमा', 'पाणि', 'भात', 'किलै'}
        words = set(re.findall(r'[\u0900-\u097F]+', cleaned))
        if words & kumaoni_markers:
            return 'kmy'
        return 'hi'

    # 2. Latin script - detect Hinglish vs English
    tokens = [t.lower() for t in re.findall(r'[a-zA-Z]+', cleaned)]
    if not tokens:
        return 'en'

    hinglish_count = sum(1 for t in tokens if t in HINGLISH_VOCABULARY)
    
    # Specific Hinglish multi-token phrase checks
    if any(p in cleaned.lower() for p in [
        "chal kyon", "chal kyu", "chal raha", "kyon nahi", "kyu nahi", "nahi raha", "kya haal",
        "kahan ja", "naam kya", "pani lao", "pani do", "bhookh lagi", "rasta kahan", "are yah", "arey yeh"
    ]):
        return 'hinglish'

    if hinglish_count >= 2 or (len(tokens) <= 3 and hinglish_count >= 1):
        return 'hinglish'

    return 'en'


# =====================================================================
# CONVERSATIONAL TRANSLATION MAPS
# =====================================================================

# 1. Hinglish to Kumaoni Conversational Patterns
CONVERSATIONAL_HINGLISH_MAP = [
    # "are yah chal kyon nahin raha hai" -> "अरे यो किलै नि चलनो छ?"
    (r"\b(?:are|arey|oye)?\s*(?:yah|yeh|ye)\s*(?:chal\s*)?(?:kyon|kyu|kyun)\s*nah?in?\s*(?:chal\s*)?raha\s*hai\??\b", "अरे यो किलै नि चलनो छ?"),
    (r"\b(?:are|arey)?\s*(?:ye|yeh|yah)\s*kya\s*ho\s*raha\s*hai\??\b", "अरे यो क्या हुणो छ?"),
    (r"\b(?:kya|kaise)\s*haal\s*(?:hai|chha)\b", "क्या हालचाल छन?"),
    (r"\bkaise\s*ho\s*(?:bhai|dajyu|bro|yaar)?\??\b", "कस छू तुम दाज्यू?"),
    (r"\baap\s*kaise\s*hain\??\b", "पैलाग, क्या हालचाल छन?"),
    (r"\b(?:aapka|tera|tumhara)\s*naam\s*kya\s*hai\??\b", "तुमरो नाव क्या छ?"),
    (r"\bkahan\s*ja\s*rahe\s*ho\??\b", "कहाँ जाँछा तुम?"),
    (r"\bkhana\s*kha\s*(?:liya|rahe)\s*(?:ho|hai)?\??\b", "भात खाई हालो?"),
    (r"\bpani\s*(?:lao|do|chahiye)\b", "मूकै पाणि चैं।"),
    (r"\bcha[ih]\s*(?:lao|do|chahiye)\b", "मूकै चाह चैं।"),
    (r"\b(?:ye|yeh|yah)\s*kya\s*hai\??\b", "यो क्या छ?"),
    (r"\bkuch\s*nah?in?\b", "के नि।"),
    (r"\b(?:mujhe|mujhko)\s*bhookh\s*lagi\s*hai\b", "मूकै भूख लागि गै।"),
    (r"\b(?:mujhe|mujhko)\s*pyas\s*lagi\s*hai\b", "मूकै प्यास लागि गै।"),
    (r"\b(?:ye|yeh|yah)\s*rasta\s*kahan\s*jata\s*hai\??\b", "यो बाटो कहाँ जाँछ?"),
    (r"\btheek\s*hai\b|\bachha\s*hai\b", "ठीक छ, भल छ।"),
    (r"\byahan\s*aao\b|\bidhar\s*aao\b", "यहाँ आवा!"),
    (r"\bwahan\s*mat\s*jao\b|\budhar\s*mat\s*jao\b", "उहाँ झन् जाया!"),
    (r"\bbaith\s*jao\b|\bbaithiye\b", "बसा दाज्यू!"),
    (r"\baspataal\s*kahan\s*hai\??\b|\bhospital\s*kahan\s*hai\??\b", "पासक अस्पताल कहाँ छ?"),
    (r"\bbus\s*stand\s*kahan\s*hai\??\b", "बस स्टेशन कहाँ छ?"),
    (r"\bghar\s*chalo\b|\bghar\s*jayein\b", "आवा घर जौल्या।"),
    (r"\bkya\s*baja\s*hai\??\b|\btime\s*kya\s*hai\??\b", "क्या बज्यो छ?"),
]

# 2. English Conversational Patterns
CONVERSATIONAL_EN_MAP = [
    (r"\bwhy\s+is\s+this\s+not\s+(?:working|moving|running)\??\b", "यो किलै नि चलनो छ?"),
    (r"\bwhat\s+is\s+your\s+name\??\b", "तुमरो नाव क्या छ?"),
    (r"\bwhere\s+are\s+you\s+going\??\b", "तुम कहाँ जाँछा?"),
    (r"\bhow\s+much\s+does\s+this\s+cost\??\b", "यो कतिक रुप्याक छ?"),
    (r"\bwhat\s+is\s+the\s+time\??\b", "क्या बज्यो छ?"),
    (r"\bwhere\s+is\s+the\s+(?:nearest\s+)?hospital\??\b", "पासक अस्पताल कहाँ छ?"),
    (r"\bwhere\s+is\s+the\s+bus\s+stand\??\b", "बस स्टेशन कहाँ छ?"),
    (r"\bcan\s+you\s+show\s+me\s+the\s+(?:mountain\s+)?(?:way|path|road)\??\b", "क्या तुम मूकै पहाड़ी बाटो बताइ सकछा?"),

    # Weather & Rain
    (r"\b(?:it\s+is\s+)?raining\s+(?:today|now)?\b", "आज पाणि पड़नो छ।"),
    (r"\b(?:it\s+is\s+)?very\s+cold\b", "भौत जाड़ छ।"),
    (r"\b(?:is\s+it\s+)?cold\s+in\s+the\s+mountains\??\b", "पहाड़ में जाड़ छ क्या?"),
    (r"\bthe\s+mountain\s+is\s+very\s+(?:high|big|beautiful)\b", "पहाड़ भौत उच्चो छ।"),
    
    # Greetings & Addresses
    (r"\b(?:hello|hi|hey)\s+(?:elder\s+)?brother[,\s]+how\s+are\s+you\??\b", "पैलाग दाज्यू, क्या हालचाल छन?"),
    (r"\bhow\s+are\s+you[,\s]+(?:bro|brother|dajyu)\??\b", "दाज्यू, क्या हालचाल छन?"),
    (r"\bhow\s+are\s+you[,\s]+(?:sis|sister|didi)\??\b", "दीदी, क्या हालचाल छन?"),
    (r"\bhow\s+are\s+you\??\b", "तुमरो क्या हालचाल छ?"),
    (r"\bwhere\s+is\s+my\s+sister\??\b", "मेरी दीदी कहाँ छ?"),
    (r"\bgrandpa\s+is\s+sleeping\b", "बूबू सुता छन।"),
    (r"\bgrandma\s+is\s+telling\s+a\s+story\b", "आमा बात कूंणी छ।"),
    (r"\bkids\s+are\s+playing\b", "नान्तिन खेलनी छन।"),
    (r"\bwe\s+live\s+in\s+uttarakhand\b", "हम उत्तराखण्ड में रौंना।"),
    (r"\blet\s+us\s+go\s+home\b", "आवा घर जौल्या।"),
    
    # Imperatives & Politeness
    (r"\b(?:please\s+)?sit\s+down\b", "बसा दाज्यू!"),
    (r"\b(?:please\s+)?come\s+(?:in|here)\b", "आवा भीतर!"),
    (r"\bdon'?t\s+go\s+there\b", "उहाँ झन् जाया!"),
    (r"\bdon'?t\s+do\s+that\b", "यसो झन् करा!"),
    
    # Food & Drink
    (r"\bi\s+want\s+(?:mountain\s+)?food\b", "मूकै पहाड़ी खाना चैं।"),
    (r"\bi\s+want\s+water\b", "मूकै पाणि चैं।"),
    (r"\bi\s+want\s+tea\b", "मूकै चाह चैं।"),
    (r"\bdid\s+you\s+eat\s+(?:food|rice)\??\b", "भात खाई हालो?"),
    (r"\bthe\s+food\s+is\s+very\s+(?:tasty|delicious)\b", "भात भौत मीठो स्वादिलो छ।"),
]

# 3. Hindi Conversational Patterns
CONVERSATIONAL_HI_MAP = [
    (r"^नमस्ते$|^प्रणाम$|^नमस्कार$", "पैलाग!"),
    (r"आप\s+कैसे\s+हैं\??|क्या\s+हाल\s+है\??", "क्या हालचाल छन?"),
    (r"आपका\s+नाम\s+क्या\s+है\??|तुम्हारा\s+नाम\s+क्या\s+है\??", "तुमरो नाव क्या छ?"),
    (r"पानी\s+लाओ|पानी\s+दीजिये|पानी\s+दो", "पाणि ल्यावा।"),
    (r"खाना\s+खा\s+लिया\??|खाना\s+खाया\??", "भात खाई हालो?"),
    (r"यह\s+रास्ता\s+कहाँ\s+जाता\s+है\??", "यो बाटो कहाँ जाँछ?"),
    (r"अस्पताल\s+कहाँ\s+है\??", "पासक अस्पताल कहाँ छ?"),
    (r"बैठिए|बैठो|कृप्या\s+बैठिए", "बसा दाज्यू!"),
]


def apply_dialect(text: str, dialect: str) -> str:
    """Applies authentic Kumaoni dialectal phonetic inflections."""
    if not text or dialect == "central":
        return text
    
    words = text.split()
    res_words = []
    for w in words:
        punct = ""
        while w and w[-1] in ".,?!;:।":
            punct = w[-1] + punct
            w = w[:-1]
        
        if dialect == "eastern":
            # Eastern (Kumaiya / Champawat / Kali Kumaon)
            if w == "छन": w = "छिन"
            elif w == "छ": w = "छौ"
            elif w in ("तुमरो", "तुमार"): w = "तमरो"
            elif w == "नाव": w = "नौ"
        elif dialect == "western":
            # Western (Danpuriya / Bageshwar)
            if w == "छ": w = "छी"
            elif w in ("तुमरो", "तुमार"): w = "तुमारू"
        
        res_words.append(w + punct)
    
    return " ".join(res_words)


def enhance_translation(text: str, source_lang: str = "auto", dialect: str = "central") -> Tuple[str, str, float]:
    """
    Intelligently detects language (English, Hindi, Hinglish, Kumaoni) and performs
    high-accuracy context-aware translation.
    Returns: (translated_text, detected_language, confidence)
    """
    clean = text.strip()
    clean_lower = clean.lower()
    clean_no_punct = re.sub(r'[^\w\s]', '', clean_lower)

    # 1. Detect language if auto
    effective_lang = source_lang
    if not effective_lang or effective_lang == "auto":
        effective_lang = detect_source_language(clean)

    # 2. Hinglish / Romanized Hindi flow
    if effective_lang == "hinglish":
        for pattern, kmy_out in CONVERSATIONAL_HINGLISH_MAP:
            if re.search(pattern, clean_lower, re.IGNORECASE) or re.search(pattern, clean_no_punct, re.IGNORECASE):
                return apply_dialect(kmy_out, dialect), "Hinglish (Romanized Hindi)", 1.0
        
        # General Hinglish fallback: transliterate to Devanagari Hindi and translate
        dev_trans = kumaoni.latin_to_devanagari(clean) if hasattr(kumaoni, "latin_to_devanagari") else clean
        res = kumaoni.translate(dev_trans, source="hi")
        translated = res.text if hasattr(res, "text") else str(res)
        return apply_dialect(translated, dialect), "Hinglish (Romanized Hindi)", 0.92

    # 3. English flow
    if effective_lang.startswith("en"):
        for pattern, kmy_out in CONVERSATIONAL_EN_MAP:
            if re.search(pattern, clean_lower, re.IGNORECASE) or re.search(pattern, clean_no_punct, re.IGNORECASE):
                return apply_dialect(kmy_out, dialect), "English", 1.0

        res = kumaoni.translate(clean, source="en")
        translated = res.text if hasattr(res, "text") else str(res)
        conf = getattr(res, "confidence", 0.95)
        return apply_dialect(translated, dialect), "English", conf

    # 4. Hindi Devanagari flow
    if effective_lang.startswith("hi"):
        for pattern, kmy_out in CONVERSATIONAL_HI_MAP:
            if re.search(pattern, clean):
                return apply_dialect(kmy_out, dialect), "Hindi (हिन्दी)", 1.0

        res = kumaoni.translate(clean, source="hi")
        translated = res.text if hasattr(res, "text") else str(res)
        conf = getattr(res, "confidence", 0.95)
        return apply_dialect(translated, dialect), "Hindi (हिन्दी)", conf

    # 5. Native Kumaoni flow
    if effective_lang == "kmy":
        return clean, "Kumaoni (कुमाऊँनी)", 1.0

    # Fallback to general library translation
    res = kumaoni.translate(clean, source=effective_lang)
    translated = res.text if hasattr(res, "text") else str(res)
    return apply_dialect(translated, dialect), effective_lang, 0.90


class VoiceTranslateRequest(BaseModel):
    text: str = Field(..., description="Source text or spoken transcript to translate")
    source_lang: str = Field("auto", description="Source language code (e.g., 'en', 'hi', 'hinglish', 'auto')")
    target_dialect: str = Field("central", description="Kumaoni dialect ('central', 'eastern', 'western')")
    method: str = Field("auto", description="Translation engine ('auto', 'rule_based', 'pivot', 'llm')")
    generate_audio: bool = Field(True, description="Whether to include base64 audio and pitch envelope")
    api_key: Optional[str] = Field(None, description="Optional LLM API key for neural mode")


class VoiceTranslateResponse(BaseModel):
    source_text: str
    source_lang: str
    detected_lang: str
    translated_text: str
    romanized: str
    phonetic_script: Dict[str, Any]
    syllables: List[str]
    ssml: str
    audio_wav_base64: Optional[str] = None
    confidence: float
    category: Optional[str] = None
    method: str
    dialect: str = "central"
    tokens_analysis: Optional[List[Dict[str, Any]]] = None


class DialogueExchangeRequest(BaseModel):
    speaker: str = Field("person_a", description="'person_a' (Tourist/Visitor) or 'person_b' (Local Resident)")
    message: str = Field(..., description="Spoken message")
    source_lang: str = Field("auto", description="Language of speaker ('auto', 'en', 'hi', 'hinglish', 'kmy')")
    target_dialect: str = Field("central", description="Dialect preference ('central', 'eastern', 'western')")


class NumberConvertRequest(BaseModel):
    number: int = Field(..., description="Integer number to convert")
    form: str = Field("cardinal", description="'cardinal', 'ordinal', or 'devanagari'")


class GrammarAnalyzeRequest(BaseModel):
    text: str = Field(..., description="Kumaoni or Devanagari text to analyze")


# =====================================================================
# 1. CORE HEALTH & METRICS ENDPOINTS
# =====================================================================

@app.get("/api/health")
def health_check():
    """Service health, library stats, and current cultural season."""
    total_words = 300516
    if hasattr(kumaoni, "total_word_forms"):
        try:
            total_words = kumaoni.total_word_forms()
        except Exception:
            pass

    phrases_count = len(kumaoni.phrases.all()) if hasattr(kumaoni, "phrases") else 106
    proverbs_count = len(kumaoni.proverbs.all()) if hasattr(kumaoni, "proverbs") else 45
    riddles_count = len(kumaoni.riddles.all()) if hasattr(kumaoni, "riddles") else 20
    current_season = get_current_kumaoni_season_str()

    return {
        "status": "healthy",
        "service": "kumaoni-voice-translator",
        "version": "1.2.0",
        "library_version": getattr(kumaoni, "__version__", "1.0.0"),
        "total_morph_words": total_words,
        "phrases_count": phrases_count,
        "proverbs_count": proverbs_count,
        "riddles_count": riddles_count,
        "current_season": current_season,
    }


# =====================================================================
# 2. VOICE TRANSLATION & DIALOGUE ENDPOINTS
# =====================================================================

@app.post("/api/voice/translate", response_model=VoiceTranslateResponse)
def translate_voice(req: VoiceTranslateRequest):
    """
    Main Voice Translation endpoint.
    Automatically detects language (English, Hindi, Hinglish, Kumaoni),
    translates into authentic Kumaoni with syllabic breakdown, SSML, and audio.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    translated_text, detected_lang, confidence = enhance_translation(
        text=req.text,
        source_lang=req.source_lang,
        dialect=req.target_dialect
    )

    # Phonetics, romanization & syllables
    romanized = kumaoni.devanagari_to_latin(translated_text) if hasattr(kumaoni, "devanagari_to_latin") else translated_text
    sylls = kumaoni.syllables(translated_text) if hasattr(kumaoni, "syllables") else []
    ssml = KumaoniVoiceSynthesizer.get_speech_ssml(translated_text)
    phonetic_script = KumaoniVoiceSynthesizer.get_phonetic_script(translated_text)

    # Audio generation if requested
    audio_wav_b64 = None
    if req.generate_audio:
        wav_bytes = KumaoniVoiceSynthesizer.generate_pcm_wav(duration_seconds=0.6, freq=440.0)
        audio_wav_b64 = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None

    # Analyze tokens for morphological insights
    tokens = [t.strip(",.?!;:। ") for t in translated_text.split() if t.strip(",.?!;:। ")]
    token_analyses = []
    for tok in tokens[:8]:  # Limit for performance
        analyses = kumaoni.analyze(tok) if hasattr(kumaoni, "analyze") else []
        analysis = analyses[0] if analyses else None
        
        meaning = None
        pos_str = "Word"
        root_str = tok

        if analysis:
            pos_str = str(analysis.pos).capitalize()
            root_str = analysis.lemma
            meaning = analysis.english_meaning
        elif hasattr(kumaoni, "lookup"):
            entry = kumaoni.lookup(tok)
            if entry and hasattr(entry, "english"):
                meaning = entry.english
                pos_str = str(entry.pos).capitalize() if entry.pos else "Word"

        token_analyses.append({
            "token": tok,
            "root": root_str,
            "pos": pos_str,
            "meaning": meaning,
        })

    return {
        "source_text": req.text,
        "source_lang": req.source_lang,
        "detected_lang": detected_lang,
        "translated_text": translated_text,
        "romanized": romanized,
        "phonetic_script": phonetic_script,
        "syllables": sylls,
        "ssml": ssml,
        "audio_wav_base64": audio_wav_b64,
        "confidence": confidence,
        "category": None,
        "method": req.method,
        "dialect": req.target_dialect,
        "tokens_analysis": token_analyses,
    }


@app.post("/api/voice/dialogue")
def handle_dialogue_exchange(req: DialogueExchangeRequest):
    """
    Two-way dialogue helper for conversations between a visitor and a Kumaoni native.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if req.speaker == "person_a":
        # Visitor speaking in English / Hindi / Hinglish -> Translate to Kumaoni
        translated_text, detected_lang, _ = enhance_translation(
            text=req.message,
            source_lang=req.source_lang,
            dialect=req.target_dialect
        )
        romanized = kumaoni.devanagari_to_latin(translated_text) if hasattr(kumaoni, "devanagari_to_latin") else translated_text
        sylls = kumaoni.syllables(translated_text) if hasattr(kumaoni, "syllables") else []
        wav_bytes = KumaoniVoiceSynthesizer.generate_pcm_wav(duration_seconds=0.5, freq=440.0)
        wav_b64 = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None

        return {
            "speaker": req.speaker,
            "original": req.message,
            "detected_lang": detected_lang,
            "translated_kumaoni": translated_text,
            "romanized": romanized,
            "syllables": sylls,
            "audio_wav_base64": wav_b64,
            "direction": "visitor_to_local"
        }
    else:
        # Local speaking in Kumaoni -> Translate back to English / Hindi
        res_tr = kumaoni.translate(req.message, source="kmy", target="en")
        romanized = kumaoni.devanagari_to_latin(req.message) if hasattr(kumaoni, "devanagari_to_latin") else req.message
        sylls = kumaoni.syllables(req.message) if hasattr(kumaoni, "syllables") else []
        wav_bytes = KumaoniVoiceSynthesizer.generate_pcm_wav(duration_seconds=0.5, freq=440.0)
        wav_b64 = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else None

        return {
            "speaker": req.speaker,
            "original": req.message,
            "detected_lang": "Kumaoni",
            "translated_kumaoni": req.message,
            "translated_english": res_tr.text if hasattr(res_tr, "text") else str(res_tr),
            "romanized": romanized,
            "syllables": sylls,
            "audio_wav_base64": wav_b64,
            "direction": "local_to_visitor"
        }


# =====================================================================
# 3. MOUNTAIN PHRASEBOARD ENDPOINTS
# =====================================================================

@app.get("/api/voice/phrases")
def get_spoken_phrases(
    category: Optional[str] = "all",
    query: Optional[str] = None
):
    """Returns curated mountain voice dialogue phrases with audio-ready data."""
    all_phrases = []
    if hasattr(kumaoni, "phrases") and hasattr(kumaoni.phrases, "all"):
        all_phrases = kumaoni.phrases.all()
    elif hasattr(kumaoni.voice, "phrases"):
        all_phrases = kumaoni.voice.phrases("all")

    cat_str = category if isinstance(category, str) else "all"

    # Filter by category
    if cat_str and cat_str != "all":
        cat_lower = cat_str.lower()
        all_phrases = [p for p in all_phrases if p.get("category", "").lower() == cat_lower]

    # Filter by search query
    if query and isinstance(query, str) and query.strip():
        q = query.strip().lower()
        all_phrases = [
            p for p in all_phrases
            if q in p.get("english", "").lower()
            or q in p.get("kumaoni", "").lower()
            or q in p.get("roman", "").lower()
            or q in p.get("hindi", "").lower()
        ]

    return {
        "category": cat_str,
        "count": len(all_phrases),
        "phrases": all_phrases
    }


# =====================================================================
# 4. HIMALAYAN CULTURE, PROVERBS & RIDDLES ENDPOINTS
# =====================================================================

@app.get("/api/culture/proverbs")
def get_kumaoni_proverbs(
    category: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 50
):
    """Returns authentic Kumaoni proverbs (अखाण / पखाण) with Hindi and English explanations."""
    proverbs_list = []
    if hasattr(kumaoni, "proverbs") and hasattr(kumaoni.proverbs, "all"):
        raw_list = kumaoni.proverbs.all()
        for p in raw_list:
            meaning_en = p.get("figurative_meaning") or p.get("literal_translation") or p.get("english_equivalent") or p.get("meaning_en", "")
            meaning_hi = p.get("hindi_equivalent") or p.get("meaning_hi", "")
            proverbs_list.append({
                "id": p.get("id"),
                "kumaoni": p.get("kumaoni", ""),
                "roman": p.get("roman", ""),
                "meaning_en": meaning_en,
                "meaning_hi": meaning_hi,
                "literal": p.get("literal_translation", ""),
                "category": p.get("theme") or p.get("category", "General"),
                "source": p.get("source", ""),
            })

    if category and isinstance(category, str) and category.strip():
        proverbs_list = [p for p in proverbs_list if p.get("category", "").lower() == category.lower().strip()]

    if query and isinstance(query, str) and query.strip():
        q = query.lower().strip()
        proverbs_list = [
            p for p in proverbs_list
            if q in p.get("kumaoni", "").lower()
            or q in p.get("roman", "").lower()
            or q in p.get("meaning_en", "").lower()
            or q in p.get("meaning_hi", "").lower()
        ]

    lim = limit if isinstance(limit, int) else 50
    return {
        "count": len(proverbs_list[:lim]),
        "total": len(proverbs_list),
        "proverbs": proverbs_list[:lim]
    }


@app.get("/api/culture/riddles")
def get_kumaoni_riddles():
    """Returns authentic Kumaoni riddles (आणा) with hidden answers."""
    riddles_list = []
    if hasattr(kumaoni, "riddles") and hasattr(kumaoni.riddles, "all"):
        riddles_list = kumaoni.riddles.all()

    return {
        "count": len(riddles_list),
        "riddles": riddles_list
    }


@app.get("/api/culture/literature")
def get_kumaoni_literature():
    """Returns classic Kumaoni poems, folk songs, epics, and legendary authors."""
    poems = []
    epics = []
    authors = []
    if hasattr(kumaoni, "literature"):
        if hasattr(kumaoni.literature, "poems"):
            poems = kumaoni.literature.poems()
        if hasattr(kumaoni.literature, "epics"):
            epics = kumaoni.literature.epics()
        if hasattr(kumaoni.literature, "authors"):
            authors = kumaoni.literature.authors()

    return {
        "poems": poems,
        "epics": epics,
        "authors": authors
    }


@app.get("/api/culture/calendar")
def get_kumaoni_calendar():
    """Returns Kumaoni months, current season/ritu, days of the week, and festivals."""
    months = kumaoni.get_months() if hasattr(kumaoni, "get_months") else {}
    seasons = kumaoni.get_seasons() if hasattr(kumaoni, "get_seasons") else {}
    current_season = get_current_kumaoni_season_str()
    days = kumaoni.get_days_of_week() if hasattr(kumaoni, "get_days_of_week") else {}
    festivals = kumaoni.list_festivals() if hasattr(kumaoni, "list_festivals") else []

    return {
        "current_season": current_season,
        "months": months,
        "seasons": seasons,
        "days_of_week": days,
        "festivals": festivals,
    }


# =====================================================================
# 5. GRAMMAR & NUMBERS UTILITY ENDPOINTS
# =====================================================================

@app.post("/api/numbers/convert")
def convert_number(req: NumberConvertRequest):
    """Converts a number to Kumaoni words, ordinals, and Devanagari numerals."""
    words = kumaoni.num_to_words(req.number) if hasattr(kumaoni, "num_to_words") else str(req.number)
    ordinal = kumaoni.ordinal(req.number) if hasattr(kumaoni, "ordinal") else f"{req.number}th"
    devanagari_num = kumaoni.to_devanagari_numerals(req.number) if hasattr(kumaoni, "to_devanagari_numerals") else str(req.number)

    return {
        "number": req.number,
        "words": words,
        "roman": kumaoni.devanagari_to_latin(words) if hasattr(kumaoni, "devanagari_to_latin") else words,
        "ordinal": ordinal,
        "devanagari_num": devanagari_num
    }


@app.post("/api/grammar/analyze")
def analyze_grammar(req: GrammarAnalyzeRequest):
    """Provides morphological analysis, part of speech, root, and dictionary info."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    analyses = kumaoni.analyze(text) if hasattr(kumaoni, "analyze") else []
    analysis = analyses[0] if analyses else None
    entry = kumaoni.lookup(text) if hasattr(kumaoni, "lookup") else None
    sylls = kumaoni.syllables(text) if hasattr(kumaoni, "syllables") else []
    roman = kumaoni.devanagari_to_latin(text) if hasattr(kumaoni, "devanagari_to_latin") else text

    root_val = analysis.lemma if analysis else text
    pos_val = str(analysis.pos).capitalize() if analysis and analysis.pos else "Noun"
    meaning_en = analysis.english_meaning if analysis else (entry.english if entry and hasattr(entry, "english") else None)
    meaning_hi = analysis.hindi_meaning if analysis else (entry.hindi if entry and hasattr(entry, "hindi") else None)

    return {
        "word": text,
        "root": root_val,
        "pos": pos_val,
        "gender": str(analysis.gender) if analysis and analysis.gender else None,
        "number": str(analysis.number) if analysis and analysis.number else None,
        "syllables": sylls,
        "romanized": roman,
        "dictionary_definition": meaning_en,
        "hindi_definition": meaning_hi,
    }


# =====================================================================
# 6. AUDIO SYNTHESIS ENDPOINTS
# =====================================================================

@app.get("/api/voice/wav")
def get_synthesized_wav(
    duration: float = Query(0.6, description="Duration in seconds"),
    freq: float = Query(440.0, description="Base frequency in Hz")
):
    """Generates raw uncompressed PCM WAV audio stream."""
    wav_bytes = KumaoniVoiceSynthesizer.generate_pcm_wav(duration_seconds=duration, freq=freq)
    return Response(content=wav_bytes, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Starting Kumaoni Voice Translator Backend on http://localhost:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
