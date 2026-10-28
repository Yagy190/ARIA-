"""
main.py
Main orchestrator and execution script for ARIA (Accessible Routing & Intelligent Alerts).
Coordinates Voice Interface, Google Maps Navigation, Society Hazard Inputs,
Risk Analysis Engine, and Vehicle V2X Dispatching into an end-to-end assistive experience.
"""

import sys
import time
import argparse
import subprocess
import threading
from typing import Optional, Dict, Any

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    USER_LOCATION,
    print_system_status,
    has_valid_maps_key,
    has_valid_gemini_key,
    has_valid_firebase_key
)
from voice_interface import VoiceInterface
from maps_navigation import MapsNavigation
from society_inputs import SocietyInputs
from risk_engine import RiskEngine
from vehicle_alerts import VehicleAlerts
from gemini_api import GeminiAssistant


class ARIA:
    """
    Main Assistive System Coordinator for Accessible Navigation.
    """

    def __init__(self, voice_mode: Optional[str] = None, tts_enabled: bool = True):
        self.voice = VoiceInterface(mode=voice_mode, tts_enabled=tts_enabled)
        self.gemini = GeminiAssistant()
        self.maps = MapsNavigation()
        self.society = SocietyInputs()
        self.risk_engine = RiskEngine(gemini_assistant=self.gemini)
        self.vehicles = VehicleAlerts()

        self.current_location = dict(USER_LOCATION)
        self.current_route: Optional[Dict[str, Any]] = None
        self.current_step_index = 0
        self.is_navigating = False

    def start_navigation(self, destination_query: str, auto_advance: bool = False, step_delay: float = 1.8):
        """
        Calculates walking route, analyzes micro-hazards along the route,
        notifies vehicles if risks exist, and guides the user step by step.
        """
        self.voice.speak(f"Starting accessible route search for '{destination_query}'.")

        # 1. Geocode destination
        dest_info = self.maps.geocode_address(destination_query)
        if not dest_info:
            self.voice.speak(f"Sorry, I could not pinpoint '{destination_query}'. Please try again with a landmark or street name.")
            return

        dest_name = dest_info.get("formatted_address", destination_query)
        self.voice.speak(f"Destination located: {dest_name[:60]}. Fetching walking route...")

        # 2. Get walking route (Google Maps API or OpenStreetMap Foot Routing)
        route = self.maps.get_walking_route(self.current_location, dest_info)
        if not route or not route.get("steps"):
            self.voice.speak("No safe walking route was found to that location.")
            return

        self.current_route = route
        self.current_step_index = 0
        self.is_navigating = True

        total_dist = route.get("distance", "few hundred meters")
        total_time = route.get("duration", "several minutes")
        steps = route["steps"]
        provider = route.get("provider", "ARIA Navigation Engine")

        self.voice.speak(
            f"Route ready via {provider}. Total distance is {total_dist}, estimated walk time {total_time}. "
            f"There are {len(steps)} guidance steps."
        )

        # 3. Society Hazard Assessment
        self.voice.speak("Scanning real-time crowdsourced safety hazards...")
        relevant_alerts = self.society.get_relevant_alerts(steps)

        risk_analysis = self.risk_engine.analyze_route(steps, relevant_alerts)
        risk_level = risk_analysis["risk_level"]

        if risk_level in ["MEDIUM", "HIGH", "CRITICAL"]:
            self.voice.speak(
                f"Attention: {risk_level} hazard level detected along this route. "
                "I will give you tactile and audio warnings before each risk."
            )
        else:
            self.voice.speak("Path is currently clear of severe micro-hazards.")

        # 4. Vehicle Safety Dispatch
        if risk_analysis.get("vehicle_alert_required"):
            self.voice.speak("Broadcasting pedestrian presence alert to surrounding vehicles.")
            first_alert_desc = "Blind pedestrian navigating with walking cane near active crossings"
            if risk_analysis["critical_alerts"]:
                first_alert_desc = risk_analysis["critical_alerts"][0]["description"]

            self.vehicles.send_alert(
                pedestrian_location=self.current_location,
                risk_info=f"{risk_level} risk: {first_alert_desc}",
                severity=risk_level,
                action="CAUTION: REDUCE SPEED - BLIND PEDESTRIAN CROSSING AHEAD"
            )

        # 5. Step-by-Step Walking Guidance
        self.guide_step_by_step(auto_advance=auto_advance, step_delay=step_delay)

    def guide_step_by_step(self, auto_advance: bool = False, step_delay: float = 1.8):
        """
        Iterates through route steps, delivering directional audio
        and timely hazard alerts for visually impaired users.
        """
        if not self.current_route:
            return

        steps = self.current_route["steps"]

        while self.is_navigating and self.current_step_index < len(steps):
            step = steps[self.current_step_index]
            step_num = self.current_step_index + 1
            total_steps = len(steps)

            # Announce Step Instruction
            instruction = step["instruction"]
            self.voice.speak(f"Step {step_num} of {total_steps}: {instruction}")

            # Check if this step has any associated hazards
            step_alerts = self.society.get_relevant_alerts([step], radius_meters=80.0)
            if step_alerts:
                step_risk_eval = self.risk_engine.analyze_route([step], step_alerts)
                for eval_item in step_risk_eval.get("step_evaluations", []):
                    for r in eval_item.get("risks", []):
                        # Speak tactile-aware guidance
                        self.voice.speak(r["warning_speech"])
                        # Notify vehicles at this specific coordinate
                        if r["requires_vehicle_alert"]:
                            self.vehicles.send_alert(
                                pedestrian_location={"lat": step["lat"], "lng": step["lng"]},
                                risk_info=f"Pedestrian at step {step_num}: {r['description']}",
                                severity=r["severity"].upper(),
                                action="SLOW DOWN - PEDESTRIAN NAVIGATING ACTIVE HAZARD"
                            )

            # Update current location to step coordinates
            self.current_location["lat"] = step.get("end_lat", step["lat"])
            self.current_location["lng"] = step.get("end_lng", step["lng"])

            if self.current_step_index == total_steps - 1:
                if step_delay > 0:
                    time.sleep(min(step_delay, 1.0))
                self.voice.speak("You have arrived at your destination safely. ARIA navigation complete.")
                self.is_navigating = False
                break

            # Advance to next step
            if auto_advance:
                if step_delay > 0:
                    time.sleep(step_delay)
                self.current_step_index += 1
            else:
                user_cmd = self.voice.listen("Say 'next' to continue, 'repeat' to hear again, or 'stop' to halt.")
                if not user_cmd:
                    self.current_step_index += 1
                    continue

                parsed = self.gemini.parse_user_command(user_cmd)
                intent = parsed.get("intent", "next")

                if intent == "stop":
                    self.voice.speak("Navigation paused.")
                    self.is_navigating = False
                    break
                elif intent == "repeat":
                    continue
                elif intent == "status":
                    remaining = total_steps - step_num
                    self.voice.speak(f"You are at step {step_num}. {remaining} steps remaining.")
                else:
                    self.current_step_index += 1

    def handle_voice_command(self, raw_command: str):
        """Processes high-level natural language user commands."""
        if not raw_command:
            return

        parsed = self.gemini.parse_user_command(raw_command)
        intent = parsed.get("intent")
        destination = parsed.get("destination", "")

        if intent == "navigate":
            target = destination or "nearest hospital"
            self.start_navigation(target)
        elif intent == "stop":
            self.is_navigating = False
            self.current_route = None
            self.voice.speak("Navigation stopped. ARIA is standing by.")
        elif intent == "status":
            if self.is_navigating and self.current_route:
                step_idx = self.current_step_index + 1
                total = len(self.current_route["steps"])
                self.voice.speak(f"Active navigation: at step {step_idx} of {total}.")
            else:
                self.voice.speak(f"ARIA is standing by at {self.current_location.get('address_hint', 'your location')}. Say 'navigate to hospital' to begin.")
        elif intent == "help":
            self.voice.speak(
                "You can say: 'Navigate to nearest hospital', 'Stop navigation', "
                "'Where am I', 'Report pothole', or 'Repeat step'."
            )
        elif intent == "report_hazard":
            htype = parsed.get("hazard_type") or "obstacle"
            self.society.add_alert(
                location=self.current_location,
                hazard_type=htype,
                description=f"User voice reported {htype}",
                severity="high",
                reported_by="ARIA Voice User"
            )
            self.voice.speak(f"Thank you. Your report of a {htype} has been added to help other blind pedestrians.")
        else:
            self.start_navigation(raw_command)

    def run_interactive(self):
        """Runs the primary voice / terminal interaction loop."""
        print_system_status()
        self.voice.speak(
            "ARIA activated. Accessible Routing and Intelligent Alerts ready. "
            "Say 'navigate to hospital' or your destination to begin."
        )

        while True:
            try:
                cmd = self.voice.listen("Speak or type your navigation command (or 'quit' to exit)")
                if not cmd:
                    continue
                if cmd.lower() in ["quit", "exit", "shutdown"]:
                    self.voice.speak("ARIA shutting down. Stay safe.")
                    break
                self.handle_voice_command(cmd)
            except KeyboardInterrupt:
                print("\nExiting ARIA.")
                break


