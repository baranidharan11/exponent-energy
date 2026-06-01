from typing import Dict, Tuple, Any, Optional
from scheduler.engine import SchedulingEngine
from scheduler.models import Scenario, ScheduleResult

class ScheduleOptimizer:
    def __init__(self, engine: Optional[SchedulingEngine] = None):
        """Initialize the optimizer wrapper around the scheduling engine."""
        self.engine = engine or SchedulingEngine()

    def optimize(self, scenario: Scenario, custom_weights: Optional[Dict[str, float]] = None) -> ScheduleResult:
        """Run the scheduling engine, optionally overriding scenario weights.
        
        Args:
            scenario: The base Scenario Pydantic model.
            custom_weights: Optional dict overrides for weights: 'individual', 'operator', 'overall'.
            
        Returns:
            ScheduleResult Pydantic model.
        """
        if custom_weights:
            # Create a copy with modified weights
            scenario_copy = scenario.model_copy(deep=True)
            scenario_copy.weights.individual = custom_weights.get("individual", scenario.weights.individual)
            scenario_copy.weights.operator = custom_weights.get("operator", scenario.weights.operator)
            scenario_copy.weights.overall = custom_weights.get("overall", scenario.weights.overall)
            return self.engine.solve(scenario_copy)
        
        return self.engine.solve(scenario)

    def run_sensitivity_analysis(self, scenario: Scenario) -> Dict[str, Dict[str, Any]]:
        """Perform sensitivity analysis by running the scheduler with different 
        weight profiles to demonstrate how objectives trade off against each other.
        
        Args:
            scenario: The input Scenario.
            
        Returns:
            Dict mapping profile names to summary metrics.
        """
        profiles = {
            "Balanced (1:1:1)": {"individual": 1.0, "operator": 1.0, "overall": 1.0},
            "Individual-Heavy (5:1:1)": {"individual": 5.0, "operator": 1.0, "overall": 1.0},
            "Operator-Heavy (1:5:1)": {"individual": 1.0, "operator": 5.0, "overall": 1.0},
            "Network-Heavy (1:1:5)": {"individual": 1.0, "operator": 1.0, "overall": 5.0}
        }
        
        analysis_results = {}
        for profile_name, weights in profiles.items():
            try:
                res = self.optimize(scenario, custom_weights=weights)
                analysis_results[profile_name] = {
                    "feasible": True,
                    "total_wait_time_mins": res.total_wait_time,
                    "total_delay_mins": res.total_delay,
                    "max_bus_wait_mins": max(b.total_wait_time_mins for b in res.bus_schedules) if res.bus_schedules else 0
                }
            except Exception as e:
                analysis_results[profile_name] = {
                    "feasible": False,
                    "error": str(e)
                }
        return analysis_results
