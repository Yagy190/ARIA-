"""
aria_layer.py
ARIA Accessibility & Safety Intelligence Layer (Middleware / Overlay SDK).

ARIA is NOT a standalone navigation app. It is a universal, pluggable intelligence
layer that sits inside or on top of any existing mapping and navigation system
(such as Google Maps, Apple Maps, Mapbox, or OEM Navigation SDKs).

Responsibilities of the ARIA Layer:
1. Intercepts raw route streams from Google Maps.
2. Overlays dynamic crowdsourced micro-hazards (potholes, scaffolding, crowds)
   that standard map providers do not track.
3. Rephrases visual navigation instructions into tactile, cane-aware guidance.
4. Dispatches real-time V2X pedestrian alerts to nearby connected vehicles.
"""

import sys
import time
from typing import Dict, Any, List, Optional, Callable

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import USER_LOCATION, HAZARD_DETECTION_RADIUS_METERS
from maps_navigation import calculate_haversine_distance, clean_html_instructions
from society_inputs import SocietyInputs
from risk_engine import RiskEngine
from vehicle_alerts import VehicleAlerts
from gemini_api import GeminiAssistant
from voice_interface import VoiceInterface


class AriaLayer:
    """
    Universal Assistive Middleware Layer for Google Maps and mapping systems.
    Can be embedded into mobile navigation SDKs, web map viewers, or run as
    a background assistive daemon.
    """

    def __init__(self, voice_enabled: bool = True, tts_mode: str = "pyttsx3"):
        self.society = SocietyInputs()
        self.gemini = GeminiAssistant()
        self.risk_engine = RiskEngine(gemini_assistant=self.gemini)
        self.vehicles = VehicleAlerts()
        self.voice = VoiceInterface(mode="auto" if voice_enabled else "silent", 
                                   tts_enabled=(tts_mode != "console"))
        self.active_session_id = None
        self.alert_listeners: List[Callable[[Dict[str, Any]], None]] = []

    def register_alert_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Allows external systems (like vehicle HUDs or companion apps) to receive live layer events."""
        self.alert_listeners.append(callback)

    # =========================================================================
    # 1. ROUTE INTERCEPTION & ACCESSIBILITY AUGMENTATION
    # =========================================================================
    def augment_google_maps_route(self, google_maps_route: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intercepts a standard Google Maps Directions API response or route object,
        enriches each step with micro-hazard proximity, tactile guidance, and safety scores.
        """
        steps = google_maps_route.get("steps", [])
        if not steps and "legs" in google_maps_route:
            # Direct Google Maps API raw JSON format
            steps = []
            for leg in google_maps_route.get("legs", []):
                for s in leg.get("steps", []):
                    steps.append({
                        "instruction": clean_html_instructions(s.get("html_instructions", "")),
                        "distance": s.get("distance", {}).get("text", "0 m"),
                        "distance_meters": s.get("distance", {}).get("value", 0),
                        "duration": s.get("duration", {}).get("text", "0 min"),
                        "lat": s.get("start_location", {}).get("lat", 0.0),
                        "lng": s.get("start_location", {}).get("lng", 0.0),
                        "end_lat": s.get("end_location", {}).get("lat", 0.0),
                        "end_lng": s.get("end_location", {}).get("lng", 0.0),
                    })

        # 1. Fetch relevant society micro-hazards along this path
        relevant_hazards = self.society.get_relevant_alerts(steps, radius_meters=HAZARD_DETECTION_RADIUS_METERS)

        # 2. Run Risk Engine to compute danger score and guidance
        risk_summary = self.risk_engine.analyze_route(steps, relevant_hazards)

        # 3. Augment each step with blind-accessible spatial advisories
        augmented_steps = []
        for idx, step in enumerate(steps):
            aug_step = dict(step)
            # Find hazards tied to this step
            step_evals = [e for e in risk_summary.get("step_evaluations", []) if e.get("step_index") == idx]
            
            aug_step["micro_hazards"] = []
            tactile_warnings = []
            requires_vehicle_alert = False

            if step_evals:
                for r in step_evals[0].get("risks", []):
                    aug_step["micro_hazards"].append(r)
                    tactile_warnings.append(r["warning_speech"])
                    if r.get("requires_vehicle_alert"):
                        requires_vehicle_alert = True

            # Synthesize final spoken guidance for this step
            base_instruction = step.get("instruction", "")
            if tactile_warnings:
                aug_step["augmented_speech"] = f"{base_instruction}. { ' '.join(tactile_warnings) }"
            else:
                aug_step["augmented_speech"] = base_instruction

            aug_step["requires_vehicle_alert"] = requires_vehicle_alert
            augmented_steps.append(aug_step)

        return {
            "original_provider": google_maps_route.get("provider", "Google Maps"),
            "layer": "ARIA Assistive Intelligence Layer v1.0",
            "distance": google_maps_route.get("distance", "unknown"),
            "duration": google_maps_route.get("duration", "unknown"),
            "overall_risk_level": risk_summary["risk_level"],
            "total_risk_score": risk_summary["total_risk_score"],
            "safe_to_proceed": risk_summary["safe_to_proceed"],
            "vehicle_alert_required": risk_summary["vehicle_alert_required"],
            "hazards_detected_count": len(relevant_hazards),
            "augmented_steps": augmented_steps
        }

    # =========================================================================
    # 2. REAL-TIME GPS TELEMETRY INTERCEPTION (DURING ACTIVE WALKING)
    # =========================================================================
    def process_live_telemetry(self, current_lat: float, current_lng: float,
                               current_google_step: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invoked on every GPS coordinate update during active navigation inside Google Maps.
        Checks for dynamic hazards within 30 meters, generates immediate tactile cues,
        and broadcasts warnings to vehicles approaching this exact coordinate.
        """
        loc = {"lat": current_lat, "lng": current_lng}
        dummy_step = [{"lat": current_lat, "lng": current_lng}]

        # Check for immediate micro-hazards within 40m radius
        immediate_hazards = self.society.get_relevant_alerts(dummy_step, radius_meters=40.0)
        
        telemetry_event = {
            "timestamp": time.time(),
            "location": loc,
            "immediate_hazards_count": len(immediate_hazards),
            "spoken_advisory": None,
            "vehicle_alert_dispatched": False
        }

        if immediate_hazards:
            highest_hazard = immediate_hazards[0]
            dist = highest_hazard.get("distance_to_route_meters", 15.0)
            step_text = current_google_step.get("instruction", "walking") if current_google_step else "walking ahead"

            # Generate Gemini-powered accessible audio warning
            advisory = self.gemini.generate_blind_friendly_hazard_alert(
                hazard=highest_hazard,
                distance_meters=dist,
                step_instruction=step_text
            )
            telemetry_event["spoken_advisory"] = advisory

            # Speak directly to pedestrian
            self.voice.speak(advisory)

            # Check if vehicles need to be warned
            severity = highest_hazard.get("severity", "medium").lower()
            if severity in ["high", "critical"] or "cross" in step_text.lower():
                self.vehicles.send_alert(
                    pedestrian_location=loc,
                    risk_info=f"{highest_hazard.get('hazard_type', 'hazard').title()}: {highest_hazard.get('description')}",
                    severity=severity.upper(),
                    action="CAUTION: SLOW DOWN - BLIND PEDESTRIAN NAVIGATING IMMEDIATE HAZARD"
                )
                telemetry_event["vehicle_alert_dispatched"] = True

        # Notify any external listeners
        for listener in self.alert_listeners:
            try:
                listener(telemetry_event)
            except Exception:
                pass

        return telemetry_event

    # =========================================================================
    # 3. CROWDSOURCED HAZARD INJECTION
    # =========================================================================
    def report_hazard_to_layer(self, lat: float, lng: float, hazard_type: str,
                               description: str, severity: str = "medium",
                               reporter: str = "Connected Citizen") -> Dict[str, Any]:
        """Allows people, companion apps, or road sensors to inject live micro-hazards into the layer."""
        return self.society.add_alert(
            location={"lat": lat, "lng": lng},
            hazard_type=hazard_type,
            description=description,
            severity=severity,
            reported_by=reporter
        )