def show_interactive_menu():
    """Displays user-friendly terminal menu for testing all capabilities."""
    while True:
        print_system_status()
        print("\nSelect an operational mode:")
        print("  [1] 🎙️  Voice Mode (Microphone Input + Audio Speech)")
        print("  [2] ⌨️  Keyboard Mode (Type Destinations & Commands)")
        print("  [3] 🚀 Automated Hackathon Demo Walk (Mount Sinai Hospital)")
        print("  [4] 🌐 Launch Interactive Visual Web Dashboard (Streamlit)")
        print("  [5] 📍 Set Custom Starting Coordinates")
        print("  [0] ❌ Exit")
        
        try:
            choice = input("\nEnter choice [1-5, or 0]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if choice == "1":
            app = ARIA(voice_mode="microphone")
            app.run_interactive()
        elif choice == "2":
            app = ARIA(voice_mode="text")
            app.run_interactive()
        elif choice == "3":
            app = ARIA(voice_mode="text")
            dest = input("Enter destination (or press Enter for 'Mount Sinai West Hospital'): ").strip()
            if not dest:
                dest = "Mount Sinai West Hospital"
            app.start_navigation(dest, auto_advance=True)
            input("\nWalk complete! Press Enter to return to menu...")
        elif choice == "4":
            print("\n🚀 Launching Streamlit Visual Dashboard in your browser...")
            subprocess.Popen([sys.executable, "-m", "streamlit", "run", "web_dashboard.py"])
            print("Dashboard opened! Return here to continue.")
            time.sleep(2)
        elif choice == "5":
            try:
                lat = float(input(f"Enter Latitude (current: {USER_LOCATION['lat']}): ") or USER_LOCATION['lat'])
                lng = float(input(f"Enter Longitude (current: {USER_LOCATION['lng']}): ") or USER_LOCATION['lng'])
                USER_LOCATION['lat'] = lat
                USER_LOCATION['lng'] = lng
                USER_LOCATION['address_hint'] = f"Custom Coords ({lat:.4f}, {lng:.4f})"
                print(f"✅ Location updated to {lat}, {lng}")
            except ValueError:
                print("⚠️ Invalid coordinate numbers.")
        elif choice == "0":
            print("Exiting ARIA. Stay safe!")
            break
        else:
            print("Invalid choice, please select 1 to 5.")


def run_aria():
    """Entry point matching hackathon idea specification."""
    aria = ARIA(voice_mode="text")
    aria.voice.speak("ARIA is running the default accessible walking flow.")
    aria.start_navigation("Mount Sinai West Hospital", auto_advance=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARIA: Accessible Routing & Intelligent Alerts")
    parser.add_argument("--demo", action="store_true", help="Run automated hackathon demonstration flow")
    parser.add_argument("--destination", type=str, default=None, help="Destination to navigate to immediately")
    parser.add_argument("--text", action="store_true", help="Force keyboard text input mode (no microphone)")
    parser.add_argument("--voice", action="store_true", help="Force microphone voice input mode")
    args = parser.parse_args()

    if args.demo:
        target = args.destination or "Mount Sinai West Hospital"
        mode = "text" if args.text else None
        app = ARIA(voice_mode=mode)
        print_system_status()
        app.start_navigation(target, auto_advance=True)
    elif args.destination:
        mode = "text" if args.text else None
        app = ARIA(voice_mode=mode)
        print_system_status()
        app.start_navigation(args.destination, auto_advance=False)
    elif args.voice:
        app = ARIA(voice_mode="microphone")
        app.run_interactive()
    elif args.text:
        app = ARIA(voice_mode="text")
        app.run_interactive()
    else:
        show_interactive_menu()
