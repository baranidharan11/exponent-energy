import logging
from typing import List, Dict, Any, Optional
from ortools.sat.python.cp_model import CpModel, CpSolver, OPTIMAL, FEASIBLE

from scheduler.models import (
    Scenario, ScheduleResult, BusScheduleResult, ChargeEvent
)
from scheduler.rules import (
    Rule, RouteOrderRule, BatteryRangeRule, NoOverlapRule,
    MinIndividualWaitRule, OperatorFairnessRule, MinNetworkDelayRule
)
from utils.helpers import get_route_nodes, parse_time_to_mins

logger = logging.getLogger(__name__)

class SchedulingEngine:
    def __init__(self, rules: Optional[List[Rule]] = None):
        """Initialize the scheduling engine. If rules are not provided, 
        load the default set of hard and soft rules."""
        if rules is not None:
            self.rules = rules
        else:
            self.rules = [
                RouteOrderRule(),
                BatteryRangeRule(),
                NoOverlapRule(),
                MinIndividualWaitRule(),
                OperatorFairnessRule(),
                MinNetworkDelayRule()
            ]

    def solve(self, scenario: Scenario, timeout_seconds: float = 30.0) -> ScheduleResult:
        """Build and solve the scheduling optimization model for a given scenario.
        
        Args:
            scenario: The input Scenario Pydantic model.
            timeout_seconds: Max solver time limit.
            
        Returns:
            ScheduleResult Pydantic model.
            
        Raises:
            RuntimeError if the model is infeasible or cannot be solved.
        """
        model = CpModel()
        
        # 1. Initialize variables dictionary
        vars_dict: Dict[str, Any] = {
            "arrival": {},
            "departure": {},
            "battery": {},
            "charge_active": {},
            "charge_start": {},
            "charge_end": {},
            "charge_interval": {},
            "wait_time": {},
            "total_wait": {},
            "delay": {},
            "objective_terms": [] # list of (term_var, weight)
        }

        # Constants from scenario
        route = scenario.route
        speed = scenario.travel_speed_kmh
        charging_duration = int(scenario.charging_duration_mins)

        # 2. Create decision variables for each bus
        for bus in scenario.buses:
            path = get_route_nodes(route, bus.direction)
            dep_mins = parse_time_to_mins(bus.departure_time)
            max_range = int(bus.max_range_km)

            # We use a time horizon of 48 hours (2880 mins) to prevent boundary collisions
            time_horizon = 2880

            # Arrival, Departure, and Battery variables at each stop along the path
            for j in range(len(path)):
                node = path[j]
                if j == 0:
                    # Origin node: arrival and departure times are fixed to the scheduled departure time
                    vars_dict["arrival"][bus.id, j] = model.NewConstant(dep_mins)
                    vars_dict["departure"][bus.id, j] = model.NewConstant(dep_mins)
                    vars_dict["battery"][bus.id, j] = model.NewConstant(max_range)
                else:
                    vars_dict["arrival"][bus.id, j] = model.NewIntVar(0, time_horizon, f"arr_{bus.id}_{node}")
                    vars_dict["departure"][bus.id, j] = model.NewIntVar(0, time_horizon, f"dep_{bus.id}_{node}")
                    vars_dict["battery"][bus.id, j] = model.NewIntVar(0, max_range, f"bat_{bus.id}_{node}")

            # Charging variables for intermediate stations (stops 1 to 4)
            for j in range(1, len(path) - 1):
                station_id = path[j]
                
                # Active charging decision (1 if bus charges here, 0 otherwise)
                charge_act = model.NewBoolVar(f"charge_act_{bus.id}_{station_id}")
                vars_dict["charge_active"][bus.id, station_id] = charge_act

                # Start and end of charge
                c_start = model.NewIntVar(0, time_horizon, f"charge_start_{bus.id}_{station_id}")
                c_end = model.NewIntVar(0, time_horizon, f"charge_end_{bus.id}_{station_id}")
                
                vars_dict["charge_start"][bus.id, station_id] = c_start
                vars_dict["charge_end"][bus.id, station_id] = c_end

                # Define optional interval variable representing the charging time slot
                c_interval = model.NewOptionalIntervalVar(
                    c_start,
                    charging_duration,
                    c_end,
                    charge_act,
                    f"charge_interval_{bus.id}_{station_id}"
                )
                vars_dict["charge_interval"][bus.id, station_id] = c_interval

                # Wait time variable at this station
                w_time = model.NewIntVar(0, time_horizon, f"wait_{bus.id}_{station_id}")
                vars_dict["wait_time"][bus.id, station_id] = w_time

            # Total wait time for this bus
            total_w = model.NewIntVar(0, time_horizon, f"total_wait_{bus.id}")
            model.Add(total_w == sum(vars_dict["wait_time"][bus.id, s] for s in path[1:-1]))
            vars_dict["total_wait"][bus.id] = total_w

            # Delay for this bus (arrival time at destination - scheduled departure time - min travel time)
            # Find total route distance
            total_dist = sum(seg.distance_km for seg in route.segments)
            min_travel_time = int(round((total_dist / speed) * 60))
            
            dest_idx = len(path) - 1
            bus_delay = model.NewIntVar(0, time_horizon, f"delay_{bus.id}")
            model.Add(bus_delay == vars_dict["arrival"][bus.id, dest_idx] - dep_mins - min_travel_time)
            vars_dict["delay"][bus.id] = bus_delay

        # 3. Apply all active rules (Constraints & Objective construction)
        for rule in self.rules:
            logger.info(f"Applying rule: {rule.name}")
            rule.apply(model, scenario, vars_dict)

        # 4. Set the weighted objective function
        objective_terms = vars_dict["objective_terms"]
        if objective_terms:
            # We minimize the weighted sum of objective variables
            # Weight is scaled by 100 to handle float weights in CP-SAT (which requires integers)
            model.Minimize(
                sum(int(round(weight * 100)) * term for term, weight in objective_terms)
            )
        else:
            # Fallback if no soft rules were defined
            model.Minimize(0)

        # 5. Solve the model
        solver = CpSolver()
        solver.parameters.max_time_in_seconds = timeout_seconds
        
        status = solver.Solve(model)

        if status not in (OPTIMAL, FEASIBLE):
            status_name = solver.StatusName(status)
            raise RuntimeError(f"Solver failed to find a feasible schedule. Status: {status_name}")

        # 6. Parse solution and build output model
        bus_schedules: List[BusScheduleResult] = []
        
        for bus in scenario.buses:
            path = get_route_nodes(route, bus.direction)
            dep_mins = parse_time_to_mins(bus.departure_time)
            
            arrival_times_dict = {}
            departure_times_dict = {}
            battery_levels_dict = {}
            charge_events: List[ChargeEvent] = []

            for j in range(len(path)):
                node = path[j]
                arr_val = solver.Value(vars_dict["arrival"][bus.id, j])
                dep_val = solver.Value(vars_dict["departure"][bus.id, j])
                bat_val = solver.Value(vars_dict["battery"][bus.id, j])
                
                arrival_times_dict[node] = arr_val
                departure_times_dict[node] = dep_val
                battery_levels_dict[node] = float(bat_val)

            # Extract charge events
            for j in range(1, len(path) - 1):
                station_id = path[j]
                is_active = solver.Value(vars_dict["charge_active"][bus.id, station_id])
                
                if is_active:
                    arr_val = solver.Value(vars_dict["arrival"][bus.id, j])
                    c_start_val = solver.Value(vars_dict["charge_start"][bus.id, station_id])
                    c_end_val = solver.Value(vars_dict["charge_end"][bus.id, station_id])
                    w_time_val = solver.Value(vars_dict["wait_time"][bus.id, station_id])
                    
                    event = ChargeEvent(
                        bus_id=bus.id,
                        station_id=station_id,
                        arrival_time_mins=arr_val,
                        charge_start_mins=c_start_val,
                        charge_end_mins=c_end_val,
                        wait_time_mins=w_time_val,
                        charge_duration_mins=charging_duration
                    )
                    charge_events.append(event)

            # Sort charge events by start time just in case
            charge_events.sort(key=lambda x: x.charge_start_mins)

            bus_res = BusScheduleResult(
                bus_id=bus.id,
                operator=bus.operator,
                direction=bus.direction,
                departure_time_mins=dep_mins,
                arrival_time_mins=solver.Value(vars_dict["arrival"][bus.id, len(path)-1]),
                total_wait_time_mins=solver.Value(vars_dict["total_wait"][bus.id]),
                charge_events=charge_events,
                route_path=path,
                arrival_times=arrival_times_dict,
                departure_times=departure_times_dict,
                battery_levels=battery_levels_dict
            )
            bus_schedules.append(bus_res)

        # Calculate global metrics
        solved_total_wait = sum(sched.total_wait_time_mins for sched in bus_schedules)
        
        # Total network delay = sum of delays of all buses
        solved_total_delay = sum(solver.Value(vars_dict["delay"][bus.id]) for bus in scenario.buses)

        return ScheduleResult(
            scenario_id=scenario.id,
            bus_schedules=bus_schedules,
            total_wait_time=solved_total_wait,
            total_delay=solved_total_delay
        )
