"""
gemini_api.py
Google Gemini AI integration for ARIA.
Provides intent understanding, spatial hazard rephrasing for visually impaired users,
and conversational assistance with autonomous fallback.
"""

import json
import re
from typing import Dict, Any, Optional
from config import GEMINI_API_KEY, has_valid_gemini_key

# Attempt to load the official google-genai SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiAssistant:
    """
    Integrates Gemini AI for natural language parsing, conversational routing,
    and adaptive spatial descriptions for blind and visually impaired users.
    """

    def __init__(self):
        self.client = None
        self.model_name = "gemini-3.8-flash"  # Current Google Gemini standard
        self.is_active = False

        if GENAI_AVAILABLE and has_valid_gemini_key():
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                self.is_active = True
                print("✨ Gemini API initialized successfully (Model: gemini-3.8-flash).")
            except Exception as e:
                print(f"⚠️ Could not initialize Gemini API: {e}. Falling back to rule-based engine.")
                self.is_active = False
        else:
            self.is_active = False

    def parse_user_command(self, user_text: str) -> Dict[str, Any]:
        """
        Parses user's spoken voice command to extract intent and destination.
        Returns a dict: {"intent": "navigate"|"stop"|"status"|"help"|"report", "destination": str, "details": str}
        """
        if not user_text:
            return {"intent": "unknown", "destination": "", "details": ""}

        user_text = user_text.strip()

        # If Gemini is active, use generative intent parsing
        if self.is_active and self.client:
            try:
                prompt = (
                    "You are the intent parser for ARIA, an assistive navigation system for blind users.\n"
                    f"User voice input: \"{user_text}\"\n"
                    "Extract the intent and return ONLY a valid JSON object with keys:\n"
                    "- intent: one of ['navigate', 'stop', 'status', 'help', 'report_hazard', 'repeat', 'unknown']\n"
                    "- destination: name or place if navigating (e.g. 'hospital', 'starbucks', 'home'), else ''\n"
                    "- hazard_type: if reporting hazard ('pothole', 'construction', 'crowd', 'obstacle'), else ''\n"
                    "- summary: brief 1-sentence friendly confirmation message for speech"
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                text = response.text.strip()
                # Clean code blocks if present
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(text)
                return parsed
            except Exception as e:
                # Fallback on any API issue
                pass

        # Rule-based fallback parsing
        text_lower = user_text.lower()

        if any(w in text_lower for w in ["stop", "cancel", "end route", "quit", "halt"]):
            return {"intent": "stop", "destination": "", "summary": "Navigation stopped."}

        if any(w in text_lower for w in ["where am i", "status", "how far", "remaining", "steps left"]):
            return {"intent": "status", "destination": "", "summary": "Checking route status."}

        if any(w in text_lower for w in ["help", "what can you do", "commands"]):
            return {"intent": "help", "destination": "", "summary": "Here are the commands you can say."}

        if any(w in text_lower for w in ["repeat", "say again", "what did you say"]):
            return {"intent": "repeat", "destination": "", "summary": "Repeating last instruction."}

        # Check navigation commands
        nav_triggers = ["navigate me to", "navigate to", "take me to", "go to", "walk to", "route to", "find nearest", "find the nearest", "find"]
        destination = ""
        for trigger in nav_triggers:
            if trigger in text_lower:
                idx = text_lower.find(trigger) + len(trigger)
                destination = user_text[idx:].strip().strip(".!?,")
                break

        if not destination and any(kw in text_lower for kw in ["hospital", "pharmacy", "doctor", "store", "park", "home", "station"]):
            for kw in ["hospital", "pharmacy", "doctor", "store", "park", "home", "station"]:
                if kw in text_lower:
                    destination = f"nearest {kw}"
                    break

        if destination:
            return {
                "intent": "navigate",
                "destination": destination,
                "summary": f"Starting navigation to {destination}."
            }

        return {
            "intent": "navigate",
            "destination": user_text,
            "summary": f"Searching route for {user_text}."
        }

    def generate_blind_friendly_hazard_alert(self, hazard: Dict[str, Any], distance_meters: float, step_instruction: str) -> str:
        """
        Translates a technical hazard detection into an actionable, spatial,
        clear audio warning suitable for a visually impaired pedestrian using a cane or guide dog.
        """
        hazard_type = hazard.get("hazard_type", "hazard")
        desc = hazard.get("description", "hazard ahead")
        severity = hazard.get("severity", "medium").lower()

        # Approximate human paces (approx 0.75m per pace)
        paces = max(1, int(distance_meters / 0.75))

        if self.is_active and self.client:
            try:
                prompt = (
                    "You are ARIA, an assistive audio guide for a blind pedestrian.\n"
                    f"Hazard detected: {hazard_type} ({desc}).\n"
                    f"Severity: {severity}.\n"
                    f"Distance ahead: {int(distance_meters)} meters (approx {paces} paces).\n"
                    f"Current route instruction: {step_instruction}.\n\n"
                    "Generate a concise, calm, high-clarity voice alert (under 25 words). "
                    "Instruct the user on physical action (e.g. 'keep left', 'sweep cane carefully', 'slow down', 'listen for machinery'). "
                    "Do NOT use visual-only descriptions (like 'look out' or 'see that color'). Output plain text only."
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                text = response.text.strip().replace("\n", " ")
                if text:
                    return text
            except Exception:
                pass

        # Offline / Fallback templates
        urgency = "Caution" if severity in ["low", "medium"] else "Urgent Warning"
        if hazard_type == "pothole":
            return f"{urgency}: Pothole reported approximately {paces} paces ahead. Keep to the right side of the sidewalk and sweep your cane forward."
        elif hazard_type == "construction":
            return f"{urgency}: Construction zone in {paces} paces. Reduce speed and listen for workers and barriers."
        elif hazard_type == "crowd":
            return f"{urgency}: Heavy pedestrian congestion ahead in {paces} paces. Maintain a steady pace on the right edge."
        elif hazard_type == "obstacle":
            return f"{urgency}: Obstacle on the path in {paces} paces: {desc}. Tap ahead with your cane before stepping."
        elif hazard_type == "traffic":
            return f"{urgency}: Active vehicular traffic crossing ahead. Stop at the curb and wait for tactile signal."
        else:
            return f"{urgency}: {desc} detected {paces} paces ahead. Proceed with care."
