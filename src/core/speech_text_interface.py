#!/usr/bin/env python3
"""Multi-language Speech-to-Text and Text-to-Speech integration for 3D Print CAD Assistant."""

import logging
import tempfile
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    import pyttsx3
    TEXT_TO_SPEECH_AVAILABLE = True
except ImportError:
    TEXT_TO_SPEECH_AVAILABLE = False

from .core.i18n_optimized import Language, I18nManager

class SpeechToTextManager:
    """Multi-language speech-to-text conversion with translation support."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        self.supported_languages = {
            'en': 'en-US',  # English (US)
            'ja': 'ja-JP',  # Japanese
            'es': 'es-ES',  # Spanish
            'fr': 'fr-FR',  # French
            'de': 'de-DE',  # German
            'it': 'it-IT',  # Italian
            'pt': 'pt-BR',  # Portuguese
            'ru': 'ru-RU',  # Russian
            'zh': 'zh-CN',  # Chinese (Mandarin)
            'ko': 'ko-KR',  # Korean
            'ar': 'ar-SA',  # Arabic
            'hi': 'hi-IN',  # Hindi
        }

    def is_available(self) -> bool:
        """Check if speech recognition is available."""
        return SPEECH_RECOGNITION_AVAILABLE and self.recognizer is not None

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for speech recognition."""
        return list(self.supported_languages.keys())

    def recognize_speech(self, language: Language = Language.EN, timeout: int = 5) -> Optional[str]:
        """Recognize speech from microphone."""
        if not self.is_available():
            self.logger.warning("Speech recognition not available")
            return None

        lang_code = self.supported_languages.get(language.value)
        if not lang_code:
            self.logger.warning(f"Speech recognition not supported for language: {language.value}")
            return None

        try:
            with sr.Microphone() as source:
                self.logger.info(f"Listening for speech in {language.value}...")

                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                # Listen for audio
                audio = self.recognizer.listen(source, timeout=timeout)

                # Recognize speech
                text = self.recognizer.recognize_google(audio, language=lang_code)
                self.logger.info(f"Recognized speech: {text}")
                return text

        except sr.UnknownValueError:
            self.logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            self.logger.error(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Speech recognition error: {e}")
            return None

    def recognize_from_file(self, audio_file: Path, language: Language = Language.EN) -> Optional[str]:
        """Recognize speech from audio file."""
        if not self.is_available():
            self.logger.warning("Speech recognition not available")
            return None

        lang_code = self.supported_languages.get(language.value)
        if not lang_code:
            self.logger.warning(f"Speech recognition not supported for language: {language.value}")
            return None

        try:
            with sr.AudioFile(str(audio_file)) as source:
                audio = self.recognizer.record(source)

                # Recognize speech
                text = self.recognizer.recognize_google(audio, language=lang_code)
                self.logger.info(f"Recognized speech from file: {text}")
                return text

        except Exception as e:
            self.logger.error(f"Speech recognition from file error: {e}")
            return None


class TextToSpeechManager:
    """Multi-language text-to-speech conversion."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.engine = pyttsx3.init() if TEXT_TO_SPEECH_AVAILABLE else None
        self.supported_languages = {
            'en': 'en',      # English
            'ja': 'ja',      # Japanese
            'es': 'es',      # Spanish
            'fr': 'fr',      # French
            'de': 'de',      # German
            'it': 'it',      # Italian
            'pt': 'pt',      # Portuguese
            'ru': 'ru',      # Russian
            'zh': 'zh',      # Chinese
            'ko': 'ko',      # Korean
        }

        if self.engine:
            # Configure voice properties
            self.engine.setProperty('rate', 150)    # Speaking rate
            self.engine.setProperty('volume', 0.9)  # Volume

    def is_available(self) -> bool:
        """Check if text-to-speech is available."""
        return TEXT_TO_SPEECH_AVAILABLE and self.engine is not None

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for text-to-speech."""
        return list(self.supported_languages.keys())

    def speak_text(self, text: str, language: Language = Language.EN) -> bool:
        """Convert text to speech."""
        if not self.is_available():
            self.logger.warning("Text-to-speech not available")
            return False

        lang_code = self.supported_languages.get(language.value)
        if not lang_code:
            self.logger.warning(f"Text-to-speech not supported for language: {language.value}")
            return False

        try:
            # Set language-specific voice if available
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if lang_code in voice.languages or language.value in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break

            self.engine.say(text)
            self.engine.runAndWait()
            return True

        except Exception as e:
            self.logger.error(f"Text-to-speech error: {e}")
            return False

    def save_to_file(self, text: str, output_file: Path, language: Language = Language.EN) -> bool:
        """Save text-to-speech audio to file."""
        if not self.is_available():
            self.logger.warning("Text-to-speech not available")
            return False

        lang_code = self.supported_languages.get(language.value)
        if not lang_code:
            self.logger.warning(f"Text-to-speech not supported for language: {language.value}")
            return False

        try:
            # Set language-specific voice if available
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if lang_code in voice.languages or language.value in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break

            # Save to file
            self.engine.save_to_file(text, str(output_file))
            self.engine.runAndWait()
            return True

        except Exception as e:
            self.logger.error(f"Save to file error: {e}")
            return False


class MultiLanguageInterface:
    """Unified interface for speech-to-text and text-to-speech with translation."""

    def __init__(self):
        self.speech_to_text = SpeechToTextManager()
        self.text_to_speech = TextToSpeechManager()
        self.i18n_manager = I18nManager()

    def translate_and_speak(self, text_key: str, target_language: Language = Language.EN, **kwargs) -> bool:
        """Translate text and speak it in the target language."""
        # Get translated text
        translated_text = self.i18n_manager.t(text_key, **kwargs)

        # Speak the translated text
        return self.text_to_speech.speak_text(translated_text, target_language)

    def listen_and_translate(self, source_language: Language = Language.EN, target_language: Language = Language.EN) -> Optional[str]:
        """Listen to speech, recognize it, and optionally translate."""
        # Recognize speech
        recognized_text = self.speech_to_text.recognize_speech(source_language)

        if not recognized_text:
            return None

        # If different language, translate the recognized text
        if source_language != target_language:
            # This would require integration with translation service
            # For now, return the recognized text as-is
            return recognized_text

        return recognized_text

    def get_interface_status(self) -> Dict[str, Any]:
        """Get status of speech/text interfaces."""
        return {
            "speech_to_text": {
                "available": self.speech_to_text.is_available(),
                "supported_languages": self.speech_to_text.get_supported_languages()
            },
            "text_to_speech": {
                "available": self.text_to_speech.is_available(),
                "supported_languages": self.text_to_speech.get_supported_languages()
            },
            "current_language": self.i18n_manager.get_language().value
        }
