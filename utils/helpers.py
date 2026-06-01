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
    # Build the path from segments.
    # Bengaluru -> Kochi: Bengaluru, A, B, C, D, Kochi
    # Kochi -> Bengaluru: Kochi, D, C, B, A, Bengaluru
    if "Bengaluru→Kochi" in direction or direction.lower().startswith("b"):
        return ["Bengaluru", "A", "B", "C", "D", "Kochi"]
    elif "Kochi→Bengaluru" in direction or direction.lower().startswith("k"):
        return ["Kochi", "D", "C", "B", "A", "Bengaluru"]
    else:
        # Generic fallback
        nodes = []
        for seg in route.segments:
            if not nodes:
                nodes.append(seg.from_node)
            nodes.append(seg.to_node)
        return nodes

def get_segment_distance(route: Route, from_node: str, to_node: str) -> float:
    """Find the distance between two nodes on the route.
    It supports lookup in either direction."""
    for seg in route.segments:
        if (seg.from_node == from_node and seg.to_node == to_node) or \
           (seg.from_node == to_node and seg.to_node == from_node):
            return seg.distance_km
    raise ValueError(f"No segment found between {from_node} and {to_node}")
