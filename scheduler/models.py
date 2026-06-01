from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class Station(BaseModel):
    id: str
    name: str
    chargers_count: int = 1
    electricity_cost_profile: Optional[List[Dict[str, Any]]] = None

class RouteSegment(BaseModel):
    from_node: str
    to_node: str
    distance_km: float

class Route(BaseModel):
    id: str
    name: str
    segments: List[RouteSegment]

class Bus(BaseModel):
    id: str
    operator: str
    direction: str  # e.g., "Bengaluru→Kochi" or "Kochi→Bengaluru"
    departure_time: str  # e.g., "19:00"
    priority: int = 1  # higher number = higher priority
    max_range_km: float = 240.0

class Weights(BaseModel):
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0

class Scenario(BaseModel):
    id: str
    name: str
    description: str
    route: Route
    stations: List[Station]
    buses: List[Bus]
    weights: Weights
    charging_duration_mins: float = 25.0
    travel_speed_kmh: float = 60.0

class ChargeEvent(BaseModel):
    bus_id: str
    station_id: str
    arrival_time_mins: int
    charge_start_mins: int
    charge_end_mins: int
    wait_time_mins: int
    charge_duration_mins: int

class BusScheduleResult(BaseModel):
    bus_id: str
    operator: str
    direction: str
    departure_time_mins: int
    arrival_time_mins: int
    total_wait_time_mins: int
    charge_events: List[ChargeEvent]
    route_path: List[str]
    arrival_times: Dict[str, int]
    departure_times: Dict[str, int]
    battery_levels: Dict[str, float]

class ScheduleResult(BaseModel):
    scenario_id: str
    bus_schedules: List[BusScheduleResult]
    total_wait_time: int
    total_delay: int
