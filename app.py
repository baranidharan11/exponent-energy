import streamlit as st
from pathlib import Path

from scheduler.optimizer import ScheduleOptimizer
from scheduler.simulator import ScheduleSimulator
from utils.loader import load_scenario_from_file

# Import modularized UI functions
from ui import (
    inject_custom_css,
    render_sidebar,
    render_scenario_details_tab,
    render_bus_schedule_tab,
    render_station_schedule_tab
)

# Set page config
st.set_page_config(
    page_title="Exponent Energy - Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Locate scenario directory
SCENARIO_DIR = Path("data")

# Find all scenario*.json files dynamically
scenario_files = sorted(list(SCENARIO_DIR.glob("*.json")))

# Initialize session state for scenario selection and edits
if "active_scenario" not in st.session_state:
    st.session_state.selected_file = scenario_files[0] if scenario_files else None
    if st.session_state.selected_file:
        st.session_state.active_scenario = load_scenario_from_file(str(st.session_state.selected_file))
    else:
        st.session_state.active_scenario = None
    st.session_state.scenario_edited = False

# Render Sidebar controls and manage state updates
dark_mode, custom_weights = render_sidebar(scenario_files, SCENARIO_DIR)

# Inject custom CSS styling and retrieve the appropriate Plotly theme configurations
plotly_theme = inject_custom_css(dark_mode)

# Application Header
st.markdown('<div class="main-title">⚡ Exponent Energy</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Electric Bus Charging Scheduler & Fleet Optimizer</div>', unsafe_allow_html=True)
st.markdown('<div class="header-accent"></div>', unsafe_allow_html=True)

# Run the Solver & Simulator if a scenario is active
base_scenario = st.session_state.active_scenario
if base_scenario:
    optimizer = ScheduleOptimizer()
    simulator = ScheduleSimulator()

    with st.spinner("Optimizing schedule via OR-Tools CP-SAT solver..."):
        try:
            # Solve with custom weights
            schedule_result = optimizer.optimize(base_scenario, custom_weights)
            is_valid, validation_errors = simulator.validate(base_scenario, schedule_result)
        except Exception as e:
            st.error(f"Solver Error: {e}")
            st.stop()

    # Display solve status
    if is_valid:
        st.success("✨ Optimization complete! A physically feasible, optimal schedule was resolved.")
    else:
        st.warning("⚠️ Schedule resolved but simulator flagged validation warnings:")
        for err in validation_errors:
            st.write(f"- {err}")

    # Create UI Tabs
    tab1, tab2, tab3 = st.tabs([
        "📂 Scenario Details",
        "🚌 Bus Schedule & Timetable",
        "🚉 Station Queue & Charger View"
    ])

    # Render contents of each tab using the ui module
    with tab1:
        render_scenario_details_tab(base_scenario)

    with tab2:
        render_bus_schedule_tab(schedule_result, base_scenario, dark_mode, plotly_theme, optimizer)

    with tab3:
        render_station_schedule_tab(schedule_result, base_scenario, plotly_theme)
else:
    st.info("No active scenario. Please choose or upload a valid scenario JSON.")
