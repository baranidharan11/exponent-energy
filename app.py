import streamlit as st
import pandas as pd
import json
import datetime
from pathlib import Path
import plotly.express as px

from scheduler.models import Scenario
from scheduler.engine import SchedulingEngine
from scheduler.optimizer import ScheduleOptimizer
from scheduler.simulator import ScheduleSimulator
from utils.loader import load_scenario_by_id, load_scenario_from_file
from utils.helpers import format_mins_to_time, get_route_nodes

# Set page config
st.set_page_config(
    page_title="Exponent Energy - Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar Configuration
st.sidebar.header("🔧 Scheduler Controls")

# Light/Dark Mode Selector
dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=True)

# Custom Exponent-themed styling based on theme selection
if dark_mode:
    theme_vars = """
    :root {
        --bg-gradient: linear-gradient(135deg, #0A0C16 0%, #151829 100%);
        --text-color: #F1F5F9;
        --sidebar-bg: #0A0C16;
        --card-bg: rgba(22, 28, 48, 0.7);
        --card-border: 1px solid rgba(255, 87, 34, 0.2);
        --card-hover-border: rgba(255, 107, 53, 0.55);
        --card-hover-shadow: 0 10px 30px rgba(255, 107, 53, 0.15);
        --row-even-bg: #141A29;
        --row-odd-bg: #1C2438;
        --border-color: rgba(255, 255, 255, 0.08);
        --title-color: #FF6B35;
        --subtitle-color: #94A3B8;
        --slider-track: #2D334A;
    }
    """
    plotly_template = "plotly_dark"
    plotly_bg = "rgba(0,0,0,0)"
    plotly_grid = "rgba(255, 255, 255, 0.08)"
    plotly_text = "#F1F5F9"
else:
    theme_vars = """
    :root {
        --bg-gradient: linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 100%);
        --text-color: #0F172A;
        --sidebar-bg: #FFFFFF;
        --card-bg: rgba(255, 255, 255, 0.85);
        --card-border: 1px solid rgba(255, 87, 34, 0.15);
        --card-hover-border: rgba(255, 87, 34, 0.45);
        --card-hover-shadow: 0 10px 30px rgba(255, 87, 34, 0.1);
        --row-even-bg: #FFFFFF;
        --row-odd-bg: #F1F5F9;
        --border-color: rgba(0, 0, 0, 0.08);
        --title-color: #E64A19;
        --subtitle-color: #475569;
        --slider-track: #E2E8F0;
    }
    """
    plotly_template = "plotly_white"
    plotly_bg = "rgba(0,0,0,0)"
    plotly_grid = "rgba(0, 0, 0, 0.08)"
    plotly_text = "#0F172A"

