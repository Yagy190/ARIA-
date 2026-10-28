"""
config.py
Configuration loader and settings for ARIA (Accessible Routing & Intelligent Alerts).
Supports environment variables (.env), key validation, and default fallback values.
"""

import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Try loading .env file from current or parent directories
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# ==============================================================
# API Keys (Set in .env or system environment)
# ==============================================================
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()
FIREBASE_SERVER_KEY = os.getenv("FIREBASE_SERVER_KEY", "").strip()

# ==============================================================
# Navigation & Geolocation Settings
# ==============================================================
# Default test location: Central Manhattan, NYC (Broadway / 42nd St)
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "40.7580"))
DEFAULT_LNG = float(os.getenv("DEFAULT_LNG", "-73.9855"))

USER_LOCATION = {
    "lat": DEFAULT_LAT,
    "lng": DEFAULT_LNG,
    "address_hint": "Broadway & W 42nd St, New York, NY"
}

# Search radius for hazards near walking route (in meters)
HAZARD_DETECTION_RADIUS_METERS = 150.0

# Critical danger threshold where vehicle warnings must be dispatched
VEHICLE_ALERT_THRESHOLD = "high"  # alerts on 'high' and 'critical'

# ==============================================================
# Audio & Voice Settings
# ==============================================================
VOICE_MODE = os.getenv("VOICE_MODE", "auto").lower()  # 'microphone', 'text', 'auto'
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3").lower()  # 'pyttsx3', 'gemini', 'console'
SPEECH_RATE = int(os.getenv("SPEECH_RATE", "175"))  # Words per minute for pyttsx3
SPEECH_VOLUME = float(os.getenv("SPEECH_VOLUME", "1.0"))  # 0.0 to 1.0


def has_valid_maps_key() -> bool:
    """Returns True if Google Maps API key is configured with a non-placeholder value."""
    return bool(GOOGLE_MAPS_API_KEY and not GOOGLE_MAPS_API_KEY.startswith("YOUR_"))


def has_valid_gemini_key() -> bool:
    """Returns True if Gemini API key is configured with a non-placeholder value."""
    return bool(GEMINI_API_KEY and not GEMINI_API_KEY.startswith("YOUR_"))


def has_valid_firebase_key() -> bool:
    """Returns True if Firebase server key is configured with a non-placeholder value."""
    return bool(FIREBASE_SERVER_KEY and not FIREBASE_SERVER_KEY.startswith("YOUR_"))


def print_system_status():
    """Prints a clear summary of system integrations and active modes."""
    print("=" * 65)
    print(" 🦾 ARIA: Accessible Routing & Intelligent Alerts")
    print("=" * 65)
    print(f" [Maps Navigation]  : {'Google Maps API (Live)' if has_valid_maps_key() else 'Autonomous Smart Fallback (OSM / Mock Route)'}")
    print(f" [Gemini AI Engine] : {'Gemini 3.8 / 2.5 Flash (Live)' if has_valid_gemini_key() else 'Autonomous Assistive NLP Fallback'}")
    print(f" [Vehicle V2X / FCM]: {'Firebase FCM (Live)' if has_valid_firebase_key() else 'Simulated Local V2X Broadcast Queue'}")
    print(f" [Current Location] : {USER_LOCATION['lat']:.4f}, {USER_LOCATION['lng']:.4f} ({USER_LOCATION['address_hint']})")
    print(f" [Voice Mode]       : {VOICE_MODE.upper()}")
    print("=" * 65)
