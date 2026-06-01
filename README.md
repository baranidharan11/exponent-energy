# ⚡ Exponent Energy Bus Charging Scheduler

A production-quality electric bus charging scheduler web application built with **Python 3.11+**, **Streamlit**, and **Google OR-Tools CP-SAT**.

The application models and schedules electric bus charging timelines across a shared route with chargers, optimizing for waiting time, operator fairness, and network delay.

---

## 🚀 Quick Start

### 1. Prerequisite
Ensure you have Python 3.11+ installed.

### 2. Install Dependencies
Install all required python packages:
```bash
pip install -r requirements.txt
```

### 3. Run Locally
Start the Streamlit dashboard:
```bash
streamlit run app.py
```
This will spin up a local development server (usually at `http://localhost:8501`) and open the application in your browser.

---

## 🛠️ Project Structure

The project has a modular, scalable architecture separating model definitions, rules engine, solver logic, scenario configurations, and UI representation.

```text
exponent-energy/
│
├── app.py                     # Streamlit web application & UI representation
│
├── scheduler/
│   ├── models.py              # Pydantic data models for input and output validation
│   ├── engine.py              # CP-SAT constraint programming solver core
│   ├── rules.py               # Pluggable rule system (hard constraints & soft objectives)
│   ├── optimizer.py           # ScheduleOptimizer (weight overrides & sensitivity analysis)
│   └── simulator.py           # State-machine simulator validating output correctness
│
├── data/
│   ├── scenario1.json         # Scenario 1 - Even Spacing
│   ├── scenario2.json         # Scenario 2 - Bunched Start
│   ├── scenario3.json         # Scenario 3 - Asymmetric Load
│   ├── scenario4.json         # Scenario 4 - Operator-Heavy
│   └── scenario5.json         # Scenario 5 - Worst Case Convergence
│
├── utils/
│   ├── loader.py              # JSON loaders with validation
│   └── helpers.py             # Time parsing, time formatting, and route helper utilities
│
├── requirements.txt           # Project dependencies
├── ARCHITECTURE.md            # In-depth architectural design and modeling decisions
└── README.md                  # This file
```

---

## 🎨 Streamlit UI Features

The interface is custom-styled with Exponent's dark & orange themes and features three tabs:
1. **📂 Scenario Details**:
   - Visual summary of scenario configurations.
   - Route segments layout.
   - Interactive expander displaying the raw scenario JSON file content.
2. **🚌 Bus Schedule & Timetable**:
   - High-level metric cards (`Total Delay`, `Total Wait Time`, `Max Individual Wait`, `Charges Completed`).
   - Interactive, searchable, and sortable Bus Timetable.
   - Beautiful, color-coded **Plotly Gantt Chart** displaying the timeline for each bus (Traveling, Waiting in queue, Charging).
   - Sensitivity Analysis comparison table comparing the active weights against alternative profiles.
   - CSV and JSON exporters for schedule outputs.
3. **🚉 Station Schedule**:
   - Chronological queue ordering for all stations (A, B, C, D) specifying queue positions.
   - Station Charger Utilization metrics table.
   - Station Occupancy Gantt Chart showing charger occupancy time slots.

---

## ⚖️ Tuning Objectives and Weights

The solver optimizes a weighted combination of three distinct objectives:
1. **Individual Bus Wait (`weights.individual`)**: Minimizes the maximum wait time experienced by any single bus.
2. **Operator Fairness (`weights.operator`)**: Minimizes the difference between operators' average wait times.
3. **Overall Network Delay (`weights.overall`)**: Minimizes the total delay (charging + waiting time) across the fleet.

### Method A: Interactive Tuning (Streamlit UI)
Adjust the sliders in the sidebar. The scheduler re-optimizes the timeline and updates charts in real-time.

### Method B: Scenario Weight Config File
Edit the `"weights"` dictionary in any scenario JSON file under `data/`:
```json
"weights": {
  "individual": 1.0,
  "operator": 2.0,
  "overall": 1.0
}
```
The scheduler reads these default weights upon loading the scenario.

---

## ➕ Adding a New Scenario

To add a new scenario, create a JSON file `data/scenarioX.json`. The engine validates the file using Pydantic. Ensure it follows the schema:

```json
{
  "id": "custom-scenario",
  "name": "Custom Operational Case",
  "description": "Custom scenario explanation.",
  "route": {
    "id": "route-01",
    "name": "Main Route",
    "segments": [
      {"from_node": "Bengaluru", "to_node": "A", "distance_km": 100.0},
      {"from_node": "A", "to_node": "B", "distance_km": 120.0},
      {"from_node": "B", "to_node": "C", "distance_km": 100.0},
      {"from_node": "C", "to_node": "D", "distance_km": 120.0},
      {"from_node": "D", "to_node": "Kochi", "distance_km": 100.0}
    ]
  },
  "stations": [
    {"id": "A", "name": "Station A", "chargers_count": 1},
    {"id": "B", "name": "Station B", "chargers_count": 1},
    {"id": "C", "name": "Station C", "chargers_count": 1},
    {"id": "D", "name": "Station D", "chargers_count": 1}
  ],
  "buses": [
    {
      "id": "bus-01",
      "operator": "kpn",
      "direction": "Bengaluru→Kochi",
      "departure_time": "19:00",
      "priority": 1,
      "max_range_km": 240.0
    }
  ],
  "weights": {
    "individual": 1.0,
    "operator": 1.0,
    "overall": 1.0
  },
  "charging_duration_mins": 25.0,
  "travel_speed_kmh": 60.0
}
```

---

## 🧩 Adding a New Scheduling Rule

Rules are implemented using the **Rule Engine Pattern**. 

To add a new constraint or objective:
1. Define a class inheriting from `Rule` in `scheduler/rules.py`.
2. Implement the `apply(self, model, scenario, vars_dict)` method.
3. Register the rule in `scheduler/engine.py` within `__init__`.

Example: Adding a hard rule that prohibits certain operators from charging at Station A:
```python
# scheduler/rules.py
class ProhibitOperatorAtStationARule(Rule):
    @property
    def name(self) -> str:
        return "ProhibitOperatorAtStationARule"

    @property
    def description(self) -> str:
        return "Prohibits flixbus from charging at Station A."

    def apply(self, model, scenario, vars_dict) -> None:
        charge_active = vars_dict["charge_active"]
        for bus in scenario.buses:
            if bus.operator == "flixbus":
                # Enforce that flixbus charge state at A is always 0
                model.Add(charge_active[bus.id, "A"] == 0)
```
Then register it inside `scheduler/engine.py`:
```diff
# scheduler/engine.py
             self.rules = [
                 RouteOrderRule(),
                 BatteryRangeRule(),
                 NoOverlapRule(),
+                ProhibitOperatorAtStationARule(),
                 MinIndividualWaitRule(),
                 OperatorFairnessRule(),
                 MinNetworkDelayRule()
             ]
```

---

## ☁️ Deployment

Deploy this repository directly to **Streamlit Community Cloud** in two steps:
1. Push the code to a public GitHub repository.
2. Log in to [Streamlit Share](https://share.streamlit.io/) and select **"Deploy an app"**.
3. Choose the repository, branch, and select `app.py` as the entrypoint. Streamlit will install packages from `requirements.txt` and launch the app.
