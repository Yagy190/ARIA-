"""
Aria.py
Direct entrypoint and backwards-compatible runner for ARIA.
Preserves the exact functional modular imports specified in the hackathon architecture:
- voice_interface
- maps_navigation
- society_inputs
- risk_engine
- vehicle_alerts
"""

import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from voice_interface import listen_to_user, speak_to_user
from maps_navigation import get_walking_route
from society_inputs import get_society_risk_alerts
from risk_engine import analyze_risks
from vehicle_alerts import send_vehicle_alert
from config import print_system_status, USER_LOCATION


def run_aria():
    """
    Executes the classic ARIA flow:
    1. Blind user speaks command
    2. Route fetched via Maps API / Pedestrian Router
    3. Step-by-step spoken navigation
    4. Society hazard detection
    5. Spoken warnings + Vehicle V2X safety alerts
    6. Arrival confirmation
    """
    print_system_status()

    # 1. Blind user speaks
    user_command = listen_to_user()
    if not user_command:
        user_command = "Navigate me to the nearest hospital"
    
    speak_to_user(f"Navigation started for: {user_command}")

    # 2. Define locations
    start = USER_LOCATION
    destination = "Mount Sinai West Hospital"

    # 3. Get walking route
    route = get_walking_route(start, destination)

    # 4. Process each step
    for step_num, step in enumerate(route, 1):
        speak_to_user(f"Step {step_num}: {step}")

        # 5. Get society alerts near current position
        society_alerts = get_society_risk_alerts(start)

        # 6. Analyze risks for this step
        risks = analyze_risks(step, society_alerts)

        # 7. Speak risks to blind user
        for risk in risks:
            speak_to_user(risk)

            # 8. Alert vehicles
            send_vehicle_alert(start, risk)

    speak_to_user("You have reached your destination safely. ARIA accessible navigation finished.")


if __name__ == "__main__":
    run_aria()
