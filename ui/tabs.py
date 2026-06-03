import streamlit as st
import pandas as pd
import json
import datetime
from utils.helpers import format_mins_to_time
from ui.charts import plot_bus_timeline, plot_station_occupancy

def render_scenario_details_tab(base_scenario):
    """
    Renders Tab 1: Scenario Details.
    """
    st.subheader(base_scenario.name)
    st.caption(base_scenario.description)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ⚙️ Scenario Constraints")
        max_range_val = f"{base_scenario.buses[0].max_range_km} km" if base_scenario.buses else "N/A"
        meta_df = pd.DataFrame([
            {"Parameter": "Battery Capacity / Range", "Value": max_range_val},
            {"Parameter": "Charging Duration (to 100%)", "Value": f"{base_scenario.charging_duration_mins} mins"},
            {"Parameter": "Default Segment Travel Speed", "Value": f"{base_scenario.travel_speed_kmh} km/h"},
            {"Parameter": "Active Station Chargers", "Value": f"{len(base_scenario.stations)} ({', '.join(s.id for s in base_scenario.stations)})"},
            {"Parameter": "Total Fleet Size", "Value": f"{len(base_scenario.buses)} buses"},
        ])
        st.table(meta_df)

        st.markdown("### 📊 Route Layout & Distances")
        route_df = pd.DataFrame([
            {
                "From": seg.from_node, 
                "To": seg.to_node, 
                "Distance": f"{seg.distance_km} km", 
                "Travel Time": f"{int((seg.distance_km / base_scenario.travel_speed_kmh) * 60)} mins"
            }
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


def render_bus_schedule_tab(schedule_result, base_scenario, dark_mode, plotly_theme, optimizer):
    """
    Renders Tab 2: Bus Schedule & Timetable.
    """
    # 1. Summary Metrics
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    total_charges = sum(len(sched.charge_events) for sched in schedule_result.bus_schedules)
    max_bus_wait = max(sched.total_wait_time_mins for sched in schedule_result.bus_schedules) if schedule_result.bus_schedules else 0
    
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
            # Fallback
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
            
    if not timetable_rows:
        df_timetable = pd.DataFrame(columns=[
            "Bus ID", "Operator", "Direction", "Departure", "Station", 
            "Charge Start", "Charge End", "Wait Time", "Arrival Time", "raw_wait_mins"
        ])
    else:
        df_timetable = pd.DataFrame(timetable_rows)
        
    st.markdown("### 📋 Formatted Timetable")
    if not df_timetable.empty and "raw_wait_mins" in df_timetable.columns:
        st.dataframe(df_timetable.drop(columns=["raw_wait_mins"]), width="stretch")
    else:
        st.dataframe(df_timetable, width="stretch")

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
            
    if not timeline_data:
        df_timeline = pd.DataFrame(columns=["Bus ID", "Activity", "Start", "End", "State"])
    else:
        df_timeline = pd.DataFrame(timeline_data)

    fig_bus = plot_bus_timeline(df_timeline, plotly_theme)
    if fig_bus:
        st.plotly_chart(fig_bus, use_container_width=True)
    else:
        st.info("No timeline data to display.")

    # 4. Downloads Section
    st.markdown("### 💾 Export Schedule Results")
    down_col1, down_col2 = st.columns(2)
    
    # CSV download
    if not df_timetable.empty and "raw_wait_mins" in df_timetable.columns:
        csv_data = df_timetable.drop(columns=["raw_wait_mins"]).to_csv(index=False)
    else:
        csv_data = df_timetable.to_csv(index=False)
        
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


def render_station_schedule_tab(schedule_result, base_scenario, plotly_theme):
    """
    Renders Tab 3: Station Schedule.
    """
    col_st1, col_st2 = st.columns([1, 1.2])

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

    with col_st1:
        st.markdown("### 📋 Station Queue & Order")
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
        base_date = datetime.datetime(2026, 6, 1, 0, 0)
        
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
            fig_st = plot_station_occupancy(df_st_time, plotly_theme)
            if fig_st:
                st.plotly_chart(fig_st, use_container_width=True)
