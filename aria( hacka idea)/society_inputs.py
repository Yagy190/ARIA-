"""
society_inputs.py
Collects, aggregates, and retrieves crowdsourced hazard alerts from nearby people.
Blind pedestrians are vulnerable to dynamic micro-hazards like open potholes,
construction scaffolding, and sudden crowds that static maps do not display.
"""

import json
import random
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from maps_navigation import calculate_haversine_distance
from config import HAZARD_DETECTION_RADIUS_METERS, USER_LOCATION


class SocietyInputs:
    """
    Manages crowdsourced safety alerts submitted by community members,
    pedestrians, and urban monitors.
    """

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = Path(data_file or (Path(__file__).resolve().parent / "society_alerts.json"))
        self._lock = threading.Lock()
        self.alerts: List[Dict[str, Any]] = []

        if self.data_file.exists():
            self.load_from_disk()
        else:
            self.populate_default_alerts()

    def populate_default_alerts(self):
        """Seeds realistic community hazard reports situated in the operational test area."""
        base_lat = USER_LOCATION["lat"]
        base_lng = USER_LOCATION["lng"]

        sample_alerts = [
            {
                "id": "ALT-101",
                "hazard_type": "pothole",
                "severity": "high",
                "description": "Deep open pothole on the pedestrian crosswalk near curb",
                "location": {"lat": base_lat + 0.0012, "lng": base_lng + 0.0006},
                "reported_by": "Nearby Citizen (SafeWalk App)",
                "timestamp": datetime.now().isoformat(),
                "upvotes": 5
            },
            {
                "id": "ALT-102",
                "hazard_type": "construction",
                "severity": "high",
                "description": "Metal scaffolding extending into sidewalk, low hanging pipe",
                "location": {"lat": base_lat + 0.0028, "lng": base_lng + 0.0014},
                "reported_by": "Store Merchant",
                "timestamp": datetime.now().isoformat(),
                "upvotes": 12
            },
            {
                "id": "ALT-103",
                "hazard_type": "crowd",
                "severity": "medium",
                "description": "Large gathering and queue blocking subway entrance sidewalk",
                "location": {"lat": base_lat + 0.0019, "lng": base_lng + 0.0010},
                "reported_by": "Pedestrian Volunteer",
                "timestamp": datetime.now().isoformat(),
                "upvotes": 3
            },
            {
                "id": "ALT-104",
                "hazard_type": "obstacle",
                "severity": "critical",
                "description": "Electric delivery scooter discarded horizontally across tactile path",
                "location": {"lat": base_lat + 0.0038, "lng": base_lng + 0.0019},
                "reported_by": "ARIA Community Member",
                "timestamp": datetime.now().isoformat(),
                "upvotes": 8
            },
            {
                "id": "ALT-105",
                "hazard_type": "traffic",
                "severity": "high",
                "description": "Traffic signal acoustic chirper malfunctioning, heavy turning vehicles",
                "location": {"lat": base_lat + 0.0021, "lng": base_lng + 0.0008},
                "reported_by": "Traffic Warden",
                "timestamp": datetime.now().isoformat(),
                "upvotes": 7
            }
        ]

        with self._lock:
            self.alerts = sample_alerts
        self.save_to_disk()

    def add_alert(self, location: Dict[str, float], hazard_type: str, description: str,
                  severity: str = "medium", reported_by: str = "Community User") -> Dict[str, Any]:
        """
        Adds a new crowdsourced hazard report and persists it.
        """
        alert = {
            "id": f"ALT-{random.randint(1000, 9999)}",
            "hazard_type": hazard_type.lower(),
            "severity": severity.lower(),
            "description": description,
            "location": {"lat": location["lat"], "lng": location["lng"]},
            "reported_by": reported_by,
            "timestamp": datetime.now().isoformat(),
            "upvotes": 1
        }
        with self._lock:
            self.alerts.append(alert)
        self.save_to_disk()
        print(f"📱 [SOCIETY INPUT RECORDED]: {severity.upper()} {hazard_type} - '{description}'")
        return alert

    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Returns snapshot of all registered alerts."""
        with self._lock:
            return list(self.alerts)

    def get_relevant_alerts(self, route_steps: List[Dict[str, Any]],
                            radius_meters: float = HAZARD_DETECTION_RADIUS_METERS) -> List[Dict[str, Any]]:
        """
        Identifies hazards located within radius_meters of any point along the walking route.
        Attaches the closest distance and step index to each match.
        """
        relevant = []
        with self._lock:
            current_alerts = list(self.alerts)

        for alert in current_alerts:
            a_lat = alert["location"]["lat"]
            a_lng = alert["location"]["lng"]

            closest_distance = float("inf")
            matched_step_idx = -1

            for idx, step in enumerate(route_steps):
                # Check distance to start point
                d1 = calculate_haversine_distance(step["lat"], step["lng"], a_lat, a_lng)
                # Check distance to end point if available
                end_lat = step.get("end_lat", step["lat"])
                end_lng = step.get("end_lng", step["lng"])
                d2 = calculate_haversine_distance(end_lat, end_lng, a_lat, a_lng)

                min_step_dist = min(d1, d2)
                if min_step_dist < closest_distance:
                    closest_distance = min_step_dist
                    matched_step_idx = idx

            if closest_distance <= radius_meters:
                # Create a match record with spatial metadata
                item = dict(alert)
                item["distance_to_route_meters"] = round(closest_distance, 1)
                item["matched_step_index"] = matched_step_idx
                relevant.append(item)

        # Sort by distance
        relevant.sort(key=lambda x: x["distance_to_route_meters"])
        return relevant

    def simulate_society_inputs(self):
        """Simulates incoming real-time alerts from local citizens during navigation."""
        hazards = [
            ("pothole", "Sidewalk concrete cracked, uneven surface", "medium"),
            ("construction", "Workers unloading scaffolding poles on sidewalk", "high"),
            ("crowd", "Sudden surge of commuters exiting station", "medium"),
            ("obstacle", "Wet floor with caution cones near building entrance", "low"),
            ("traffic", "Delivery van double parked blocking pedestrian sightline", "high")
        ]
        hazard_type, desc, severity = random.choice(hazards)
        loc = {
            "lat": USER_LOCATION["lat"] + random.uniform(0.0005, 0.0030),
            "lng": USER_LOCATION["lng"] + random.uniform(0.0003, 0.0020)
        }
        self.add_alert(loc, hazard_type, desc, severity, reported_by="Simulated Urban Sensor")

    def save_to_disk(self):
        """Saves alerts to JSON file."""
        try:
            with self._lock:
                data = self.alerts
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save society alerts to disk: {e}")

    def load_from_disk(self):
        """Loads alerts from JSON file."""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self.alerts = data
        except Exception:
            self.populate_default_alerts()


# Global default instance
default_society = SocietyInputs()

def get_society_risk_alerts(current_location):
    """Backwards-compatible wrapper matching original project spec."""
    all_alerts = default_society.get_all_alerts()
    return [
        {
            "type": a["hazard_type"],
            "severity": a["severity"],
            "message": a["description"]
        }
        for a in all_alerts
    ]
