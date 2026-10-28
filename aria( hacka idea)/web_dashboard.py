"""
web_dashboard.py
Interactive Visual & Simulation Dashboard for ARIA.
Designed for Hackathon Judges, Demonstrations, and Visual Assistance.
Visualizes the pedestrian route, crowdsourced society hazards,
real-time audio speech feed, and incoming V2X vehicle alerts on an interactive map.
"""

import time
import folium
import streamlit as st
import streamlit.components.v1 as components

from config import USER_LOCATION, has_valid_maps_key, has_valid_gemini_key, has_valid_firebase_key
from maps_navigation import MapsNavigation
from society_inputs import SocietyInputs
from risk_engine import RiskEngine
from vehicle_alerts import VehicleAlerts
from gemini_api import GeminiAssistant

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="ARIA Assistive Navigation & Safety Hub",
    page_icon="🦾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast Accessibility Theme
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E88E5;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555555;
        margin-bottom: 20px;
    }
    .metric-card {
        background: #f8f9fa;
        border-left: 5px solid #1E88E5;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .v2x-alert-banner {
        background: #FFEBEE;
        border: 2px solid #D32F2F;
        border-radius: 8px;
        padding: 14px;
        color: #B71C1C;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .speech-bubble {
        background: #E3F2FD;
        border-left: 4px solid #1976D2;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "society" not in st.session_state:
    st.session_state.society = SocietyInputs()
if "maps" not in st.session_state:
    st.session_state.maps = MapsNavigation()
if "gemini" not in st.session_state:
    st.session_state.gemini = GeminiAssistant()
if "risk_engine" not in st.session_state:
    st.session_state.risk_engine = RiskEngine(st.session_state.gemini)
if "vehicles" not in st.session_state:
    st.session_state.vehicles = VehicleAlerts()
if "current_route" not in st.session_state:
    # Default route: Mount Sinai West Hospital
    dest_coords = st.session_state.maps.geocode_address("hospital")
    st.session_state.current_route = st.session_state.maps.get_walking_route(USER_LOCATION, dest_coords)
if "active_step" not in st.session_state:
    st.session_state.active_step = 0
if "speech_history" not in st.session_state:
    st.session_state.speech_history = [
        "ARIA activated. System ready to guide blind user safely.",
        "Destination set: Mount Sinai West Hospital."
    ]

# Sidebar Controls
st.sidebar.title("🦾 ARIA Controls")
st.sidebar.markdown("**Accessible Routing & Intelligent Alerts**")

st.sidebar.divider()
st.sidebar.subheader("🔑 System Status")
st.sidebar.write(f"🗺️ **Maps API**: {'🟢 Active' if has_valid_maps_key() else '🟡 Smart Fallback'}")
st.sidebar.write(f"🧠 **Gemini AI**: {'🟢 Active' if has_valid_gemini_key() else '🟡 Smart Fallback'}")
st.sidebar.write(f"🚗 **Vehicle V2X**: {'🟢 FCM Active' if has_valid_firebase_key() else '🟡 Local Broadcast'}")

st.sidebar.divider()
st.sidebar.subheader("📍 Navigation Destination")
dest_input = st.sidebar.text_input("Enter Destination or Landmark", value="Nearest Hospital")

if st.sidebar.button("🔍 Find Accessible Route", use_container_width=True):
    dest_coords = st.session_state.maps.geocode_address(dest_input)
    if dest_coords:
        route = st.session_state.maps.get_walking_route(USER_LOCATION, dest_coords)
        if route:
            st.session_state.current_route = route
            st.session_state.active_step = 0
            st.session_state.speech_history.append(f"Route found for {dest_input}. Total distance: {route['distance']}.")
            st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🚶 Pedestrian Simulation")
total_steps = len(st.session_state.current_route["steps"]) if st.session_state.current_route else 0
col_prev, col_next = st.sidebar.columns(2)

with col_prev:
    if st.button("⬅️ Previous", use_container_width=True, disabled=st.session_state.active_step <= 0):
        st.session_state.active_step = max(0, st.session_state.active_step - 1)
        st.rerun()

with col_next:
    if st.button("➡️ Advance", use_container_width=True, disabled=st.session_state.active_step >= total_steps - 1):
        st.session_state.active_step = min(total_steps - 1, st.session_state.active_step + 1)
        # Add spoken feedback for current step
        curr_step = st.session_state.current_route["steps"][st.session_state.active_step]
        st.session_state.speech_history.append(f"Step {st.session_state.active_step + 1}: {curr_step['instruction']}")
        st.rerun()

if st.sidebar.button("🔄 Reset Navigation", use_container_width=True):
    st.session_state.active_step = 0
    st.rerun()

# Main Header
st.markdown('<div class="main-header">🦾 ARIA: Accessible Routing & Intelligent Alerts</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-Time Assistive Walking Navigation with Crowdsourced Hazard Detection & Connected Vehicle Warnings</div>', unsafe_allow_html=True)

# Layout: 2 Columns (Map & Details on Left, Alerts & Controls on Right)
col_left, col_right = st.columns([7, 5])

with col_left:
    st.subheader("🗺️ Real-Time Accessible Navigation Map")

    # Fetch relevant alerts for the route
    route = st.session_state.current_route
    steps = route["steps"] if route else []
    relevant_alerts = st.session_state.society.get_relevant_alerts(steps) if steps else []
    risk_analysis = st.session_state.risk_engine.analyze_route(steps, relevant_alerts)

    # Determine current pedestrian coordinates
    curr_step_idx = st.session_state.active_step
    curr_step = steps[curr_step_idx] if steps else None
    pedestrian_pos = [curr_step["lat"], curr_step["lng"]] if curr_step else [USER_LOCATION["lat"], USER_LOCATION["lng"]]

    # Build Folium Map
    m = folium.Map(location=pedestrian_pos, zoom_start=16, tiles="CartoDB positron")

    # Draw walking route line
    route_points = []
    if steps:
        for s in steps:
            route_points.append([s["lat"], s["lng"]])
            if "end_lat" in s:
                route_points.append([s["end_lat"], s["end_lng"]])
        folium.PolyLine(route_points, color="#1E88E5", weight=5, opacity=0.85, tooltip="ARIA Walking Path").add_to(m)

    # Mark Start & Destination
    if route and "origin" in route and "destination" in route:
        folium.Marker(
            [route["origin"]["lat"], route["origin"]["lng"]],
            popup="Trip Origin",
            icon=folium.Icon(color="green", icon="play", prefix="fa")
        ).add_to(m)
        folium.Marker(
            [route["destination"]["lat"], route["destination"]["lng"]],
            popup=f"Destination ({dest_input})",
            icon=folium.Icon(color="darkred", icon="flag-checkered", prefix="fa")
        ).add_to(m)

    # Mark Current Pedestrian Position
    folium.Marker(
        pedestrian_pos,
        popup=f"🚶 Blind Pedestrian (Step {curr_step_idx + 1}/{total_steps})",
        icon=folium.Icon(color="blue", icon="male", prefix="fa")
    ).add_to(m)

    # Mark Society Hazard Alerts
    severity_colors = {
        "low": "blue",
        "medium": "orange",
        "high": "red",
        "critical": "darkred"
    }

    hazard_icons = {
        "pothole": "exclamation-triangle",
        "construction": "wrench",
        "crowd": "users",
        "obstacle": "ban",
        "traffic": "car"
    }

    all_alerts = st.session_state.society.get_all_alerts()
    for alert in all_alerts:
        a_loc = alert["location"]
        a_type = alert.get("hazard_type", "obstacle")
        a_sev = alert.get("severity", "medium").lower()
        color = severity_colors.get(a_sev, "orange")
        icon_name = hazard_icons.get(a_type, "info")

        folium.Marker(
            [a_loc["lat"], a_loc["lng"]],
            popup=f"<b>{a_sev.upper()} {a_type.title()}</b><br>{alert['description']}<br><i>Reported by: {alert.get('reported_by', 'Citizen')}</i>",
            tooltip=f"{a_type}: {alert['description'][:30]}...",
            icon=folium.Icon(color=color, icon=icon_name, prefix="fa")
        ).add_to(m)

    # Render Map HTML
    components.html(m._repr_html_(), height=500)

    # Current Step Info Card
    if curr_step:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🚶 Step {curr_step_idx + 1} of {total_steps}</h4>
            <p style="font-size: 1.15rem; margin-bottom: 5px;"><strong>Instruction:</strong> {curr_step['instruction']}</p>
            <p style="color: #666; margin: 0;">Distance: <strong>{curr_step['distance']}</strong> | Est. Time: <strong>{curr_step['duration']}</strong></p>
        </div>
        """, unsafe_allow_html=True)

with col_right:
    # Vehicle V2X HUD Alert Banner
    st.subheader("🚗 Vehicle-to-Pedestrian (V2X) Broadcast")

    recent_vehicle_alerts = st.session_state.vehicles.get_recent_alerts(limit=3)

    if recent_vehicle_alerts:
        latest = recent_vehicle_alerts[0]
        st.markdown(f"""
        <div class="v2x-alert-banner">
            <div style="font-size: 1.1rem;">🚨 VEHICLE COCKPIT ALERT RECEIVED</div>
            <div style="margin-top: 4px;"><strong>Target:</strong> Vehicles within 200m of Broadway & W 43rd</div>
            <div><strong>Hazard Context:</strong> {latest['risk_info']}</div>
            <div style="margin-top: 6px; font-size: 1rem; color: #B71C1C;"><strong>ACTION:</strong> {latest['action_recommended']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No active vehicle warnings dispatched at this moment.")

    # Spoken Audio Guidance Feed
    st.subheader("🔊 ARIA Spoken Audio Guidance")
    st.caption("Live stream of what the visually impaired user hears via headphones / bone conduction:")

    speech_container = st.container(height=210)
    with speech_container:
        for msg in reversed(st.session_state.speech_history[-8:]):
            st.markdown(f'<div class="speech-bubble">🗣️ {msg}</div>', unsafe_allow_html=True)

    # Society Hazard Crowdsourcing Panel
    st.subheader("📱 Community Hazard Reporter")
    with st.expander("➕ Report a New Micro-Hazard on Path", expanded=False):
        with st.form("hazard_report_form"):
            h_type = st.selectbox("Hazard Type", ["pothole", "construction", "crowd", "obstacle", "traffic"])
            h_sev = st.selectbox("Severity", ["low", "medium", "high", "critical"], index=2)
            h_desc = st.text_input("Description", value="Deep water puddle hiding uneven road drop")
            submitted = st.form_submit_button("Submit Hazard Alert")

            if submitted:
                new_alert = st.session_state.society.add_alert(
                    location={"lat": pedestrian_pos[0] + 0.0006, "lng": pedestrian_pos[1] + 0.0004},
                    hazard_type=h_type,
                    description=h_desc,
                    severity=h_sev,
                    reported_by="Dashboard Citizen"
                )
                st.session_state.speech_history.append(f"New alert recorded: {h_type} ahead.")
                st.success(f"Report submitted! Nearby pedestrians will be alerted.")
                st.rerun()

st.divider()
st.markdown("Developed with ❤️ for accessibility using Google Maps API, Gemini AI, and V2X Communication.")
