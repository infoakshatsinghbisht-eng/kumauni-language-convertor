# -*- coding: utf-8 -*-
"""
Test suite for the Kumaoni Voice Translator Web App & FastAPI Backend.
Validates all voice translation, dialogue, culture, literature, calendar,
numbers, and grammar endpoints with the updated Kumaoni library.
"""

import sys
from pathlib import Path
import unittest

PROJECT_DIR = Path(__file__).resolve().parent.parent
POSSIBLE_LIB_PATHS = [
    PROJECT_DIR.parent,
    PROJECT_DIR.parent / "kumaoni language library",
    PROJECT_DIR / "kumaoni",
]
for p in POSSIBLE_LIB_PATHS:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "backend"))

from backend.server import (
    app,
    health_check,
    translate_voice,
    handle_dialogue_exchange,
    get_spoken_phrases,
    get_kumaoni_proverbs,
    get_kumaoni_riddles,
    get_kumaoni_literature,
    get_kumaoni_calendar,
    convert_number,
    analyze_grammar,
    get_synthesized_wav,
    VoiceTranslateRequest,
    DialogueExchangeRequest,
    NumberConvertRequest,
    GrammarAnalyzeRequest,
)


class TestVoiceAppAPI(unittest.TestCase):

    def test_health_check(self):
        data = health_check()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "kumaoni-voice-translator")
        self.assertGreaterEqual(data["total_morph_words"], 300000)
        self.assertGreaterEqual(data["phrases_count"], 100)
        self.assertGreaterEqual(data["proverbs_count"], 40)
        self.assertGreaterEqual(data["riddles_count"], 15)
        self.assertIn("current_season", data)

    def test_voice_translate_colloquial_english(self):
        # Test newly updated colloquial kinship & question translations
        req = VoiceTranslateRequest(
            text="Where is mom?",
            source_lang="en",
            target_dialect="central",
            method="auto",
            generate_audio=True,
        )
        data = translate_voice(req)
        self.assertIn("translated_text", data)
        self.assertIn("ईजा", data["translated_text"])
        self.assertIn("romanized", data)
        self.assertIn("syllables", data)
        self.assertIn("ssml", data)
        self.assertIsNotNone(data.get("audio_wav_base64"))
        self.assertTrue(len(data.get("tokens_analysis", [])) > 0)

    def test_voice_translate_hospital_question(self):
        req = VoiceTranslateRequest(
            text="Where is the hospital?",
            source_lang="en",
            target_dialect="central",
            method="auto",
            generate_audio=True,
        )
        data = translate_voice(req)
        self.assertTrue(len(data["translated_text"]) > 0)
        self.assertIn("romanized", data)

    def test_dialogue_visitor(self):
        req = DialogueExchangeRequest(
            speaker="person_a",
            message="Where is the river?",
            source_lang="en",
            target_dialect="central",
        )
        data = handle_dialogue_exchange(req)
        self.assertEqual(data["direction"], "visitor_to_local")
        self.assertIn("translated_kumaoni", data)
        self.assertIn("romanized", data)

    def test_dialogue_native(self):
        req = DialogueExchangeRequest(
            speaker="person_b",
            message="यो पाणि मीठ छ।",
            source_lang="kmy",
            target_dialect="central",
        )
        data = handle_dialogue_exchange(req)
        self.assertEqual(data["direction"], "local_to_visitor")
        self.assertIn("translated_english", data)

    def test_voice_phrases_filter_and_search(self):
        # Test category filtering
        data = get_spoken_phrases(category="greetings")
        self.assertEqual(data["category"], "greetings")
        self.assertGreater(data["count"], 0)

        # Test search query
        search_data = get_spoken_phrases(category="all", query="water")
        self.assertGreaterEqual(search_data["count"], 0)

    def test_proverbs_endpoint(self):
        data = get_kumaoni_proverbs(limit=10)
        self.assertGreater(data["count"], 0)
        self.assertIn("kumaoni", data["proverbs"][0])
        self.assertIn("meaning_en", data["proverbs"][0])

    def test_riddles_endpoint(self):
        data = get_kumaoni_riddles()
        self.assertGreater(data["count"], 0)
        self.assertTrue("riddle" in data["riddles"][0] or "kumaoni" in data["riddles"][0])

    def test_literature_endpoint(self):
        data = get_kumaoni_literature()
        self.assertIn("epics", data)
        self.assertIn("authors", data)
        self.assertGreater(len(data["epics"]), 0)

    def test_calendar_endpoint(self):
        data = get_kumaoni_calendar()
        self.assertIn("current_season", data)
        self.assertIn("months", data)
        self.assertIn("seasons", data)
        self.assertIn("days_of_week", data)

    def test_number_converter(self):
        req = NumberConvertRequest(number=108, form="cardinal")
        data = convert_number(req)
        self.assertEqual(data["number"], 108)
        self.assertIn("words", data)
        self.assertEqual(data["devanagari_num"], "१०८")

    def test_grammar_analyzer(self):
        req = GrammarAnalyzeRequest(text="खाँछ")
        data = analyze_grammar(req)
        self.assertEqual(data["word"], "खाँछ")
        self.assertIn("root", data)
        self.assertIn("syllables", data)

    def test_voice_wav_stream(self):
        resp = get_synthesized_wav(duration=0.2, freq=440.0)
        self.assertEqual(resp.media_type, "audio/wav")
        self.assertTrue(resp.body.startswith(b"RIFF"))


if __name__ == "__main__":
    unittest.main()
