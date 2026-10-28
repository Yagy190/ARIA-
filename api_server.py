"""
api_server.py
Lightweight Middleware API Server for the ARIA Layer.
Enables Google Maps (Web, Android, iOS), Mapbox, Apple Maps, or third-party
navigation engines to communicate with ARIA via standard HTTP REST endpoints.
"""

import sys
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from aria_layer import AriaLayer

app = FastAPI(
    title="ARIA Assistive Intelligence Layer API",
    description="Universal accessibility middleware for Google Maps and mapping systems.",
    version="1.0.0"
)

# Instantiate the global ARIA Layer instance
aria = AriaLayer(voice_enabled=False, tts_mode="console")


# =============================================================================
# Request Schemas
# =============================================================================
class LocationPoint(BaseModel):
    lat: float
    lng: float


class TelemetryRequest(BaseModel):
    lat: float
    lng: float
    step_instruction: Optional[str] = "Walking"


class HazardReportRequest(BaseModel):
    lat: float
    lng: float
    hazard_type: str
    description: str
    severity: str = "medium"
    reported_by: Optional[str] = "Mobile User"


class GoogleRouteStep(BaseModel):
    instruction: str
    distance: Optional[str] = "100 m"
    distance_meters: Optional[int] = 100
    duration: Optional[str] = "1 min"
    lat: float
    lng: float
    end_lat: Optional[float] = None
    end_lng: Optional[float] = None


class AugmentRouteRequest(BaseModel):
    provider: Optional[str] = "Google Maps"
    distance: Optional[str] = "500 m"
    duration: Optional[str] = "6 mins"
    steps: List[GoogleRouteStep]


# =============================================================================
# Endpoints
# =============================================================================
@app.get("/")
def root():
    return {
        "system": "ARIA: Accessible Routing & Intelligent Alerts",
        "role": "Universal Map Intelligence & Safety Layer",
        "supported_map_systems": ["Google Maps", "Apple Maps", "Mapbox", "OpenStreetMap"],
        "status": "active"
    }


@app.post("/api/v1/augment-route")
def augment_route(payload: AugmentRouteRequest):
    """
    Takes standard Google Maps route steps and augments them with:
    - Micro-hazards within route buffer
    - Tactile, cane-aware spoken audio guidance
    - Risk engine safety assessment & vehicle alert triggers
    """
    raw_dict = payload.model_dump()
    augmented = aria.augment_google_maps_route(raw_dict)
    return augmented


@app.post("/api/v1/telemetry-ping")
def telemetry_ping(payload: TelemetryRequest):
    """
    Called periodically during active navigation inside Google Maps.
    Evaluates real-time proximity to dynamic hazards and triggers vehicle warnings if needed.
    """
    step_obj = {"instruction": payload.step_instruction}
    event = aria.process_live_telemetry(payload.lat, payload.lng, current_google_step=step_obj)
    return event


@app.post("/api/v1/report-hazard")
def report_hazard(payload: HazardReportRequest):
    """
    Crowdsourcing endpoint for community members to inject new micro-hazards into the layer.
    """
    alert = aria.report_hazard_to_layer(
        lat=payload.lat,
        lng=payload.lng,
        hazard_type=payload.hazard_type,
        description=payload.description,
        severity=payload.severity,
        reporter=payload.reported_by or "API Reporter"
    )
    return {"status": "success", "alert": alert}


@app.get("/api/v1/hazards")
def get_all_hazards():
    """Returns all active micro-hazards in the overlay layer."""
    return {"hazards": aria.society.get_all_alerts()}


@app.get("/api/v1/vehicle-alerts")
def get_vehicle_alerts():
    """Returns recent V2X safety alerts dispatched to surrounding vehicles."""
    return {"recent_dispatches": aria.vehicles.get_recent_alerts(limit=20)}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting ARIA Layer Middleware API Server on http://localhost:8000 ...")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
