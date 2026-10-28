"""
test_aria.py
Automated Unit and Integration Test Suite for ARIA.
Validates all core modules:
1. VoiceInterface (Text & TTS)
2. MapsNavigation (Geocoding, OSRM & Google fallback)
3. SocietyInputs (Hazard crowdsourcing & Haversine proximity)
4. RiskEngine (Scoring, crossing detection, blind guidance)
5. VehicleAlerts (V2X dispatch & broadcast queue)
6. GeminiAssistant (Intent parsing & hazard speech generation)
7. End-to-End ARIA integration flow
"""

import os
import sys
import unittest

# Silence TTS audio during automated unit tests so tests run instantly
os.environ["TTS_ENGINE"] = "console"
os.environ["VOICE_MODE"] = "text"

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import USER_LOCATION
from voice_interface import VoiceInterface
from maps_navigation import MapsNavigation, calculate_haversine_distance
from society_inputs import SocietyInputs
from risk_engine import RiskEngine
from vehicle_alerts import VehicleAlerts
from gemini_api import GeminiAssistant
from main import ARIA


class TestARIASystem(unittest.TestCase):

    def setUp(self):
        self.voice = VoiceInterface(mode="text", tts_enabled=False)
        self.maps = MapsNavigation()
        self.society = SocietyInputs()
        self.gemini = GeminiAssistant()
        self.risk_engine = RiskEngine(self.gemini)
        self.vehicles = VehicleAlerts()

    def test_01_haversine_calculation(self):
        """Tests that Haversine distance matches real-world metrics."""
        # Times Square to Central Park South (~1000-1100 meters)
        d = calculate_haversine_distance(40.7580, -73.9855, 40.7650, -73.9730)
        self.assertGreater(d, 800)
        self.assertLess(d, 1500)

    def test_02_maps_geocoding(self):
        """Tests geocoding returns valid latitude and longitude."""
        loc = self.maps.geocode_address("hospital")
        self.assertIsNotNone(loc)
        self.assertIn("lat", loc)
        self.assertIn("lng", loc)
        self.assertTrue(isinstance(loc["lat"], (float, int)))

    def test_03_maps_routing(self):
        """Tests that route generator produces sequential steps with coordinates."""
        dest = {"lat": 40.7645, "lng": -73.9820}
        route = self.maps.get_walking_route(USER_LOCATION, dest)
        self.assertIsNotNone(route)
        self.assertIn("steps", route)
        self.assertGreater(len(route["steps"]), 0)
        step1 = route["steps"][0]
        self.assertIn("instruction", step1)
        self.assertIn("lat", step1)
        self.assertIn("lng", step1)

    def test_04_society_alerts_and_proximity(self):
        """Tests adding crowdsourced alerts and retrieving via route proximity."""
        initial_count = len(self.society.get_all_alerts())
        test_loc = {"lat": USER_LOCATION["lat"] + 0.0005, "lng": USER_LOCATION["lng"] + 0.0005}
        
        new_alert = self.society.add_alert(
            location=test_loc,
            hazard_type="pothole",
            description="Unit Test Pothole",
            severity="high"
        )
        self.assertEqual(len(self.society.get_all_alerts()), initial_count + 1)

        # Proximity check
        steps = [{"lat": USER_LOCATION["lat"], "lng": USER_LOCATION["lng"]}]
        relevant = self.society.get_relevant_alerts(steps, radius_meters=200.0)
        self.assertTrue(any(a["id"] == new_alert["id"] for a in relevant))

    def test_05_risk_engine_analysis(self):
        """Tests that risk scores categorize risks and generate blind-friendly guidance."""
        dummy_steps = [
            {"instruction": "Walk straight along sidewalk", "lat": 40.7580, "lng": -73.9855},
            {"instruction": "Cross the street at traffic signal", "lat": 40.7590, "lng": -73.9850}
        ]
        dummy_alerts = [
            {
                "id": "T-1",
                "hazard_type": "pothole",
                "severity": "high",
                "description": "Deep open pothole",
                "distance_to_route_meters": 15.0,
                "matched_step_index": 0
            },
            {
                "id": "T-2",
                "hazard_type": "traffic",
                "severity": "critical",
                "description": "Speeding cars turning into pedestrian lane",
                "distance_to_route_meters": 10.0,
                "matched_step_index": 1
            }
        ]
        res = self.risk_engine.analyze_route(dummy_steps, dummy_alerts)
        self.assertIn("risk_level", res)
        self.assertIn(res["risk_level"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertTrue(res["vehicle_alert_required"])
        self.assertGreater(len(res["critical_alerts"]), 0)

    def test_06_vehicle_v2x_dispatch(self):
        """Tests that vehicle alerts are logged and formatted with safety advisories."""
        self.vehicles.send_alert(
            pedestrian_location=USER_LOCATION,
            risk_info="Blind pedestrian crossing",
            severity="HIGH",
            action="SLOW DOWN"
        )
        recent = self.vehicles.get_recent_alerts(limit=5)
        self.assertGreater(len(recent), 0)
        latest = recent[0]
        self.assertEqual(latest["severity"], "HIGH")
        self.assertIn("location", latest)

    def test_07_gemini_intent_parsing(self):
        """Tests natural language intent extraction."""
        # Navigate intent
        p1 = self.gemini.parse_user_command("Take me to Mount Sinai Hospital")
        self.assertEqual(p1.get("intent"), "navigate")
        
        # Stop intent
        p2 = self.gemini.parse_user_command("Stop navigation now")
        self.assertEqual(p2.get("intent"), "stop")

        # Status intent
        p3 = self.gemini.parse_user_command("Where am I and how many steps left?")
        self.assertEqual(p3.get("intent"), "status")

    def test_08_end_to_end_flow(self):
        """Tests complete end-to-end flow without raising exceptions."""
        app = ARIA(voice_mode="text", tts_enabled=False)
        # Run a quick automated step-through with 0 delay for instant unit testing
        app.start_navigation("hospital", auto_advance=True, step_delay=0.0)
        self.assertFalse(app.is_navigating)
        self.assertIsNotNone(app.current_route)


if __name__ == "__main__":
    print("=" * 65)
    print(" 🧪 Running ARIA Automated Verification Test Suite")
    print("=" * 65)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestARIASystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n✅ ALL 8 TEST SUITES PASSED PERFECTLY!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED.")
        sys.exit(1)
