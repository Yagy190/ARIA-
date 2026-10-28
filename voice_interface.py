"""
voice_interface.py
Voice Interface for ARIA.
Provides Speech-to-Text (STT) and Text-to-Speech (TTS) for blind users.
Features pyttsx3 offline speech synthesis, speech_recognition microphone input,
and graceful console fallback for automated or non-microphone environments.
"""

import sys
import time
import threading
from typing import Optional, Callable
from config import VOICE_MODE, TTS_ENGINE, SPEECH_RATE, SPEECH_VOLUME

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Speech Recognition library
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

# Local Text-to-Speech library
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class VoiceInterface:
    """
    Handles all accessibility voice interactions.
    Because blind users rely completely on audio, reliability, clarity,
    and instantaneous fallback are primary design goals.
    """

    def __init__(self, mode: Optional[str] = None, tts_enabled: bool = True):
        self.mode = (mode or VOICE_MODE).lower()
        self.tts_enabled = tts_enabled and (TTS_ENGINE != "console")
        self.tts_engine = None
        self.recognizer = None
        self.microphone = None
        self.mic_working = False
        self._lock = threading.Lock()

        # Initialize TTS Engine if enabled
        if PYTTSX3_AVAILABLE and self.tts_enabled:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", SPEECH_RATE)
                self.tts_engine.setProperty("volume", SPEECH_VOLUME)
                
                # Pick a natural voice if available
                voices = self.tts_engine.getProperty("voices")
                if voices:
                    for v in voices:
                        if "zira" in v.name.lower() or "david" in v.name.lower() or "english" in v.name.lower():
                            self.tts_engine.setProperty("voice", v.id)
                            break
            except Exception as e:
                print(f"⚠️ PyTTSx3 initialization notice: {e}. Outputting text to console.")
                self.tts_engine = None

        # Initialize Speech Recognizer
        if SR_AVAILABLE and self.mode in ["microphone", "auto"]:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
                
                # Test microphone availability
                mics = sr.Microphone.list_microphone_names()
                if mics:
                    self.microphone = sr.Microphone()
                    self.mic_working = True
                else:
                    self.mic_working = False
            except Exception:
                self.mic_working = False
        else:
            self.mic_working = False

    def speak(self, text: str, block: bool = True):
        """
        Converts text to spoken audio and displays it cleanly in terminal.
        """
        if not text:
            return

        # Visual accessibility display
        print(f"\n🔊 [ARIA VOICE]: {text}")

        # Spoken audio via TTS engine
        if self.tts_engine:
            def _say():
                with self._lock:
                    try:
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                    except Exception:
                        pass

            if block:
                _say()
            else:
                thread = threading.Thread(target=_say, daemon=True)
                thread.start()

    def listen(self, prompt: str = "Listening for your command...", timeout: int = 6) -> str:
        """
        Listens to user's voice command.
        Uses microphone if available; falls back to console if silent or timed out.
        """
        if self.mode == "text" or not self.mic_working:
            return self._listen_text(prompt)

        # Attempt microphone input
        try:
            print(f"\n🎙️  {prompt} (Speak now into your microphone)...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=8)

            print("⏳ Transcribing speech...")
            transcription = self.recognizer.recognize_google(audio)
            print(f"👤 [YOU SPOKE]: \"{transcription}\"")
            return transcription.strip()
        except sr.WaitTimeoutError:
            print("⏱️ (No speech detected on microphone)")
            # Offer immediate typed fallback so program never hangs
            return self._listen_text("Type command (or press Enter to try voice again)")
        except sr.UnknownValueError:
            print("❓ (Could not understand speech audio)")
            return self._listen_text("Type command")
        except Exception as e:
            print(f"ℹ️ Microphone notice: {e}")
            return self._listen_text(prompt)

    def _listen_text(self, prompt: str) -> str:
        """Fallback method to allow typing commands when microphone is unavailable or silent."""
        try:
            val = input(f"👤 [ARIA INPUT] {prompt} > ")
            return val.strip()
        except (EOFError, KeyboardInterrupt):
            return "stop"

    def continuous_listen(self, callback: Callable[[str], None], stop_event: threading.Event):
        """Background continuous listening loop."""
        while not stop_event.is_set():
            command = self.listen(timeout=5)
            if command:
                callback(command)
            time.sleep(0.5)


# Global default instance
default_voice = VoiceInterface()

def speak_to_user(message: str):
    """Convenience functional helper."""
    default_voice.speak(message)

def listen_to_user() -> str:
    """Convenience functional helper."""
    return default_voice.listen()
