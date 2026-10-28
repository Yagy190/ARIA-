"""
risk_engine.py
Analyzes walking routes and society alerts to detect pedestrian dangers.
Computes risk scores, assesses crossing hazards, generates tailored voice warnings,
and determines when surrounding vehicles must be notified.
"""

from typing import List, Dict, Any, Optional
from gemini_api import GeminiAssistant


class RiskEngine:
    """
    Intelligent Risk Engine designed specifically for visually impaired navigation.
    Evaluates micro-hazards, intersection vulnerability, and generates tactile/audio guidance.
    """

    def __init__(self, gemini_assistant: Optional[GeminiAssistant] = None):
        self.gemini = gemini_assistant or GeminiAssistant()

        # Severity point weights
        self.severity_weights = {
            "low": 3,
            "medium": 6,
            "high": 9,
            "critical": 12
        }

        # Hazard type base severity weights
        self.hazard_type_weights = {
            "pothole": 8,
            "construction": 7,
            "obstacle": 9,
            "traffic": 10,
            "crowd": 5,
            "wet_floor": 4
        }

    def analyze_route(self, route_steps: List[Dict[str, Any]],
                      society_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Comprehensive multi-step risk assessment across the entire path.
        """
        step_evaluations = []
        total_risk_score = 0
        critical_alerts_found = []

        for idx, step in enumerate(route_steps):
            step_instruction = step.get("instruction", "")
            is_crossing = any(w in step_instruction.lower() for w in ["cross", "intersection", "turn", "signal", "traffic"])

            # Find alerts matching this step or nearby
            step_alerts = [a for a in society_alerts if a.get("matched_step_index") == idx]

            # If no step index matched, consider nearby distance
            if not step_alerts and society_alerts:
                # Distribute alerts that are along the journey
                step_alerts = [a for a in society_alerts if a.get("distance_to_route_meters", 999) < 80][:2]

            evaluated_risks = []
            for alert in step_alerts:
                severity = alert.get("severity", "medium").lower()
                h_type = alert.get("hazard_type", "obstacle").lower()
                dist = alert.get("distance_to_route_meters", 30.0)

                # Base score
                base_score = self.hazard_type_weights.get(h_type, 6)
                sev_score = self.severity_weights.get(severity, 6)

                # Distance multiplier: closer means more immediate threat
                if dist < 25:
                    dist_mult = 1.4
                elif dist < 60:
                    dist_mult = 1.0
                else:
                    dist_mult = 0.6

                # Crossing multiplier
                crossing_mult = 1.3 if is_crossing else 1.0

                score = int((base_score + sev_score) * dist_mult * crossing_mult / 2.0)
                total_risk_score += score

                # Generate high-clarity spoken audio warning
                warning_message = self.gemini.generate_blind_friendly_hazard_alert(
                    hazard=alert,
                    distance_meters=dist,
                    step_instruction=step_instruction
                )

                risk_record = {
                    "alert_id": alert.get("id"),
                    "hazard_type": h_type,
                    "severity": severity,
                    "description": alert.get("description"),
                    "distance_meters": dist,
                    "risk_score": score,
                    "warning_speech": warning_message,
                    "requires_vehicle_alert": severity in ["high", "critical"] or is_crossing
                }

                evaluated_risks.append(risk_record)
                if risk_record["requires_vehicle_alert"]:
                    critical_alerts_found.append(risk_record)

            if evaluated_risks:
                step_evaluations.append({
                    "step_index": idx,
                    "instruction": step_instruction,
                    "is_crossing": is_crossing,
                    "risks": evaluated_risks
                })

        # Overall level categorization
        if total_risk_score < 12:
            risk_level = "LOW"
        elif total_risk_score < 28:
            risk_level = "MEDIUM"
        elif total_risk_score < 45:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        return {
            "risk_level": risk_level,
            "total_risk_score": total_risk_score,
            "step_evaluations": step_evaluations,
            "critical_alerts": critical_alerts_found,
            "safe_to_proceed": risk_level != "CRITICAL",
            "vehicle_alert_required": len(critical_alerts_found) > 0 or risk_level in ["HIGH", "CRITICAL"]
        }


# Global default instance
default_risk_engine = RiskEngine()

def analyze_risks(route_step, society_alerts):
    """Backwards-compatible wrapper matching original project spec."""
    step_obj = {"instruction": str(route_step), "lat": 40.7580, "lng": -73.9855}
    alerts_objs = []
    for a in society_alerts:
        if isinstance(a, dict):
            alerts_objs.append({
                "hazard_type": a.get("type", a.get("hazard_type", "hazard")),
                "severity": a.get("severity", "medium"),
                "description": a.get("message", a.get("description", "Hazard ahead")),
                "distance_to_route_meters": 20.0,
                "matched_step_index": 0
            })
    
    analysis = default_risk_engine.analyze_route([step_obj], alerts_objs)
    warnings = []
    for step_eval in analysis["step_evaluations"]:
        for r in step_eval["risks"]:
            warnings.append(r["warning_speech"])
    return warnings
