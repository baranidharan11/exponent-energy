from typing import List
from scheduler.models import Route

def parse_time_to_mins(time_str: str) -> int:
    """Convert a time string like '19:15' to minutes from midnight (1155)."""
    parts = time_str.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])

def format_mins_to_time(mins: int) -> str:
    """Convert minutes from midnight to a string representation, e.g. 1155 -> '19:15'.
    If the time goes into the next day, appends (+1d), (+2d), etc."""
    days = mins // 1440
    rem_mins = mins % 1440
    hours = rem_mins // 60
    minutes = rem_mins % 60
    time_str = f"{hours:02d}:{minutes:02d}"
    if days > 0:
        time_str += f" (+{days}d)"
    return time_str

def get_route_nodes(route: Route, direction: str) -> List[str]:
    """Get the sequence of nodes along the route based on the travel direction."""
    # Build the default forward sequence from the segments order
    forward_nodes = []
    for seg in route.segments:
        if not forward_nodes:
            forward_nodes.append(seg.from_node)
        if seg.to_node not in forward_nodes:
            forward_nodes.append(seg.to_node)
            
    if not forward_nodes:
        return []
        
    start_node = forward_nodes[0]
    end_node = forward_nodes[-1]
    
    # Check if direction indicates reverse travel.
    direction_lower = direction.lower()
    start_lower = start_node.lower()
    end_lower = end_node.lower()
    
    is_reverse = False
    if end_lower in direction_lower and start_lower in direction_lower:
        if direction_lower.find(end_lower) < direction_lower.find(start_lower):
            is_reverse = True
    elif direction_lower.startswith(end_lower) or direction_lower.endswith(start_lower) or "←" in direction or "<-" in direction:
        is_reverse = True
        
    if is_reverse:
        return list(reversed(forward_nodes))
    return forward_nodes

def get_segment_distance(route: Route, from_node: str, to_node: str) -> float:
    """Find the distance between two nodes on the route.
    It supports lookup in either direction."""
    for seg in route.segments:
        if (seg.from_node == from_node and seg.to_node == to_node) or \
           (seg.from_node == to_node and seg.to_node == from_node):
            return seg.distance_km
    raise ValueError(f"No segment found between {from_node} and {to_node}")
