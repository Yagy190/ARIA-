"""
layer_demo.py
Demonstration of ARIA operating as an Accessibility & Safety Intelligence Layer
inside an existing mapping system (e.g. Google Maps).

Shows:
1. Raw Google Maps route steps BEFORE ARIA
2. ARIA Layer interception & accessible augmentation AFTER ARIA
3. Real-time GPS telemetry hook and automated V2X vehicle warning triggers
"""

import sys
import json
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aria_layer import AriaLayer


def run_layer_demonstration():
    print("=" * 70)
    print(" 🦾 ARIA: Accessibility & Safety Intelligence Layer Demonstration")
    print(" Architecture: Middleware Overlay inside Google Maps")
    print("=" * 70)

    # 1. Initialize the ARIA Intelligence Layer
    # (Running in silent console mode for clean demo output)
    layer = AriaLayer(voice_enabled=True, tts_mode="console")

    # 2. Simulated RAW Output from Google Maps Directions API
    raw_google_maps_route = {
        "provider": "Google Maps Directions API",
        "distance": "420 m",
        "duration": "5 mins",
        "steps": [
            {
                "instruction": "Head northeast on Broadway toward W 43rd Street.",
                "distance": "120 m",
                "lat": 40.7580,
                "lng": -73.9855,
                "end_lat": 40.7592,
                "end_lng": -73.9850
            },
            {
                "instruction": "Turn left onto W 43rd Street.",
                "distance": "90 m",
                "lat": 40.7592,
                "lng": -73.9850,
                "end_lat": 40.7600,
                "end_lng": -73.9840
            },
            {
                "instruction": "Cross the street and continue straight.",
                "distance": "140 m",
                "lat": 40.7600,
                "lng": -73.9840,
                "end_lat": 40.7610,
                "end_lng": -73.9830
            },
            {
                "instruction": "Destination will be on the right.",
                "distance": "70 m",
                "lat": 40.7610,
                "lng": -73.9830,
                "end_lat": 40.7615,
                "end_lng": -73.9825
            }
        ]
    }

    print("\n[PHASE 1] Raw Standard Google Maps Route (Before ARIA Layer):")
    print("-" * 70)
    for i, s in enumerate(raw_google_maps_route["steps"], 1):
        print(f"  Step {i}: \"{s['instruction']}\" ({s['distance']})")

    # 3. Intercept & Augment through ARIA Layer
    print("\n" + "=" * 70)
    print(" [PHASE 2] ARIA Layer Interception & Accessibility Augmentation:")
    print("=" * 70)
    augmented = layer.augment_google_maps_route(raw_google_maps_route)

    print(f" • Overall Risk Level       : {augmented['overall_risk_level']}")
    print(f" • Total Risk Score         : {augmented['total_risk_score']}")
    print(f" • Micro-Hazards Intercepted: {augmented['hazards_detected_count']}")
    print(f" • Vehicle Warning Required : {augmented['vehicle_alert_required']}")
    print("-" * 70)

    for i, step in enumerate(augmented["augmented_steps"], 1):
        print(f"\n🚶 Step {i} [Raw Maps]: {step['instruction']}")
        if step.get("micro_hazards"):
            for h in step["micro_hazards"]:
                print(f"   ⚠️  Micro-Hazard Detected: {h['severity'].upper()} {h['hazard_type']} ({h['description']})")
        print(f"   🔊 ARIA Spoken Output : \"{step['augmented_speech']}\"")
        if step["requires_vehicle_alert"]:
            print(f"   🚗 V2X Vehicle Alert   : Dispatched to surrounding vehicles")

    # 4. Real-time GPS Telemetry Hook
    print("\n" + "=" * 70)
    print(" [PHASE 3] Live GPS Telemetry Stream (Pedestrian Walking Inside Google Maps):")
    print("=" * 70)

    simulated_gps_pings = [
        {"lat": 40.7580, "lng": -73.9855, "label": "Broadway sidewalk"},
        {"lat": 40.7592, "lng": -73.9849, "label": "Approaching pothole & crosswalk"},
        {"lat": 40.7618, "lng": -73.9836, "label": "Near discarded electric scooter"}
    ]

    for ping in simulated_gps_pings:
        print(f"\n📍 GPS Ping: Lat {ping['lat']}, Lng {ping['lng']} ({ping['label']})")
        event = layer.process_live_telemetry(ping["lat"], ping["lng"])
        if event.get("spoken_advisory"):
            print(f"   🗣️  Immediate Audio Warning: {event['spoken_advisory']}")
        else:
            print(f"   ✅ Path Clear - No immediate micro-hazards within 40m.")
        if event.get("vehicle_alert_dispatched"):
            print(f"   🚨 Connected Vehicles Notified: CAUTION - SLOW DOWN")

    print("\n" + "=" * 70)
    print(" ✅ Layer Demonstration Complete.")
    print(" ARIA successfully augmented standard Google Maps routing with")
    print(" micro-hazard awareness, tactile guidance, and V2X vehicle safety.")
    print("=" * 70)


if __name__ == "__main__":
    run_layer_demonstration()
