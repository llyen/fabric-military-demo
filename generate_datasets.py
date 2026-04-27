"""
OPERATION IRONSHIELD – Battlefield Data Simulator
Generates realistic datasets for all 7 Eventstream sources matching
the schemas from the scenario document.

Usage:
  python generate_datasets.py              # Generate all datasets (static JSON files)
  python generate_datasets.py --stream     # Stream mode: prints events to stdout (for Event Hub)
  python generate_datasets.py --notebook   # Generate Fabric notebook code (.py)

Output (default):  ./datasets/ folder with JSONL files per stream
"""

import json
import math
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

SEED = 42
random.seed(SEED)

# ── Geographic center: Poligon Drawsko Pomorskie, Poland ──
# (real Polish military training area – 53.53°N, 15.78°E)
CENTER_LAT = 53.530
CENTER_LON = 15.780
SECTOR_RADIUS_KM = 8.0

# Sectors (named areas of operations) – all within Drawsko Training Area
SECTORS = {
    "Alpha":  {"lat": 53.545, "lon": 15.750, "radius_km": 2.0},  # NW corner
    "Bravo":  {"lat": 53.530, "lon": 15.810, "radius_km": 2.5},  # East - main threat axis
    "Charlie":{"lat": 53.515, "lon": 15.770, "radius_km": 2.0},  # South
    "Delta":  {"lat": 53.540, "lon": 15.800, "radius_km": 1.5},  # NE - observation post
}

# Nearby Polish reference points (for realism in queries):
#   Drawsko Pomorskie town: 53.53°N, 15.80°E
#   Borne Sulinowo:         53.58°N, 16.53°E
#   Czaplinek:              53.56°N, 16.23°E
#   Kalisz Pomorski:        53.30°N, 15.87°E

# Timeline: T+0 = simulation start
SIM_START = datetime(2026, 3, 26, 10, 0, 0, tzinfo=timezone.utc)
SIM_DURATION_MIN = 20  # total scenario duration (matches ~15-20 min demo)

# Scenario phases (minutes from start)
PHASE_NORMAL     = (0, 4)     # peaceful patrol
PHASE_DETECTION  = (4, 7)     # radar detects enemy
PHASE_ENGAGEMENT = (7, 11)    # threat response
PHASE_BDA        = (11, 16)   # battle damage assessment
PHASE_LOGISTICS  = (16, 20)   # logistics resupply

# ── Event generation density ──
# Interval between simulation ticks (seconds). Lower = more events.
EVENT_INTERVAL_SEC = 1  # 1 event-tick per second → high density for Eventstream

# ══════════════════════════════════════════════════════════════
# BLUE FORCE ASSETS
# ══════════════════════════════════════════════════════════════

VEHICLE_TYPES = ["BWP_Borsuk", "Rosomak"]
DRONE_TYPES   = ["FlyEye", "Warmate"]
UNIT_NAMES    = ["1. kompania zmech.", "2. kompania zmech.", "3. kompania zmech.", "bateria Krab"]

def _gen_vehicles():
    vehicles = []
    vid = 1
    for unit_idx, unit in enumerate(UNIT_NAMES[:3]):
        for i in range(8):
            vtype = VEHICLE_TYPES[i % 2]
            sector = list(SECTORS.keys())[unit_idx % len(SECTORS)]
            s = SECTORS[sector]
            vehicles.append({
                "VehicleId": f"BWP-{unit_idx+1}K-{vid:02d}",
                "VehicleType": vtype,
                "UnitName": unit,
                "Sector": sector,
                "BaseLat": s["lat"] + random.uniform(-0.008, 0.008),
                "BaseLon": s["lon"] + random.uniform(-0.008, 0.008),
                "FuelPercent": random.randint(55, 95),
                "AmmoPercent": random.randint(40, 100),
                "CrewCount": random.choice([3, 3, 3, 4]),
            })
            vid += 1
    return vehicles

def _gen_soldiers():
    soldiers = []
    sid = 1
    for unit_idx, unit in enumerate(UNIT_NAMES[:3]):
        for i in range(40):
            sector = list(SECTORS.keys())[unit_idx % len(SECTORS)]
            s = SECTORS[sector]
            soldiers.append({
                "SoldierId": f"SOL-{unit_idx+1}K-{sid:03d}",
                "UnitName": unit,
                "Sector": sector,
                "BaseLat": s["lat"] + random.uniform(-0.006, 0.006),
                "BaseLon": s["lon"] + random.uniform(-0.006, 0.006),
                "BaseHR": random.randint(65, 85),
                "BaseTemp": round(random.uniform(36.4, 37.0), 1),
            })
            sid += 1
    return soldiers

def _gen_drones():
    drones = []
    for i in range(12):
        dtype = DRONE_TYPES[i % 2]
        sector = list(SECTORS.keys())[i % len(SECTORS)]
        s = SECTORS[sector]
        drones.append({
            "DroneId": f"{'FE' if dtype == 'FlyEye' else 'WM'}-{i+1:02d}",
            "DroneType": dtype,
            "Sector": sector,
            "BaseLat": s["lat"] + random.uniform(-0.005, 0.005),
            "BaseLon": s["lon"] + random.uniform(-0.005, 0.005),
            "BaseAltitude": random.randint(150, 350),
            "BatteryPercent": random.randint(70, 100),
        })
    return drones

