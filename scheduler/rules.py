from abc import ABC, abstractmethod
from ortools.sat.python.cp_model import CpModel
from scheduler.models import Scenario
from typing import Dict, Any, List
from utils.helpers import get_route_nodes, get_segment_distance

class Rule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the rule."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the description of the rule."""
        pass

    @abstractmethod
    def apply(self, model: CpModel, scenario: Scenario, vars_dict: Dict[str, Any]) -> None:
        """Apply the rule to the CP-SAT model.
        
        Args:
            model: The CP-SAT CpModel object.
            scenario: The input Scenario data.
            vars_dict: A dictionary containing all decision variables and mapping structures.
        """
        pass

# ----------------- HARD RULES -----------------

class RouteOrderRule(Rule):
    @property
    def name(self) -> str:
        return "RouteOrderRule"

    @property
    def description(self) -> str:
        return "Ensures buses follow route order, travel times are respected, and arrival/departure times at stations are linked."

    def apply(self, model: CpModel, scenario: Scenario, vars_dict: Dict[str, Any]) -> None:
        buses = scenario.buses
        route = scenario.route
        speed = scenario.travel_speed_kmh
        charging_duration = int(scenario.charging_duration_mins)

        # Retrieve variables from vars_dict
        arrival = vars_dict["arrival"]
        departure = vars_dict["departure"]
        charge_active = vars_dict["charge_active"]
        charge_start = vars_dict["charge_start"]
        charge_end = vars_dict["charge_end"]
        wait_time = vars_dict["wait_time"]

        for i, bus in enumerate(buses):
            path = get_route_nodes(route, bus.direction)
            
            # 1. Start departure matches scheduled departure time.
            # We already set arrival[bus.id, 0] = departure[bus.id, 0] = dep_time_mins in variables creation.
            # Let's ensure this constraint.
            
            # 2. Link stop arrivals and departures
            for j in range(len(path) - 1):
                from_node = path[j]
                to_node = path[j+1]
                dist = get_segment_distance(route, from_node, to_node)
                travel_time = int(round((dist / speed) * 60)) # in minutes

                # Arrival at next stop is departure from current stop + travel time
                model.Add(arrival[bus.id, j+1] == departure[bus.id, j] + travel_time)

            # 3. For intermediate stations (stops 1 to 4), model charging behavior
            for j in range(1, len(path) - 1):
                station_id = path[j]
                
                # Check if this station is configured in scenario.
                # In our case, stations are A, B, C, D.
                
                # Case 1: Bus charges at this station (charge_active is 1)
                # - Charge start must be after arrival: charge_start >= arrival
                # - Charge end is charge_start + duration: charge_end == charge_start + duration (handled by interval definition)
                # - Departure is charge_end: departure == charge_end
                # - Wait time is charge_start - arrival
                model.Add(charge_start[bus.id, station_id] >= arrival[bus.id, j]).OnlyEnforceIf(charge_active[bus.id, station_id])
                model.Add(departure[bus.id, j] == charge_end[bus.id, station_id]).OnlyEnforceIf(charge_active[bus.id, station_id])
                model.Add(wait_time[bus.id, station_id] == charge_start[bus.id, station_id] - arrival[bus.id, j]).OnlyEnforceIf(charge_active[bus.id, station_id])

                # Case 2: Bus does not charge at this station (charge_active is 0)
                # - Departure equals arrival: departure == arrival
                # - Wait time is 0
                model.Add(departure[bus.id, j] == arrival[bus.id, j]).OnlyEnforceIf(charge_active[bus.id, station_id].Not())
                model.Add(wait_time[bus.id, station_id] == 0).OnlyEnforceIf(charge_active[bus.id, station_id].Not())


class BatteryRangeRule(Rule):
    @property
    def name(self) -> str:
        return "BatteryRangeRule"

    @property
    def description(self) -> str:
        return "Ensures buses do not run out of battery. Distance since last charge must not exceed max range."

    def apply(self, model: CpModel, scenario: Scenario, vars_dict: Dict[str, Any]) -> None:
        buses = scenario.buses
        route = scenario.route
        
        battery = vars_dict["battery"]
        charge_active = vars_dict["charge_active"]

        for i, bus in enumerate(buses):
            path = get_route_nodes(route, bus.direction)
            max_range = int(bus.max_range_km)

            # Initially after departure from stop 0, remaining range is full.
            # We already set battery[bus.id, 0] = max_range in variables creation.
            
            # Transition for each segment
            for j in range(len(path) - 1):
                from_node = path[j]
                to_node = path[j+1]
                dist = int(round(get_segment_distance(route, from_node, to_node)))

                # Hard constraint: battery level after departing stop j must be enough to cover the distance to stop j+1.
                model.Add(battery[bus.id, j] >= dist)

                # Battery level *after* departing stop j+1:
                # If stop j+1 is the destination (last stop), no charger exists, battery level is just battery[j] - dist.
                if j+1 == len(path) - 1:
                    model.Add(battery[bus.id, j+1] == battery[bus.id, j] - dist)
                else:
                    station_id = path[j+1]
                    # If charges at station_id: battery level becomes max_range
                    model.Add(battery[bus.id, j+1] == max_range).OnlyEnforceIf(charge_active[bus.id, station_id])
                    # If doesn't charge: battery level is battery[j] - dist
                    model.Add(battery[bus.id, j+1] == battery[bus.id, j] - dist).OnlyEnforceIf(charge_active[bus.id, station_id].Not())