st.markdown(f"""
    <style>
    {theme_vars}
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;600;800&display=swap');
    
    /* Main Layout and Title Styles */
    .stApp {{
        background: var(--bg-gradient) !important;
        color: var(--text-color) !important;
        font-family: 'Inter', sans-serif !important;
    }}
    
    div[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border-color) !important;
    }}
    
    .main-title {{
        font-family: 'Outfit', sans-serif !important;
        color: var(--title-color) !important;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    
    .subtitle {{
        font-family: 'Inter', sans-serif;
        color: var(--subtitle-color);
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }}
    
    /* Metric Card Styling */
    div[data-testid="stMetric"] {{
        background-color: var(--card-bg) !important;
        border: var(--card-border) !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-4px) !important;
        border-color: var(--card-hover-border) !important;
        box-shadow: var(--card-hover-shadow) !important;
    }}
    
    div[data-testid="stMetric"] label {{
        color: var(--subtitle-color) !important;
        font-weight: 600;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: var(--text-color) !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        font-family: 'Outfit', sans-serif !important;
    }}
    
    /* Tabs custom styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 24px;
        background-color: transparent !important;
        border-bottom: 2px solid var(--border-color) !important;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent !important;
        border-bottom: 2px solid transparent !important;
        color: var(--subtitle-color) !important;
        font-size: 1.05rem;
        font-weight: 600;
        padding: 10px 16px;
        transition: all 0.3s ease !important;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        color: var(--title-color) !important;
    }}
    
    .stTabs [aria-selected="true"] {{
        color: var(--title-color) !important;
        border-bottom-color: var(--title-color) !important;
    }}
    
    /* Header background accent */
    .header-accent {{
        height: 4px;
        background: linear-gradient(90deg, #FF5722 0%, #FFC107 100%);
        border-radius: 2px;
        margin-bottom: 1.5rem;
    }}
    
    /* Table Styling */
    table {{
        border-collapse: collapse !important;
        width: 100% !important;
        margin: 10px 0 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        border: 1px solid var(--border-color) !important;
    }}
    
    th {{
        background: linear-gradient(90deg, #FF5722 0%, #FF8A65 100%) !important;
        color: white !important;
        font-family: 'Outfit', sans-serif !important;
        text-transform: uppercase !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.5px !important;
        padding: 12px 15px !important;
        border: none !important;
    }}
    
    tbody tr:nth-child(even) {{
        background-color: var(--row-even-bg) !important;
    }}
    
    tbody tr:nth-child(odd) {{
        background-color: var(--row-odd-bg) !important;
    }}
    
    td {{
        color: var(--text-color) !important;
        padding: 10px 15px !important;
        border-bottom: 1px solid var(--border-color) !important;
        font-size: 0.9rem !important;
    }}
    
    /* Button Customization */
    div.stButton > button {{
        background: linear-gradient(90deg, #FF5722 0%, #FF8A65 100%) !important;
        color: white !important;
        border: none !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(255, 87, 34, 0.3) !important;
    }}
    
    div.stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 87, 34, 0.5) !important;
        color: white !important;
    }}
    
    div.stButton > button:active {{
        transform: translateY(0) !important;
    }}
    
    /* Text inputs, select boxes, expanders */
    div[data-testid="stExpander"] {{
        background-color: var(--card-bg) !important;
        border: var(--card-border) !important;
        border-radius: 8px !important;
    }}
    
    div[data-testid="stWidgetLabel"] p {{
        color: var(--text-color) !important;
        font-weight: 500 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# Application Header
st.markdown('<div class="main-title">⚡ Exponent Energy</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Electric Bus Charging Scheduler & Fleet Optimizer</div>', unsafe_allow_html=True)
st.markdown('<div class="header-accent"></div>', unsafe_allow_html=True)

# Locate scenario directory
SCENARIO_DIR = Path("data")

# Scenario Selection
scenario_ids = [1, 2, 3, 4, 5]
selected_scenario_id = st.sidebar.selectbox(
    "Select Scenario",
    scenario_ids,
    format_func=lambda x: f"Scenario {x}"
)

# Load base scenario to read default weights
try:
    base_scenario = load_scenario_by_id(str(SCENARIO_DIR), selected_scenario_id)
except Exception as e:
    st.error(f"Error loading scenario data: {e}")
    st.stop()

st.sidebar.markdown("### ⚖️ Optimization Weights")
st.sidebar.info(
    "Tune these weights to adjust the scheduler's behavior. "
    "Higher weights prioritize that specific objective."
)

# Sliders for weight override
w_individual = st.sidebar.slider(
    "Individual Bus Wait Weight",
    min_value=0.0,
    max_value=10.0,
    value=float(base_scenario.weights.individual),
    step=0.5,
    help="Minimizes the maximum wait time experienced by any single bus."
)

w_operator = st.sidebar.slider(
    "Operator Fairness Weight",
    min_value=0.0,
    max_value=10.0,
    value=float(base_scenario.weights.operator),
    step=0.5,
    help="Minimizes the difference between operators' average wait times."
)

w_overall = st.sidebar.slider(
    "Network Delay Weight",
    min_value=0.0,
    max_value=10.0,
    value=float(base_scenario.weights.overall),
    step=0.5,
    help="Minimizes the total overall trip delay across the entire network."
)

# Reset Button
if st.sidebar.button("Reset to Scenario Defaults"):
    w_individual = base_scenario.weights.individual
    w_operator = base_scenario.weights.operator
    w_overall = base_scenario.weights.overall
    st.rerun()

custom_weights = {
    "individual": w_individual,
    "operator": w_operator,
    "overall": w_overall
}

# Run the Solver & Simulator
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

# Create tabs
tab1, tab2, tab3 = st.tabs([
    "📂 Scenario Details",
    "🚌 Bus Schedule & Timetable",
    "🚉 Station Queue & Charger View"
])

# ----------------- TAB 1: SCENARIO DETAILS -----------------
with tab1:
    st.subheader(base_scenario.name)
    st.caption(base_scenario.description)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ⚙️ Scenario Constraints")
        meta_df = pd.DataFrame([
            {"Parameter": "Battery Capacity / Range", "Value": f"{base_scenario.buses[0].max_range_km} km"},
            {"Parameter": "Charging Duration (to 100%)", "Value": f"{base_scenario.charging_duration_mins} mins"},
            {"Parameter": "Default Segment Travel Speed", "Value": f"{base_scenario.travel_speed_kmh} km/h"},
            {"Parameter": "Active Station Chargers", "Value": f"{len(base_scenario.stations)} ({', '.join(s.id for s in base_scenario.stations)})"},
            {"Parameter": "Total Fleet Size", "Value": f"{len(base_scenario.buses)} buses"},
        ])
        st.table(meta_df)

        st.markdown("### 📊 Route Layout & Distances")
        route_df = pd.DataFrame([
            {"From": seg.from_node, "To": seg.to_node, "Distance": f"{seg.distance_km} km", "Travel Time": f"{int((seg.distance_km / base_scenario.travel_speed_kmh) * 60)} mins"}
            for seg in base_scenario.route.segments
        ])
        st.table(route_df)



    with col2:
        st.markdown("### 📋 Bus Dispatch Schedule")
        dispatch_rows = []
        for bus in base_scenario.buses:
            dispatch_rows.append({
                "Bus ID": bus.id,
                "Operator": bus.operator.upper(),
                "Direction": bus.direction,
                "Departure Time": bus.departure_time,
                "Max Range (km)": bus.max_range_km
            })
        st.dataframe(pd.DataFrame(dispatch_rows), width="stretch", height=400)


# ----------------- TAB 2: BUS SCHEDULE & TIMETABLE -----------------
with tab2:
    # 1. Summary Metrics
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    total_charges = sum(len(sched.charge_events) for sched in schedule_result.bus_schedules)
    max_bus_wait = max(sched.total_wait_time_mins for sched in schedule_result.bus_schedules)
    
    m_col1.metric("Total Delay", f"{schedule_result.total_delay} mins", help="Sum of delays (waiting + charging) across all buses.")
    m_col2.metric("Total Wait Time", f"{schedule_result.total_wait_time} mins", help="Sum of waiting times in queues across all buses.")
    m_col3.metric("Max Individual Wait", f"{max_bus_wait} mins", help="Maximum wait time experienced by a single bus.")
    m_col4.metric("Total Charging Sessions", f"{total_charges} charges", help="Total charging operations performed.")

    # 2. DataFrame formatting for Bus Timetable
    timetable_rows = []
    for sched in schedule_result.bus_schedules:
        # If the bus has charge events, list each one as a row
        if sched.charge_events:
            for ev in sched.charge_events:
                timetable_rows.append({
                    "Bus ID": sched.bus_id,
                    "Operator": sched.operator.upper(),
                    "Direction": sched.direction,
                    "Departure": format_mins_to_time(sched.departure_time_mins),
                    "Station": f"Station {ev.station_id}",
                    "Charge Start": format_mins_to_time(ev.charge_start_mins),
                    "Charge End": format_mins_to_time(ev.charge_end_mins),
                    "Wait Time": f"{ev.wait_time_mins} mins",
                    "Arrival Time": format_mins_to_time(sched.arrival_time_mins),
                    "raw_wait_mins": ev.wait_time_mins
                })
        else:
            # Fallback (physically not possible with standard range, but good as fallback)
            timetable_rows.append({
                "Bus ID": sched.bus_id,
                "Operator": sched.operator.upper(),
                "Direction": sched.direction,
                "Departure": format_mins_to_time(sched.departure_time_mins),
                "Station": "No Charging",
                "Charge Start": "-",
                "Charge End": "-",
                "Wait Time": "0 mins",
                "Arrival Time": format_mins_to_time(sched.arrival_time_mins),
                "raw_wait_mins": 0
            })
            
    df_timetable = pd.DataFrame(timetable_rows)
    st.markdown("### 📋 Formatted Timetable")
    st.dataframe(df_timetable.drop(columns=["raw_wait_mins"]), width="stretch")

    # 3. Interactive Gantt Chart
    st.markdown("### 🗺️ Bus Timeline Gantt Chart")
    
    # Generate timeline dataframe for Plotly
    base_date = datetime.datetime(2026, 6, 1, 0, 0)
    timeline_data = []
    
    for sched in schedule_result.bus_schedules:
        path = sched.route_path
        
        # Segment 0: Travel to Stop 1
        arr1 = sched.arrival_times[path[1]]
        timeline_data.append({
            "Bus ID": sched.bus_id,
            "Activity": f"Travel {path[0]}→{path[1]}",
            "Start": base_date + datetime.timedelta(minutes=sched.departure_time_mins),
            "End": base_date + datetime.timedelta(minutes=arr1),
            "State": "Traveling"
        })
        
        # Segment 1 to N-1
        for j in range(1, len(path) - 1):
            station_id = path[j]
            ev = next((e for e in sched.charge_events if e.station_id == station_id), None)
            
            arr_time = sched.arrival_times[station_id]
            dep_time = sched.departure_times[station_id]
            
            if ev:
                # Add Wait period if any
                if ev.wait_time_mins > 0:
                    timeline_data.append({
                        "Bus ID": sched.bus_id,
                        "Activity": f"Queue Wait at {station_id}",
                        "Start": base_date + datetime.timedelta(minutes=arr_time),
                        "End": base_date + datetime.timedelta(minutes=ev.charge_start_mins),
                        "State": "Waiting"
                    })
                # Add Charging period
                timeline_data.append({
                    "Bus ID": sched.bus_id,
                    "Activity": f"Charging at {station_id}",
                    "Start": base_date + datetime.timedelta(minutes=ev.charge_start_mins),
                    "End": base_date + datetime.timedelta(minutes=ev.charge_end_mins),
                    "State": "Charging"
                })
            
            # Travel to next stop
            next_node = path[j+1]
            arr_next = sched.arrival_times[next_node]
            timeline_data.append({
                "Bus ID": sched.bus_id,
                "Activity": f"Travel {station_id}→{next_node}",
                "Start": base_date + datetime.timedelta(minutes=dep_time),
                "End": base_date + datetime.timedelta(minutes=arr_next),
                "State": "Traveling"
            })
            
    df_timeline = pd.DataFrame(timeline_data)
    
    # Sort by Bus ID for clean y-axis layout
    df_timeline = df_timeline.sort_values(by=["Bus ID", "Start"])
    
    state_colors = {
        "Traveling": "#3B82F6" if dark_mode else "#60A5FA",
        "Waiting": "#EF4444" if dark_mode else "#F87171",
        "Charging": "#10B981" if dark_mode else "#34D399"
    }

    fig_bus = px.timeline(
        df_timeline, 
        x_start="Start", 
        x_end="End", 
        y="Bus ID", 
        color="State",
        hover_name="Activity",
        color_discrete_map=state_colors,
        category_orders={"Bus ID": sorted(list(df_timeline["Bus ID"].unique()))},
        template=plotly_template
    )
    
    # Adjust layout
    fig_bus.update_yaxes(autorange="reversed")
    fig_bus.update_layout(
        xaxis_title="Time of Day",
        yaxis_title="Bus ID",
        xaxis=dict(
            gridcolor=plotly_grid,
            linecolor=plotly_grid,
            tickformat="%H:%M",
            type="date"
        ),
        yaxis=dict(
            gridcolor=plotly_grid,
            linecolor=plotly_grid
        ),
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=plotly_text)),
        paper_bgcolor=plotly_bg,
        plot_bgcolor=plotly_bg,
        font=dict(color=plotly_text, family="'Outfit', 'Inter', sans-serif")
    )
    st.plotly_chart(fig_bus, use_container_width=True)

    # 4. Downloads Section
    st.markdown("### 💾 Export Schedule Results")
    down_col1, down_col2 = st.columns(2)
    
    # CSV download
    csv_data = df_timetable.drop(columns=["raw_wait_mins"]).to_csv(index=False)
    down_col1.download_button(
        label="Download Timetable as CSV",
        data=csv_data,
        file_name=f"{base_scenario.id}_timetable.csv",
        mime="text/csv"
    )

    # JSON download
    json_data = json.dumps(schedule_result.model_dump(), indent=2)
    down_col2.download_button(
        label="Download Schedule JSON",
        data=json_data,
        file_name=f"{base_scenario.id}_schedule.json",
        mime="application/json"
    )

    # 5. Sensitivity Analysis
    st.markdown("### ⚖️ Optimization Weights Sensitivity Analysis")
    with st.expander("Compare with alternate Weight Profiles"):
        analysis_res = optimizer.run_sensitivity_analysis(base_scenario)
        analysis_rows = []
        for profile, metrics in analysis_res.items():
            if metrics["feasible"]:
                analysis_rows.append({
                    "Weight Profile": profile,
                    "Total Delay (mins)": metrics["total_delay_mins"],
                    "Total Wait Time (mins)": metrics["total_wait_time_mins"],
                    "Max Individual Wait (mins)": metrics["max_bus_wait_mins"]
                })
            else:
                analysis_rows.append({
                    "Weight Profile": profile,
                    "Total Delay (mins)": "Infeasible",
                    "Total Wait Time (mins)": "-",
                    "Max Individual Wait (mins)": "-"
                })
        st.table(pd.DataFrame(analysis_rows))


# ----------------- TAB 3: STATION SCHEDULE -----------------
with tab3:
    col_st1, col_st2 = st.columns([1, 1.2])

    with col_st1:
        st.markdown("### 📋 Station Queue & Order")
        
        # Build queue dataframe
        queue_rows = []
        for station in base_scenario.stations:
            # Find all charges at this station
            charges = []
            for sched in schedule_result.bus_schedules:
                ev = next((e for e in sched.charge_events if e.station_id == station.id), None)
                if ev:
                    charges.append((sched.bus_id, ev.charge_start_mins, ev.charge_end_mins))
            
            # Sort by charge start to determine queue position
            charges.sort(key=lambda x: x[1])
            
            for idx, (bus_id, start, end) in enumerate(charges):
                queue_rows.append({
                    "Station": f"Station {station.id}",
                    "Bus ID": bus_id,
                    "Queue Position": idx + 1,
                    "Charge Start": format_mins_to_time(start),
                    "Charge End": format_mins_to_time(end),
                    "raw_start": start
                })
                
        if queue_rows:
            df_queue = pd.DataFrame(queue_rows)
            st.dataframe(df_queue.drop(columns=["raw_start"]), width="stretch", height=450)
        else:
            st.info("No charging events in this schedule.")

    with col_st2:
        st.markdown("### ⏳ Station Charger Utilization")
        
        # Generate utilization stats
        util_rows = []
        station_timeline = []
        
        for station in base_scenario.stations:
            # Get total active minutes of charger usage
            charges_at_station = [
                row for row in queue_rows if row["Station"] == f"Station {station.id}"
            ]
            total_active_mins = len(charges_at_station) * int(base_scenario.charging_duration_mins)
            
            # Define active window span (earliest start to latest end)
            if charges_at_station:
                earliest_start = min(row["raw_start"] for row in charges_at_station)
                latest_end = max(
                    row["raw_start"] + int(base_scenario.charging_duration_mins) 
                    for row in charges_at_station
                )
                span = max(latest_end - earliest_start, 1)
                util_pct = (total_active_mins / span) * 100
            else:
                util_pct = 0.0
                span = 0
                
            util_rows.append({
                "Station": f"Station {station.id}",
                "Active Chargers": station.chargers_count,
                "Charges Completed": len(charges_at_station),
                "Total Active Time": f"{total_active_mins} mins",
                "Charger Utilization": f"{util_pct:.1f}%"
            })
            
            # Timeline data for station Gantt
            for row in charges_at_station:
                station_timeline.append({
                    "Station": row["Station"],
                    "Bus ID": row["Bus ID"],
                    "Start": base_date + datetime.timedelta(minutes=row["raw_start"]),
                    "End": base_date + datetime.timedelta(minutes=row["raw_start"] + int(base_scenario.charging_duration_mins)),
                    "Label": f"{row['Bus ID']} ({row['Queue Position']})"
                })
                
        st.table(pd.DataFrame(util_rows))
        
        # Plot station occupancy Gantt
        if station_timeline:
            st.markdown("### 📊 Station Occupancy Timeline")
            df_st_time = pd.DataFrame(station_timeline)
            df_st_time = df_st_time.sort_values(by=["Station", "Start"])
            
            fig_st = px.timeline(
                df_st_time,
                x_start="Start",
                x_end="End",
                y="Station",
                color="Bus ID",
                hover_name="Label",
                category_orders={"Station": sorted(list(df_st_time["Station"].unique()))},
                template=plotly_template
            )
            
            fig_st.update_layout(
                xaxis_title="Time of Day",
                yaxis_title="Station",
                xaxis=dict(
                    gridcolor=plotly_grid,
                    linecolor=plotly_grid,
                    tickformat="%H:%M",
                    type="date"
                ),
                yaxis=dict(
                    gridcolor=plotly_grid,
                    linecolor=plotly_grid
                ),
                height=350,
                margin=dict(l=0, r=0, t=30, b=0),
                legend_title="Bus ID",
                paper_bgcolor=plotly_bg,
                plot_bgcolor=plotly_bg,
                font=dict(color=plotly_text, family="'Outfit', 'Inter', sans-serif")
            )
            st.plotly_chart(fig_st, use_container_width=True)
