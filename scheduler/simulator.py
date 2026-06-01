from typing import List, Tuple, Dict
from scheduler.models import Scenario, ScheduleResult
from utils.helpers import get_route_nodes, get_segment_distance, parse_time_to_mins

class ScheduleSimulator:
    """Independent validator that simulates the solved schedule to ensure physical feasibility."""
    
    def validate(self, scenario: Scenario, result: ScheduleResult) -> Tuple[bool, List[str]]:
        """Simulate and validate the schedule result.
        
        Args:
            scenario: The original Scenario input.
            result: The ScheduleResult output.
            
        Returns:
            Tuple of (is_valid: bool, error_messages: List[str])
        """
        errors = []
        
        # Create quick-lookup map for bus schedules
        bus_sched_map = {sched.bus_id: sched for sched in result.bus_schedules}
        
        # 1. Validate route travel times, station departures, and segment battery levels for each bus
        for bus in scenario.buses:
            if bus.id not in bus_sched_map:
                errors.append(f"Bus {bus.id} is missing from the schedule results.")
                continue
                
            sched = bus_sched_map[bus.id]
            path = get_route_nodes(scenario.route, bus.direction)
            dep_mins = parse_time_to_mins(bus.departure_time)
            
            # Verify origin departure time
            start_dep = sched.departure_times.get(path[0])
            if start_dep != dep_mins:
                errors.append(f"Bus {bus.id} starting departure time {start_dep} does not match scenario departure time {dep_mins}.")
                
            curr_battery = bus.max_range_km
            
            for j in range(len(path) - 1):
                from_node = path[j]
                to_node = path[j+1]
                
                try:
                    dist = get_segment_distance(scenario.route, from_node, to_node)
                except ValueError as e:
                    errors.append(f"Bus {bus.id} segment {from_node}->{to_node}: {str(e)}")
                    continue
                
                # Check if battery has enough range to reach the next stop
                if curr_battery < dist:
                    errors.append(
                        f"Bus {bus.id} ran out of battery on segment {from_node} -> {to_node}. "
                        f"Battery level: {curr_battery} km, segment distance: {dist} km."
                    )
                
                curr_battery -= dist
                
                # Validate travel time based on distance and speed (60 km/h)
                travel_time = int(round((dist / scenario.travel_speed_kmh) * 60))
                arr_node = sched.arrival_times.get(to_node)
                dep_prev = sched.departure_times.get(from_node)
                
                if arr_node is None or dep_prev is None:
                    errors.append(f"Bus {bus.id} has missing arrival/departure times at segment {from_node} -> {to_node}.")
                    continue
                    
                if arr_node != dep_prev + travel_time:
                    errors.append(
                        f"Bus {bus.id} segment {from_node} -> {to_node} travel time mismatch: "
                        f"arrived at {arr_node}, departed {from_node} at {dep_prev}, "
                        f"expected travel time: {travel_time} mins, actual travel time: {arr_node - dep_prev} mins."
                    )
                
                # Intermediate station behavior check
                if j+1 < len(path) - 1:
                    station_id = path[j+1]
                    
                    # See if there is a charge event at this station
                    charge_ev = next((ev for ev in sched.charge_events if ev.station_id == station_id), None)
                    dep_node = sched.departure_times.get(station_id)
                    
                    if charge_ev:
                        # Battery charges to full
                        curr_battery = bus.max_range_km
                        
                        # Validate charge times
                        if charge_ev.charge_end_mins != charge_ev.charge_start_mins + charge_ev.charge_duration_mins:
                            errors.append(
                                f"Bus {bus.id} at station {station_id} charging duration mismatch. "
                                f"Start: {charge_ev.charge_start_mins}, End: {charge_ev.charge_end_mins}, "
                                f"expected duration: {charge_ev.charge_duration_mins} mins."
                            )
                        
                        if charge_ev.charge_start_mins < arr_node:
                            errors.append(
                                f"Bus {bus.id} at station {station_id} started charging at {charge_ev.charge_start_mins} "
                                f"before arrival time {arr_node}."
                            )
                            
                        if dep_node != charge_ev.charge_end_mins:
                            errors.append(
                                f"Bus {bus.id} at station {station_id} departed at {dep_node} "
                                f"which does not match charge end time {charge_ev.charge_end_mins}."
                            )
                    else:
                        # Did not charge: departure must equal arrival
                        if dep_node != arr_node:
                            errors.append(
                                f"Bus {bus.id} at station {station_id} did not charge, "
                                f"but departure time {dep_node} does not match arrival time {arr_node}."
                            )

        # 2. Validate charger overlaps at stations
        for station in scenario.stations:
            # Find all charging intervals at this station
            intervals: List[Tuple[int, int, str]] = []
            for sched in result.bus_schedules:
                ev = next((e for e in sched.charge_events if e.station_id == station.id), None)
                if ev:
                    intervals.append((ev.charge_start_mins, ev.charge_end_mins, sched.bus_id))
            
            # Sort intervals by start time
            intervals.sort(key=lambda x: x[0])
            
            # Check for capacity violations at any point in time
            for idx, (start, end, bus_id) in enumerate(intervals):
                concurrent_charges = 1
                for o_idx in range(idx + 1, len(intervals)):
                    o_start, o_end, o_bus_id = intervals[o_idx]
                    
                    # If the other charge starts before this one ends, it overlaps
                    if o_start < end:
                        concurrent_charges += 1
                        if concurrent_charges > station.chargers_count:
                            errors.append(
                                f"Station {station.id} charger capacity exceeded. "
                                f"Buses {bus_id} and {o_bus_id} are charging concurrently. "
                                f"Max chargers: {station.chargers_count}."
                            )
        
        return len(errors) == 0, errors