class NoOverlapRule(Rule):
    @property
    def name(self) -> str:
        return "NoOverlapRule"

    @property
    def description(self) -> str:
        return "Ensures chargers at stations are not over-allocated. Only one bus per charger at a time."

    def apply(self, model: CpModel, scenario: Scenario, vars_dict: Dict[str, Any]) -> None:
        stations = scenario.stations
        buses = scenario.buses
        route = scenario.route

        charge_intervals = vars_dict["charge_interval"]

        for station in stations:
            # Gather all optional intervals at this station across all buses
            intervals_at_station = []
            for bus in buses:
                # A bus only visits a station if it is along its route direction.
                path = get_route_nodes(route, bus.direction)
                if station.id in path[1:-1]: # ignore endpoints
                    intervals_at_station.append(charge_intervals[bus.id, station.id])

            if intervals_at_station:
                if station.chargers_count == 1:
                    # Single charger: no overlaps
                    model.AddNoOverlap(intervals_at_station)
                else:
                    # Multiple chargers: cumulative constraint
                    demands = [1] * len(intervals_at_station)
                    model.AddCumulative(intervals_at_station, demands, station.chargers_count)


# ----------------- SOFT RULES / OBJECTIVES -----------------

class MinIndividualWaitRule(Rule):
    @property
    def name(self) -> str:
        return "MinIndividualWaitRule"

    @property
    def description(self) -> str:
        return "Minimize individual bus waiting time by penalizing the maximum wait time of any bus."

    def apply(self, model: CpModel, scenario: Scenario, vars_dict: Dict[str, Any]) -> None:
        buses = scenario.buses
        total_wait = vars_dict["total_wait"]
        
        # We define a variable to represent the maximum wait time across all buses
        max_wait = model.NewIntVar(0, 5000, "max_individual_wait_time")
        
        for bus in buses:
            model.Add(max_wait >= total_wait[bus.id])
            
        # Add to objective terms: (variable, weight)
        vars_dict["objective_terms"].append((max_wait, scenario.weights.individual))
        vars_dict["max_individual_wait_var"] = max_wait


class OperatorFairnessRule(Rule):
    @property
    def name(self) -> str:
        return "OperatorFairnessRule"

    @property
    def description(self) -> str:
        return "Maintains fairness among operators by minimizing the maximum difference between operators' average wait times."

    def apply(self, model: CpModel, scenario: Scenario, vars_dict: Dict[str, Any]) -> None:
        buses = scenario.buses
        total_wait = vars_dict["total_wait"]

        # Group buses by operator
        op_buses = {}
        for bus in buses:
            op_buses.setdefault(bus.operator, []).append(bus)

        operators = list(op_buses.keys())
        if len(operators) <= 1:
            # Fairness is trivially satisfied if there is 1 or 0 operators
            return

        # Define variables for each operator's average wait time
        op_avg_wait = {}
        for op, fleet in op_buses.items():
            op_total_wait = model.NewIntVar(0, 100000, f"total_wait_{op}")
            model.Add(op_total_wait == sum(total_wait[bus.id] for bus in fleet))
            
            avg_wait = model.NewIntVar(0, 5000, f"avg_wait_{op}")
            # integer division avg_wait == op_total_wait // len(fleet)
            model.AddDivisionEquality(avg_wait, op_total_wait, len(fleet))
            op_avg_wait[op] = avg_wait

        # Define a variable for max difference between operator averages
        max_op_diff = model.NewIntVar(0, 5000, "max_operator_wait_diff")
        
        for i in range(len(operators)):
            for j in range(i + 1, len(operators)):
                op1 = operators[i]
                op2 = operators[j]
                model.Add(max_op_diff >= op_avg_wait[op1] - op_avg_wait[op2])
                model.Add(max_op_diff >= op_avg_wait[op2] - op_avg_wait[op1])

        # Add to objective terms
        vars_dict["objective_terms"].append((max_op_diff, scenario.weights.operator))
        vars_dict["operator_fairness_var"] = max_op_diff


class MinNetworkDelayRule(Rule):
    @property
    def name(self) -> str:
        return "MinNetworkDelayRule"

    @property
    def description(self) -> str:
        return "Minimizes the overall network delay (sum of arrival delays of all buses)."

    def apply(self, model: CpModel, scenario: Scenario, vars_dict: Dict[str, Any]) -> None:
        buses = scenario.buses
        delay = vars_dict["delay"]

        # Sum of delays of all buses
        total_delay = model.NewIntVar(0, 100000, "total_network_delay")
        model.Add(total_delay == sum(delay[bus.id] for bus in buses))

        # Add to objective terms
        vars_dict["objective_terms"].append((total_delay, scenario.weights.overall))
        vars_dict["total_delay_var"] = total_delay
