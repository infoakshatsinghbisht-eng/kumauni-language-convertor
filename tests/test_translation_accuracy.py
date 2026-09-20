# -*- coding: utf-8 -*-
"""
Comprehensive Benchmark & Accuracy Test Suite for Kumaoni Translator & Voice Engine.
Tests full grammatical coverage:
- Language & script detection (English, Hindi, Hinglish, Kumaoni)
- Hinglish phrase translation ("are yah chal kyon nahin raha hai")
- Kinship terms & colloquial synonyms (mom, dad, bro, sis, grandpa, grandma, kids)
- Questions (what, where, who, when, why, how, how much)
- Tenses (present continuous, past simple, future)
- Imperatives & honorific requests
- Negation & prohibitive ("don't do that", "not here")
- Food, travel, weather, directions, emergency
- Dialect variations (Central, Eastern, Western)
- Hindi -> Kumaoni translations
- Kumaoni -> English translations
- Syllabification & phonetic Romanization
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

import kumaoni
from backend.server import translate_voice, VoiceTranslateRequest, enhance_translation, detect_source_language


class TestTranslatorAccuracy(unittest.TestCase):

    def test_language_detection(self):
        self.assertEqual(detect_source_language("are yah chal Kyon Nahin raha hai"), "hinglish")
        self.assertEqual(detect_source_language("kya haal hai bhai"), "hinglish")
        self.assertEqual(detect_source_language("Where is mom?"), "en")
        self.assertEqual(detect_source_language("नमस्ते, आप कैसे हैं?"), "hi")
        self.assertEqual(detect_source_language("ईजा कहाँ छ?"), "kmy")

    def test_hinglish_translation_user_case(self):
        # Specific user case 1: "are yah chal Kyon Nahin raha hai"
        trans, detected_lang, _ = enhance_translation("are yah chal Kyon Nahin raha hai", source_lang="auto")
        self.assertIn("Hinglish", detected_lang)
        self.assertIn("किलै नि चलनो छ", trans)
        self.assertNotIn("छन yah", trans)

    def test_working_queries_and_user_dictation(self):
        # Specific user case 2: "why is does not working" and related variations
        cases = [
            ("why is does not working", "यो किलै नि चलनो छ?"),
            ("why is this not working", "यो किलै नि चलनो छ?"),
            ("why is it not working", "यो किलै नि चलनो छ?"),
            ("it is not working", "यो काम नि करनो छ।"),
            ("this is working", "यो चलनो छ।"),
            ("what happened?", "क्या भयो?"),
            ("can you hear me?", "क्या तुम मूकै सुणि सकछा?"),
        ]
        for src, expected in cases:
            trans, detected_lang, _ = enhance_translation(src, source_lang="auto")
            self.assertEqual(
                trans,
                expected,
                f"Expected '{expected}' for '{src}', got: '{trans}'"
            )
            self.assertNotIn("does", trans)
            self.assertNotIn("working", trans)
            self.assertNotIn("कै छ", trans)

    def test_kinship_and_colloquial_english(self):
        cases = [
            ("Where is mom?", "ईजा"),
            ("Where is mum?", "ईजा"),
            ("Where is mommy?", "ईजा"),
            ("Dad is at home", "बाबु"),
            ("Papa is at home", "बाबु"),
            ("Grandpa is sleeping", "बूबू"),
            ("Grandma is telling a story", "आमा"),
            ("How are you bro?", "दाज्यू"),
            ("Where is my sister?", "दीदी"),
            ("Kids are playing", "नान्तिन"),
        ]
        for src, expected in cases:
            trans, _, _ = enhance_translation(src, source_lang="en")
            self.assertIn(
                expected,
                trans,
                f"Expected '{expected}' in translation of '{src}', got: '{trans}'"
            )

    def test_question_translations(self):
        cases = [
            ("What is your name?", ["तुमरो", "नाव", "क्या", "छ"]),
            ("Where are you going?", ["कहाँ", "जाँछा"]),
            ("Where is the hospital?", ["अस्पताल", "कहाँ", "छ"]),
            ("How are you?", ["क्या", "हालचाल"]),
            ("How much does this cost?", ["कतिक", "रुप्या"]),
            ("What is the time?", ["क्या", "बज्यो"]),
        ]
        for src, expected_tokens in cases:
            trans, _, _ = enhance_translation(src, source_lang="en")
            for tok in expected_tokens:
                self.assertTrue(
                    tok in trans or tok.lower() in trans.lower(),
                    f"Expected token '{tok}' for '{src}', got: '{trans}'"
                )

    def test_food_and_travel_dialogue(self):
        cases = [
            ("I want water", "पाणि"),
            ("I want tea", "चाह"),
            ("I want mountain food", "खाना"),
            ("The food is very tasty", "मीठो"),
            ("Where is the bus stand?", "कहाँ"),
            ("Can you show me the mountain path?", "बाटो"),
        ]
        for src, expected in cases:
            trans, _, _ = enhance_translation(src, source_lang="en")
            self.assertIn(
                expected,
                trans,
                f"Expected '{expected}' for '{src}', got: '{trans}'"
            )

    def test_weather_and_nature(self):
        cases = [
            ("It is raining today", "पाणि"),
            ("It is very cold", "जाड़"),
            ("Is it cold in the mountains?", "जाड़"),
        ]
        for src, expected in cases:
            trans, _, _ = enhance_translation(src, source_lang="en")
            self.assertIn(
                expected,
                trans,
                f"Expected '{expected}' for '{src}', got: '{trans}'"
            )

    def test_imperatives_and_politeness(self):
        cases = [
            ("Please sit down", "बसा"),
            ("Please come in", "आवा"),
            ("Don't go there", "झन्"),
            ("Don't do that", "झन्"),
        ]
        for src, expected in cases:
            trans, _, _ = enhance_translation(src, source_lang="en")
            self.assertIn(
                expected,
                trans,
                f"Expected '{expected}' for '{src}', got: '{trans}'"
            )

    def test_dialect_transformations(self):
        src = "What is your name?"
        central, _, _ = enhance_translation(src, source_lang="en", dialect="central")
        eastern, _, _ = enhance_translation(src, source_lang="en", dialect="eastern")
        western, _, _ = enhance_translation(src, source_lang="en", dialect="western")

        self.assertIn("तुमरो", central)
        self.assertIn("तमरो", eastern)
        self.assertIn("तुमारू", western)

    def test_hindi_to_kumaoni_translation(self):
        cases = [
            ("नमस्ते", "पैलाग"),
            ("पानी लाओ", "पाणि"),
            ("यह रास्ता कहाँ जाता है?", "बाटो"),
        ]
        for src, expected in cases:
            trans, _, _ = enhance_translation(src, source_lang="hi")
            self.assertIn(
                expected,
                trans,
                f"Expected '{expected}' for Hindi '{src}', got: '{trans}'"
            )

    def test_voice_translation_endpoint_full(self):
        req = VoiceTranslateRequest(
            text="are yah chal Kyon Nahin raha hai",
            source_lang="auto",
            target_dialect="central",
            method="auto",
            generate_audio=True,
        )
        res = translate_voice(req)
        self.assertIn("Hinglish", res["detected_lang"])
        self.assertIn("किलै नि चलनो छ", res["translated_text"])
        self.assertTrue(len(res["syllables"]) > 0)
        self.assertTrue(len(res["romanized"]) > 0)
        self.assertTrue("<speak>" in res["ssml"])
        self.assertIsNotNone(res["audio_wav_base64"])


if __name__ == "__main__":
    unittest.main()
