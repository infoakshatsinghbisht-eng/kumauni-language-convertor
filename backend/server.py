# -*- coding: utf-8 -*-
"""
Kumaoni Voice Translator - FastAPI Backend Server.
Provides high-performance REST and streaming APIs for voice translation,
speech phonetics analysis, SSML generation, PCM WAV audio synthesis,
proverbs, riddles, literature, calendar, and grammatical analysis.
"""

import os
import sys
import base64
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

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
    version="1.1.0",
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


class VoiceTranslateRequest(BaseModel):
    text: str = Field(..., description="Source text or spoken transcript to translate")
    source_lang: str = Field("auto", description="Source language code (e.g., 'en', 'hi', 'fr', 'auto')")
    target_dialect: str = Field("central", description="Kumaoni dialect ('central', 'eastern', 'western')")
    method: str = Field("auto", description="Translation engine ('auto', 'rule_based', 'pivot', 'llm')")
    generate_audio: bool = Field(True, description="Whether to include base64 audio and pitch envelope")
    api_key: Optional[str] = Field(None, description="Optional LLM API key for neural mode")


class VoiceTranslateResponse(BaseModel):
    source_text: str
    source_lang: str
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
    source_lang: str = Field("en", description="Language of speaker ('en', 'hi', 'kmy', etc.)")
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
        "version": "1.1.0",
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
    Translates input text into authentic Kumaoni with syllabic breakdown, SSML, and audio.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    res = voice_translate(
        text=req.text,
        source_lang=req.source_lang,
        method=req.method,
        generate_audio=req.generate_audio,
        api_key=req.api_key,
    )
    result_dict = res.to_dict()
    result_dict["dialect"] = req.target_dialect

    # Analyze tokens for morphological insights
    tokens = [t.strip(",.?!;:। ") for t in result_dict["translated_text"].split() if t.strip(",.?!;:। ")]
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
    result_dict["tokens_analysis"] = token_analyses

    return result_dict


@app.post("/api/voice/dialogue")
def handle_dialogue_exchange(req: DialogueExchangeRequest):
    """
    Two-way dialogue helper for conversations between a visitor and a Kumaoni native.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if req.speaker == "person_a":
        # Visitor speaking in English/Hindi/other -> Translate to Kumaoni
        res = voice_translate(req.message, source_lang=req.source_lang, generate_audio=True)
        return {
            "speaker": req.speaker,
            "original": req.message,
            "translated_kumaoni": res.translated_text,
            "romanized": res.romanized,
            "syllables": res.syllables,
            "audio_wav_base64": res.audio_wav_base64,
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