def _gen_radars():
    radars = []
    for i, sector in enumerate(SECTORS.keys()):
        s = SECTORS[sector]
        radars.append({
            "RadarId": f"RAD-{i+1:02d}",
            "Sector": sector,
            "Lat": s["lat"] + random.uniform(-0.002, 0.002),
            "Lon": s["lon"] + random.uniform(-0.002, 0.002),
        })
    return radars

def _gen_artillery():
    arty = []
    for i in range(8):
        arty.append({
            "ArtilleryId": f"KRAB-{i+1:02d}",
            "UnitName": "bateria Krab",
            "BaseLat": 53.520 + random.uniform(-0.003, 0.003),
            "BaseLon": 15.755 + random.uniform(-0.003, 0.003),
            "AmmoCount": random.randint(30, 48),
            "Status": "ready",
        })
    return arty

def _gen_weather_stations():
    stations = []
    for i, sector in enumerate(["Alpha", "Bravo", "Charlie", "Delta", "Alpha", "Charlie"]):
        s = SECTORS[sector]
        stations.append({
            "StationId": f"WX-{i+1:02d}",
            "Sector": sector,
            "Lat": s["lat"] + random.uniform(-0.004, 0.004),
            "Lon": s["lon"] + random.uniform(-0.004, 0.004),
        })
    return stations

def _gen_convoys():
    return [
        {"ConvoyId": "KZ-01", "Cargo": "ammo_fuel", "StartLat": 53.490, "StartLon": 15.700,
         "DestLat": 53.545, "DestLon": 15.750, "Speed_kmh": 40, "LoadAmmo": 1200, "LoadFuel": 5000},
        {"ConvoyId": "KZ-02", "Cargo": "ammo", "StartLat": 53.495, "StartLon": 15.720,
         "DestLat": 53.530, "DestLon": 15.810, "Speed_kmh": 35, "LoadAmmo": 800, "LoadFuel": 0},
        {"ConvoyId": "KZ-03", "Cargo": "fuel_medical", "StartLat": 53.500, "StartLon": 15.690,
         "DestLat": 53.515, "DestLon": 15.770, "Speed_kmh": 45, "LoadAmmo": 0, "LoadFuel": 8000},
        {"ConvoyId": "KZ-04", "Cargo": "ammo_fuel", "StartLat": 53.480, "StartLon": 15.730,
         "DestLat": 53.530, "DestLon": 15.810, "Speed_kmh": 38, "LoadAmmo": 1500, "LoadFuel": 4000},
    ]

# ══════════════════════════════════════════════════════════════
# RED FORCE (enemy) simulation
# ══════════════════════════════════════════════════════════════

class RedForceColumn:
    """Simulates enemy armored column approaching sector Bravo."""
    def __init__(self):
        self.count = 14
        self.start_lat = 53.570
        self.start_lon = 15.860
        self.target_lat = SECTORS["Bravo"]["lat"]
        self.target_lon = SECTORS["Bravo"]["lon"]
        self.speed_kmh = 35
        self.heading_deg = 315
        self.appear_at_min = 4   # T+4 min (aligned with PHASE_DETECTION)
        self.destroyed_at_min = 11
        self.vehicles = []
        for i in range(self.count):
            self.vehicles.append({
                "TrackId": f"TRK-{i+1:04d}",
                "ObjectType": random.choice(["armored_vehicle"] * 10 + ["apc"] * 3 + ["command_vehicle"]),
                "offset_lat": random.uniform(-0.003, 0.003),
                "offset_lon": random.uniform(-0.003, 0.003),
                "destroyed": False,
            })

    def get_positions(self, t_min: float):
        if t_min < self.appear_at_min:
            return []
        progress = min(1.0, (t_min - self.appear_at_min) / 15.0)
        if t_min >= self.destroyed_at_min:
            # After engagement: some destroyed, rest retreat
            retreat_progress = min(1.0, (t_min - self.destroyed_at_min) / 10.0)
            progress = progress - retreat_progress * 0.3
        base_lat = self.start_lat + (self.target_lat - self.start_lat) * progress
        base_lon = self.start_lon + (self.target_lon - self.start_lon) * progress
        positions = []
        for v in self.vehicles:
            if t_min >= self.destroyed_at_min and not v["destroyed"]:
                if random.random() < 0.04:  # gradually mark as destroyed
                    v["destroyed"] = True
            if v["destroyed"] and t_min >= self.destroyed_at_min + 2:
                continue
            speed = self.speed_kmh + random.uniform(-5, 5)
            if t_min >= self.destroyed_at_min:
                speed = max(0, speed * 0.3)
            dist_to_blue = max(0.5, 12.0 * (1.0 - progress))
            positions.append({
                "TrackId": v["TrackId"],
                "ObjectType": v["ObjectType"],
                "Latitude": round(base_lat + v["offset_lat"], 6),
                "Longitude": round(base_lon + v["offset_lon"], 6),
                "Speed_kmh": round(speed, 1),
                "Heading_deg": self.heading_deg + random.randint(-10, 10),
                "DistanceToBlue_km": round(dist_to_blue + random.uniform(-0.5, 0.5), 1),
                "Destroyed": v["destroyed"],
            })
        return positions


# ══════════════════════════════════════════════════════════════
# EVENT GENERATORS
# ══════════════════════════════════════════════════════════════

def _eid(prefix: str, ts: datetime, seq: int) -> str:
    return f"{prefix}-{ts.strftime('%Y%m%d')}-{seq:06d}"

def _jitter(val, pct=0.02):
    return round(val + val * random.uniform(-pct, pct), 6)


def gen_radar_detections(ts: datetime, t_min: float, radars, red_column: RedForceColumn, seq_counter) -> List[Dict]:
    events = []
    # Friendly noise detections (moderate rate – background traffic)
    for radar in radars:
        if random.random() < 0.55:
            seq_counter[0] += 1
            events.append({
                "EventId": _eid("RD", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "Sector": radar["Sector"],
                "TrackId": f"TRK-F-{random.randint(1000,9999)}",
                "Classification": random.choice(["friendly", "friendly", "unknown"]),
                "ObjectType": random.choice(["armored_vehicle", "infantry_group", "drone"]),
                "Latitude": round(radar["Lat"] + random.uniform(-0.01, 0.01), 6),
                "Longitude": round(radar["Lon"] + random.uniform(-0.01, 0.01), 6),
                "Speed_kmh": round(random.uniform(0, 20), 1),
                "Heading_deg": random.randint(0, 359),
                "DistanceToBlue_km": round(random.uniform(0.5, 3.0), 1),
                "Confidence": round(random.uniform(0.6, 0.95), 2),
                "RadarId": radar["RadarId"],
            })

    # Red force detections
    red_positions = red_column.get_positions(t_min)
    for rp in red_positions:
        if random.random() < 0.85:  # 85% detection rate per cycle
            seq_counter[0] += 1
            confidence = round(random.uniform(0.75, 0.98), 2)
            if t_min < 6:
                confidence = round(random.uniform(0.55, 0.85), 2)  # initially lower
            events.append({
                "EventId": _eid("RD", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "Sector": "Bravo",
                "TrackId": rp["TrackId"],
                "Classification": "hostile" if confidence > 0.7 else "unknown",
                "ObjectType": rp["ObjectType"],
                "Latitude": rp["Latitude"],
                "Longitude": rp["Longitude"],
                "Speed_kmh": rp["Speed_kmh"],
                "Heading_deg": rp["Heading_deg"],
                "DistanceToBlue_km": rp["DistanceToBlue_km"],
                "Confidence": confidence,
                "RadarId": random.choice(["RAD-01", "RAD-02"]),
            })
    return events


def gen_vehicle_status(ts: datetime, t_min: float, vehicles, seq_counter) -> List[Dict]:
    events = []
    for v in vehicles:
        if random.random() < 0.85:  # ~85% report per cycle (high frequency telemetry)
            seq_counter[0] += 1
            ammo = v["AmmoPercent"]
            fuel = v["FuelPercent"]
            # 3. kompania loses ammo during engagement
            if v["UnitName"] == "3. kompania zmech." and t_min > 7:
                ammo = max(5, ammo - int((t_min - 7) * 4))
            if t_min > 9:
                fuel = max(10, fuel - int((t_min - 10) * 1.5))
            lat = _jitter(v["BaseLat"], 0.001)
            lon = _jitter(v["BaseLon"], 0.001)
            speed = 0 if random.random() < 0.6 else round(random.uniform(5, 40), 1)
            combat_ready = ammo > 30 and fuel > 20
            events.append({
                "EventId": _eid("VS", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "VehicleId": v["VehicleId"],
                "VehicleType": v["VehicleType"],
                "UnitName": v["UnitName"],
                "Sector": v["Sector"],
                "Latitude": round(lat, 6),
                "Longitude": round(lon, 6),
                "Speed_kmh": speed,
                "Heading_deg": random.randint(0, 359),
                "EngineStatus": "running",
                "FuelPercent": fuel,
                "AmmoPercent": ammo,
                "CrewCount": v["CrewCount"],
                "CombatReady": combat_ready,
            })
    return events


def gen_soldier_health(ts: datetime, t_min: float, soldiers, seq_counter) -> List[Dict]:
    events = []
    for s in soldiers:
        if random.random() < 0.60:  # 60% report per cycle (wearable sensors)
            seq_counter[0] += 1
            hr = s["BaseHR"] + random.randint(-5, 15)
            temp = s["BaseTemp"] + random.uniform(-0.2, 0.3)
            stress = "normal"
            movement = random.choice(["stationary", "stationary", "walking", "walking", "prone"])

            # During engagement: elevated stress
            if 7 < t_min < 14 and s["Sector"] in ["Bravo", "Alpha"]:
                hr += random.randint(20, 60)
                stress = "elevated" if hr < 160 else "critical"
                movement = random.choice(["running", "prone", "prone"])

            # One casualty at T+10
            if s["SoldierId"] == "SOL-2K-042" and t_min >= 10:
                hr = random.randint(130, 160)
                temp = round(random.uniform(38.5, 39.8), 1)
                stress = "critical"
                movement = "prone"

            spo2 = random.randint(95, 100)
            if stress == "critical":
                spo2 = random.randint(88, 95)

            events.append({
                "EventId": _eid("SH", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "SoldierId": s["SoldierId"],
                "UnitName": s["UnitName"],
                "Sector": s["Sector"],
                "Latitude": round(_jitter(s["BaseLat"], 0.0005), 6),
                "Longitude": round(_jitter(s["BaseLon"], 0.0005), 6),
                "HeartRate": min(220, hr),
                "BodyTemp": round(min(41.0, temp), 1),
                "BloodOxygen": spo2,
                "StressLevel": stress,
                "MovementStatus": movement,
            })
    return events


def gen_drone_observations(ts: datetime, t_min: float, drones, red_column: RedForceColumn, seq_counter) -> List[Dict]:
    events = []
    for d in drones:
        if random.random() < 0.65:  # drones report frequently
            seq_counter[0] += 1
            battery = max(5, d["BatteryPercent"] - int(t_min * 0.8))
            alt = d["BaseAltitude"] + random.randint(-30, 30)
            lat = _jitter(d["BaseLat"], 0.002)
            lon = _jitter(d["BaseLon"], 0.002)

            obs_type = "patrol_scan"
            target_class = "none"
            target_count = 0
            target_lat = None
            target_lon = None
            confidence = 0.0

            # Drones near Bravo detect enemy
            red_pos = red_column.get_positions(t_min)
            if d["Sector"] == "Bravo" and red_pos:
                obs_type = "visual_contact"
                visible = [r for r in red_pos if not r.get("Destroyed", False)]
                target_count = len(visible)
                if visible:
                    target_class = "armored_column"
                    target_lat = round(sum(r["Latitude"] for r in visible) / len(visible), 6)
                    target_lon = round(sum(r["Longitude"] for r in visible) / len(visible), 6)
                    confidence = round(random.uniform(0.85, 0.98), 2)
            elif random.random() < 0.1:
                obs_type = "thermal_anomaly"
                target_class = "unknown"
                target_count = random.randint(1, 3)
                target_lat = round(lat + random.uniform(-0.005, 0.005), 6)
                target_lon = round(lon + random.uniform(-0.005, 0.005), 6)
                confidence = round(random.uniform(0.4, 0.7), 2)

            event = {
                "EventId": _eid("DO", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "DroneId": d["DroneId"],
                "DroneType": d["DroneType"],
                "Sector": d["Sector"],
                "Latitude": round(lat, 6),
                "Longitude": round(lon, 6),
                "Altitude_m": alt,
                "BatteryPercent": battery,
                "ObservationType": obs_type,
                "TargetClassification": target_class,
                "TargetCount": target_count,
                "Confidence": confidence,
            }
            if target_lat is not None:
                event["TargetLatitude"] = target_lat
                event["TargetLongitude"] = target_lon
                event["ImageUrl"] = f"blob://observations/{_eid('DO', ts, seq_counter[0])}.jpg"
            events.append(event)
    return events


def gen_weather_data(ts: datetime, t_min: float, stations, seq_counter) -> List[Dict]:
    events = []
    for st in stations:
        if random.random() < 0.45:  # weather stations report often
            seq_counter[0] += 1
            # Weather degrades over time (as per scenario)
            base_vis = 8.0
            base_ceiling = 1200
            cloud_cover = 4
            if t_min > 10:
                degradation = min(1.0, (t_min - 10) / 15.0)
                base_vis = max(1.5, 8.0 - degradation * 6.0)
                base_ceiling = max(400, 1200 - int(degradation * 700))
                cloud_cover = min(8, 4 + int(degradation * 4))

            events.append({
                "EventId": _eid("WX", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "StationId": st["StationId"],
                "Sector": st["Sector"],
                "Latitude": round(st["Lat"], 6),
                "Longitude": round(st["Lon"], 6),
                "Temperature_C": round(8.5 + random.uniform(-1.5, 1.5), 1),
                "WindSpeed_kmh": round(12 + random.uniform(-3, 8), 1),
                "WindDirection_deg": 225 + random.randint(-20, 20),
                "Visibility_km": round(base_vis + random.uniform(-1, 0.5), 1),
                "CloudCeiling_m": base_ceiling + random.randint(-100, 100),
                "CloudCover_okta": cloud_cover,
                "Precipitation": random.choice(["none", "none", "none", "light_rain"]) if t_min < 15 else random.choice(["none", "light_rain", "light_rain", "fog"]),
                "HumidityPercent": random.randint(65, 90),
            })
    return events


def gen_sigint_intercepts(ts: datetime, t_min: float, red_column: RedForceColumn, seq_counter) -> List[Dict]:
    events = []
    red_pos = red_column.get_positions(t_min)

    if red_pos and random.random() < 0.70:
        seq_counter[0] += 1
        freq = round(random.choice([30.5, 45.2, 78.8, 121.5, 156.3, 243.0]) + random.uniform(-0.5, 0.5), 1)
        signal_type = random.choice(["voice_encrypted", "voice_encrypted", "data_burst", "command_net"])

        if t_min >= red_column.destroyed_at_min:
            signal_type = random.choice(["voice_encrypted", "emergency_call", "jamming_signal"])

        bearing = 315 + random.randint(-15, 15)
        strength = round(random.uniform(-60, -30), 1)

        events.append({
            "EventId": _eid("SI", ts, seq_counter[0]),
            "Timestamp": ts.isoformat(),
            "InterceptId": f"INT-{random.randint(10000, 99999)}",
            "Frequency_MHz": freq,
            "SignalType": signal_type,
            "Bearing_deg": bearing,
            "SignalStrength_dBm": strength,
            "Duration_sec": random.randint(3, 45),
            "Classification": "hostile_comms",
            "AssociatedSector": "Bravo",
            "Confidence": round(random.uniform(0.7, 0.95), 2),
            "TranscriptAvailable": signal_type == "voice_encrypted" and random.random() < 0.3,
            "Notes": _sigint_note(t_min, signal_type),
        })

    # Occasional friendly / background intercepts
    if random.random() < 0.25:
        seq_counter[0] += 1
        events.append({
            "EventId": _eid("SI", ts, seq_counter[0]),
            "Timestamp": ts.isoformat(),
            "InterceptId": f"INT-{random.randint(10000, 99999)}",
            "Frequency_MHz": round(random.uniform(100, 400), 1),
            "SignalType": "civilian_broadcast",
            "Bearing_deg": random.randint(0, 359),
            "SignalStrength_dBm": round(random.uniform(-80, -50), 1),
            "Duration_sec": random.randint(10, 120),
            "Classification": "civilian",
            "AssociatedSector": random.choice(list(SECTORS.keys())),
            "Confidence": round(random.uniform(0.5, 0.8), 2),
            "TranscriptAvailable": False,
            "Notes": "Civilian radio traffic – no tactical significance",
        })
    return events


def _sigint_note(t_min, sig_type):
    if t_min < 7:
        return "Initial intercept – pattern matches battalion command net"
    elif t_min < 10:
        return "Increased traffic volume – possible coordination for attack"
    elif t_min < 13:
        notes = {
            "emergency_call": "Distress signal detected – possible casualties in enemy column",
            "jamming_signal": "Electronic warfare signal – attempting to jam BLUE frequencies",
            "voice_encrypted": "Encrypted traffic – high volume, possible retreat coordination",
            "data_burst": "Short data burst – possible targeting data",
            "command_net": "Command net activity – orders being issued",
        }
        return notes.get(sig_type, "Post-engagement communications activity")
    else:
        return "Diminishing signal activity – enemy withdrawal likely"


def gen_ammo_logistics(ts: datetime, t_min: float, convoys, vehicles, seq_counter) -> List[Dict]:
    events = []

    # Convoy position updates
    for c in convoys:
        if random.random() < 0.65:
            seq_counter[0] += 1
            progress = min(1.0, t_min / 50.0)  # slow progress
            if c["ConvoyId"] == "KZ-04" and t_min > 16:
                progress = min(1.0, (t_min - 10) / 40.0)  # rerouted, slower

            lat = c["StartLat"] + (c["DestLat"] - c["StartLat"]) * progress
            lon = c["StartLon"] + (c["DestLon"] - c["StartLon"]) * progress
            speed = c["Speed_kmh"] + random.uniform(-5, 5)

            total_dist = math.sqrt((c["DestLat"] - c["StartLat"])**2 + (c["DestLon"] - c["StartLon"])**2) * 111
            remaining = total_dist * (1.0 - progress)
            eta_min = int(remaining / (speed / 60)) if speed > 0 else 999

            status = "en_route"
            if progress >= 0.95:
                status = "arrived"
                speed = 0
            elif c["ConvoyId"] == "KZ-04" and 16 <= t_min <= 18:
                status = "rerouting"

            events.append({
                "EventId": _eid("AL", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "ConvoyId": c["ConvoyId"],
                "CargoType": c["Cargo"],
                "Latitude": round(lat + random.uniform(-0.001, 0.001), 6),
                "Longitude": round(lon + random.uniform(-0.001, 0.001), 6),
                "Speed_kmh": round(max(0, speed), 1),
                "Status": status,
                "LoadAmmo_rounds": c["LoadAmmo"],
                "LoadFuel_liters": c["LoadFuel"],
                "ETA_min": max(0, eta_min),
                "DestinationUnit": _convoy_dest(c["ConvoyId"]),
                "RouteRisk": _route_risk(c["ConvoyId"], t_min),
            })

    # Depot / unit ammo summaries (aggregated view)
    if random.random() < 0.50:
        for unit_idx, unit in enumerate(UNIT_NAMES[:3]):
            seq_counter[0] += 1
            base_ammo = 85 - unit_idx * 15
            if unit == "3. kompania zmech." and t_min > 7:
                base_ammo = max(5, base_ammo - int((t_min - 7) * 5))
            events.append({
                "EventId": _eid("AL", ts, seq_counter[0]),
                "Timestamp": ts.isoformat(),
                "ConvoyId": "UNIT_SUMMARY",
                "CargoType": "status_report",
                "Latitude": SECTORS[list(SECTORS.keys())[unit_idx]]["lat"],
                "Longitude": SECTORS[list(SECTORS.keys())[unit_idx]]["lon"],
                "Speed_kmh": 0,
                "Status": "unit_status",
                "LoadAmmo_rounds": 0,
                "LoadFuel_liters": 0,
                "ETA_min": 0,
                "DestinationUnit": unit,
                "RouteRisk": "n/a",
                "UnitAmmoPercent": base_ammo,
                "UnitFuelPercent": max(20, 75 - int(t_min * 1.2)),
                "ResupplyNeeded": base_ammo < 30,
            })
    return events


def _convoy_dest(cid):
    return {"KZ-01": "1. kompania zmech.", "KZ-02": "2. kompania zmech.",
            "KZ-03": "3. kompania zmech.", "KZ-04": "3. kompania zmech."}[cid]

def _route_risk(cid, t_min):
    if cid == "KZ-04" and 4 < t_min < 16:
        return "high"
    if cid == "KZ-02" and 4 < t_min < 11:
        return "medium"
    return "low"


# ══════════════════════════════════════════════════════════════
# MAIN SIMULATION LOOP
# ══════════════════════════════════════════════════════════════

def run_simulation():
    """Generate all events for the full scenario timeline."""
    vehicles = _gen_vehicles()
    soldiers = _gen_soldiers()
    drones = _gen_drones()
    radars = _gen_radars()
    artillery = _gen_artillery()
    wx_stations = _gen_weather_stations()
    convoys = _gen_convoys()
    red_column = RedForceColumn()

    # Sequence counters per stream
    counters = {
        "radar": [0], "vehicle": [0], "soldier": [0],
        "drone": [0], "weather": [0], "sigint": [0], "logistics": [0],
    }

    # Storage per stream
    streams = {
        "radar_detections": [],
        "vehicle_status": [],
        "soldier_health": [],
        "drone_observations": [],
        "weather_data": [],
        "sigint_intercepts": [],
        "ammo_logistics": [],
    }

    # Generate events every EVENT_INTERVAL_SEC seconds for the full duration
    interval_sec = EVENT_INTERVAL_SEC
    total_steps = (SIM_DURATION_MIN * 60) // interval_sec

    for step in range(total_steps):
        elapsed_sec = step * interval_sec
        t_min = elapsed_sec / 60.0
        ts = SIM_START + timedelta(seconds=elapsed_sec)

        streams["radar_detections"].extend(
            gen_radar_detections(ts, t_min, radars, red_column, counters["radar"]))
        streams["vehicle_status"].extend(
            gen_vehicle_status(ts, t_min, vehicles, counters["vehicle"]))
        streams["soldier_health"].extend(
            gen_soldier_health(ts, t_min, soldiers, counters["soldier"]))
        streams["drone_observations"].extend(
            gen_drone_observations(ts, t_min, drones, red_column, counters["drone"]))
        streams["weather_data"].extend(
            gen_weather_data(ts, t_min, wx_stations, counters["weather"]))
        streams["sigint_intercepts"].extend(
            gen_sigint_intercepts(ts, t_min, red_column, counters["sigint"]))
        streams["ammo_logistics"].extend(
            gen_ammo_logistics(ts, t_min, convoys, vehicles, counters["logistics"]))

    return streams


def save_datasets(streams: Dict[str, List], output_dir: str):
    """Save each stream as a JSONL file."""
    os.makedirs(output_dir, exist_ok=True)
    summary = []
    for name, events in streams.items():
        path = os.path.join(output_dir, f"{name}.jsonl")
        with open(path, 'w', encoding='utf-8') as f:
            for event in events:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        size_kb = os.path.getsize(path) / 1024
        summary.append((name, len(events), f"{size_kb:.1f} KB"))
        print(f"  {name}.jsonl: {len(events)} events ({size_kb:.1f} KB)")

    # Also save as single combined JSON (for easy preview)
    combined_path = os.path.join(output_dir, "_all_events_combined.json")
    combined = {}
    for name, events in streams.items():
        combined[name] = {"event_count": len(events), "sample_first_3": events[:3], "sample_last_3": events[-3:]}
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"\n  _all_events_combined.json: summary with samples")

    return summary


def generate_fabric_notebook(output_dir: str):
    """Generate a Python notebook script for Fabric that sends events to Eventstream."""
    code = '''# ═══════════════════════════════════════════════════════════════
# OPERATION IRONSHIELD – Fabric Notebook: Real-Time Data Sender
# ═══════════════════════════════════════════════════════════════
# This notebook reads the pre-generated JSONL datasets and sends
# events to Azure Event Hub (→ Fabric Eventstream) in real-time,
# simulating live sensor feeds.
#
# Usage: Run in Microsoft Fabric notebook attached to a Spark cluster.
# Prerequisites: Upload dataset JSONL files to ABFSS lakehouse path.
# ═══════════════════════════════════════════════════════════════

# --- Configuration ---
EVENT_HUB_CONNECTION_STRING = "<YOUR_EVENT_HUB_CONNECTION_STRING>"
EVENT_HUB_NAME = "ironshield-events"
LAKEHOUSE_PATH = "abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>/Files/ironshield/"

# Time scale factor: 1.0 = real-time, 0.1 = 10x faster (for demo)
TIME_SCALE = 0.5

# --- Install Event Hub SDK (first run only) ---
# %pip install azure-eventhub

import json
import time
from datetime import datetime, timezone
from azure.eventhub import EventHubProducerClient, EventData

# --- Load datasets ---
STREAMS = [
    "radar_detections",
    "vehicle_status", 
    "soldier_health",
    "drone_observations",
    "weather_data",
    "sigint_intercepts",
    "ammo_logistics",
]

all_events = []

for stream_name in STREAMS:
    path = f"{LAKEHOUSE_PATH}{stream_name}.jsonl"
    try:
        df = spark.read.text(path)
        rows = df.collect()
        for row in rows:
            event = json.loads(row.value)
            event["_stream"] = stream_name
            all_events.append(event)
        print(f"Loaded {len(rows)} events from {stream_name}")
    except Exception as e:
        print(f"Warning: Could not load {stream_name}: {e}")

# Sort all events by timestamp
all_events.sort(key=lambda e: e.get("Timestamp", ""))
print(f"\\nTotal events to send: {len(all_events)}")

# --- Send events to Event Hub ---
producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONNECTION_STRING,
    eventhub_name=EVENT_HUB_NAME,
)

print("\\n🚀 Starting real-time simulation...")
print(f"   Time scale: {TIME_SCALE}x (1.0 = real-time)")

prev_ts = None
sent_count = 0
batch_size = 0
event_batch = producer.create_batch()

try:
    for event in all_events:
        ts_str = event.get("Timestamp", "")
        stream = event.pop("_stream", "unknown")
        
        # Timing: wait proportionally between events
        if prev_ts and ts_str:
            try:
                curr = datetime.fromisoformat(ts_str)
                prev = datetime.fromisoformat(prev_ts)
                delta = (curr - prev).total_seconds() * TIME_SCALE
                if delta > 0:
                    time.sleep(min(delta, 5.0))  # cap at 5s
            except:
                pass
        prev_ts = ts_str
        
        # Create event data with stream routing property
        event_data = EventData(json.dumps(event, ensure_ascii=False))
        event_data.properties = {"stream": stream}
        
        try:
            event_batch.add(event_data)
            batch_size += 1
        except ValueError:
            # Batch full, send it
            producer.send_batch(event_batch)
            sent_count += batch_size
            event_batch = producer.create_batch()
            event_batch.add(event_data)
            batch_size = 1
        
        # Send batch every 50 events or so
        if batch_size >= 50:
            producer.send_batch(event_batch)
            sent_count += batch_size
            event_batch = producer.create_batch()
            batch_size = 0
            print(f"   Sent {sent_count}/{len(all_events)} events...")

    # Send remaining
    if batch_size > 0:
        producer.send_batch(event_batch)
        sent_count += batch_size

    print(f"\\n✅ Simulation complete! Sent {sent_count} events total.")

finally:
    producer.close()
'''
    path = os.path.join(output_dir, "fabric_notebook_sender.py")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f"\n  fabric_notebook_sender.py: Fabric notebook code for Event Hub streaming")


def generate_kql_create_tables(output_dir: str):
    """Generate KQL commands to create tables in Eventhouse."""
    kql = '''// ═══════════════════════════════════════════════════════════════
// OPERATION IRONSHIELD – KQL Table Definitions for Eventhouse
// Run these commands in your Eventhouse KQL Database
// ═══════════════════════════════════════════════════════════════

// --- 1. Radar Detections ---
.create table RadarDetections (
    EventId: string,
    Timestamp: datetime,
    Sector: string,
    TrackId: string,
    Classification: string,
    ObjectType: string,
    Latitude: real,
    Longitude: real,
    Speed_kmh: real,
    Heading_deg: int,
    DistanceToBlue_km: real,
    Confidence: real,
    RadarId: string
)

// --- 2. Vehicle Status ---
.create table VehicleStatus (
    EventId: string,
    Timestamp: datetime,
    VehicleId: string,
    VehicleType: string,
    UnitName: string,
    Sector: string,
    Latitude: real,
    Longitude: real,
    Speed_kmh: real,
    Heading_deg: int,
    EngineStatus: string,
    FuelPercent: int,
    AmmoPercent: int,
    CrewCount: int,
    CombatReady: bool
)

// --- 3. Soldier Health ---
.create table SoldierHealth (
    EventId: string,
    Timestamp: datetime,
    SoldierId: string,
    UnitName: string,
    Sector: string,
    Latitude: real,
    Longitude: real,
    HeartRate: int,
    BodyTemp: real,
    BloodOxygen: int,
    StressLevel: string,
    MovementStatus: string
)

// --- 4. Drone Observations ---
.create table DroneObservations (
    EventId: string,
    Timestamp: datetime,
    DroneId: string,
    DroneType: string,
    Sector: string,
    Latitude: real,
    Longitude: real,
    Altitude_m: int,
    BatteryPercent: int,
    ObservationType: string,
    TargetClassification: string,
    TargetCount: int,
    Confidence: real,
    TargetLatitude: real,
    TargetLongitude: real,
    ImageUrl: string
)

// --- 5. Weather Data ---
.create table WeatherData (
    EventId: string,
    Timestamp: datetime,
    StationId: string,
    Sector: string,
    Latitude: real,
    Longitude: real,
    Temperature_C: real,
    WindSpeed_kmh: real,
    WindDirection_deg: int,
    Visibility_km: real,
    CloudCeiling_m: int,
    CloudCover_okta: int,
    Precipitation: string,
    HumidityPercent: int
)

// --- 6. SIGINT Intercepts ---
.create table SigintIntercepts (
    EventId: string,
    Timestamp: datetime,
    InterceptId: string,
    Frequency_MHz: real,
    SignalType: string,
    Bearing_deg: int,
    SignalStrength_dBm: real,
    Duration_sec: int,
    Classification: string,
    AssociatedSector: string,
    Confidence: real,
    TranscriptAvailable: bool,
    Notes: string
)

// --- 7. Ammo Logistics ---
.create table AmmoLogistics (
    EventId: string,
    Timestamp: datetime,
    ConvoyId: string,
    CargoType: string,
    Latitude: real,
    Longitude: real,
    Speed_kmh: real,
    Status: string,
    LoadAmmo_rounds: int,
    LoadFuel_liters: int,
    ETA_min: int,
    DestinationUnit: string,
    RouteRisk: string
)

// ═══════════════════════════════════════════════════════════════
// INGESTION MAPPINGS (for Event Hub → Eventhouse)
// ═══════════════════════════════════════════════════════════════

.create table RadarDetections ingestion json mapping "RadarDetections_mapping"
    \'[{"column":"EventId","path":"$.EventId"},{"column":"Timestamp","path":"$.Timestamp"},{"column":"Sector","path":"$.Sector"},{"column":"TrackId","path":"$.TrackId"},{"column":"Classification","path":"$.Classification"},{"column":"ObjectType","path":"$.ObjectType"},{"column":"Latitude","path":"$.Latitude"},{"column":"Longitude","path":"$.Longitude"},{"column":"Speed_kmh","path":"$.Speed_kmh"},{"column":"Heading_deg","path":"$.Heading_deg"},{"column":"DistanceToBlue_km","path":"$.DistanceToBlue_km"},{"column":"Confidence","path":"$.Confidence"},{"column":"RadarId","path":"$.RadarId"}]\'

.create table VehicleStatus ingestion json mapping "VehicleStatus_mapping"
    \'[{"column":"EventId","path":"$.EventId"},{"column":"Timestamp","path":"$.Timestamp"},{"column":"VehicleId","path":"$.VehicleId"},{"column":"VehicleType","path":"$.VehicleType"},{"column":"UnitName","path":"$.UnitName"},{"column":"Sector","path":"$.Sector"},{"column":"Latitude","path":"$.Latitude"},{"column":"Longitude","path":"$.Longitude"},{"column":"Speed_kmh","path":"$.Speed_kmh"},{"column":"Heading_deg","path":"$.Heading_deg"},{"column":"EngineStatus","path":"$.EngineStatus"},{"column":"FuelPercent","path":"$.FuelPercent"},{"column":"AmmoPercent","path":"$.AmmoPercent"},{"column":"CrewCount","path":"$.CrewCount"},{"column":"CombatReady","path":"$.CombatReady"}]\'

.create table SoldierHealth ingestion json mapping "SoldierHealth_mapping"
    \'[{"column":"EventId","path":"$.EventId"},{"column":"Timestamp","path":"$.Timestamp"},{"column":"SoldierId","path":"$.SoldierId"},{"column":"UnitName","path":"$.UnitName"},{"column":"Sector","path":"$.Sector"},{"column":"Latitude","path":"$.Latitude"},{"column":"Longitude","path":"$.Longitude"},{"column":"HeartRate","path":"$.HeartRate"},{"column":"BodyTemp","path":"$.BodyTemp"},{"column":"BloodOxygen","path":"$.BloodOxygen"},{"column":"StressLevel","path":"$.StressLevel"},{"column":"MovementStatus","path":"$.MovementStatus"}]\'

// ═══════════════════════════════════════════════════════════════
// SAMPLE ANALYTICAL QUERIES
// ═══════════════════════════════════════════════════════════════

// --- Hostile contacts in sector Bravo (last 10 min) ---
RadarDetections
| where Timestamp > ago(10m)
| where Classification == "hostile" and Sector == "Bravo"
| summarize 
    ContactCount = dcount(TrackId),
    AvgSpeed = avg(Speed_kmh),
    AvgHeading = avg(Heading_deg),
    MinDistance = min(DistanceToBlue_km),
    MaxConfidence = max(Confidence)
| extend ETA_min = round(MinDistance / (AvgSpeed / 60), 1)

// --- Unit combat readiness ---
VehicleStatus
| where Timestamp > ago(2m)
| summarize arg_max(Timestamp, *) by VehicleId
| summarize 
    ReadyCount = countif(CombatReady),
    TotalCount = count(),
    AvgAmmo = avg(AmmoPercent),
    AvgFuel = avg(FuelPercent)
  by UnitName
| extend ReadinessPercent = round(100.0 * ReadyCount / TotalCount, 1)

// --- Soldier health alerts ---
SoldierHealth
| where Timestamp > ago(5m)
| summarize arg_max(Timestamp, *) by SoldierId
| where HeartRate > 180 or BodyTemp > 39.0 or BloodOxygen < 92
| project SoldierId, UnitName, Sector, HeartRate, BodyTemp, BloodOxygen, StressLevel,
          AlertLevel = case(
              HeartRate > 200 or BloodOxygen < 90, "CRITICAL",
              HeartRate > 180 or BodyTemp > 39.0, "WARNING",
              "MONITOR")
| order by AlertLevel asc

// --- Anomaly detection: spike in hostile contacts ---
RadarDetections
| where Classification == "hostile"
| summarize ContactCount = dcount(TrackId) by bin(Timestamp, 1m), Sector
| make-series ContactSeries = avg(ContactCount) on Timestamp step 1m by Sector
| extend (Anomalies, AnomalyScore, ExpectedValue) = series_decompose_anomalies(ContactSeries, 2.5)
'''
    path = os.path.join(output_dir, "eventhouse_kql_setup.kql")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(kql)
    print(f"  eventhouse_kql_setup.kql: KQL table definitions + mappings + sample queries")


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

    print("=" * 60)
    print("OPERATION IRONSHIELD – Dataset Generator")
    print("=" * 60)

    print("\n📊 Generating simulation data...")
    streams = run_simulation()

    print("\n💾 Saving datasets to JSONL files...")
    save_datasets(streams, output_dir)

    print("\n📝 Generating Fabric notebook sender...")
    generate_fabric_notebook(output_dir)

    print("\n📝 Generating KQL table definitions...")
    generate_kql_create_tables(output_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_events = sum(len(e) for e in streams.values())
    print(f"\n  Total events generated: {total_events:,}")
    print(f"  Simulation duration:    {SIM_DURATION_MIN} minutes")
    print(f"  Event interval:         {EVENT_INTERVAL_SEC} second(s)")
    print(f"  Location:               Poligon Drawsko Pomorskie, Poland")
    print(f"                          ({CENTER_LAT}°N, {CENTER_LON}°E)")
    print(f"  Scenario phases:")
    print(f"    T+0–4 min:  Normal patrol (baseline)")
    print(f"    T+4–7 min:  Enemy detection (anomaly)")
    print(f"    T+7–11 min: Engagement (threat response)")
    print(f"    T+11–16 min: BDA (battle damage assessment)")
    print(f"    T+16–20 min: Logistics resupply")
    print(f"\n  Output directory: {output_dir}")
    print(f"\n  Files:")
    for name in streams:
        print(f"    {name}.jsonl")
    print(f"    _all_events_combined.json  (summary + samples)")
    print(f"    fabric_notebook_sender.py  (Event Hub streaming code)")
    print(f"    eventhouse_kql_setup.kql   (KQL table definitions)")
    print("\n✅ Done!")
