import streamlit as st
import json
from pathlib import Path
from scheduler.models import Scenario, Station, RouteSegment, Bus
from utils.loader import load_scenario_from_file
from utils.helpers import get_route_nodes

def render_sidebar(scenario_files, scenario_dir: Path):
    """
    Renders the sidebar controls and handles scenario modifications.
    Returns:
        dark_mode (bool): Whether dark mode is toggled.
        custom_weights (dict): The weight profile selected by the user.
    """
    st.sidebar.header("🔧 Scheduler Controls")
    
    # Light/Dark Mode Selector
    dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=True)
    
    # Sidebar Selector
    if scenario_files:
        # Find current index
        try:
            curr_idx = scenario_files.index(st.session_state.selected_file)
        except ValueError:
            curr_idx = 0
            
        def format_scenario_name(path):
            if path.name.startswith("template_"):
                name = path.stem.replace("template_", "").replace("_", " ").title()
                return f"📋 Template: {name}"
            else:
                name = path.stem.replace("scenario", "Scenario ")
                return f"🚗 {name}"

        selected_file = st.sidebar.selectbox(
            "Select Base Scenario / Template",
            scenario_files,
            format_func=format_scenario_name,
            index=curr_idx
        )
        
        # If selection changed, reload scenario
        if selected_file != st.session_state.selected_file:
            st.session_state.selected_file = selected_file
            st.session_state.active_scenario = load_scenario_from_file(str(selected_file))
            st.session_state.scenario_edited = False
            st.rerun()

    # File Uploader for Custom Scenarios
    uploaded_file = st.sidebar.file_uploader("📤 Upload Custom Scenario JSON", type=["json"])
    
    if "upload_success_message" in st.session_state:
        st.sidebar.success(st.session_state.upload_success_message)
        del st.session_state.upload_success_message
    
    if uploaded_file is not None:
        try:
            content = json.load(uploaded_file)
            uploaded_scenario = Scenario.model_validate(content)
            if st.session_state.get("uploaded_file_name") != uploaded_file.name:
                # Safely store the uploaded JSON file in the scenario_dir
                dest_path = scenario_dir / uploaded_file.name
                with open(dest_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=2)
                    
                st.session_state.active_scenario = uploaded_scenario
                st.session_state.selected_file = dest_path
                st.session_state.uploaded_file_name = uploaded_file.name
                st.session_state.scenario_edited = False
                st.session_state.upload_success_message = f"✅ Stored '{uploaded_file.name}' in data folder successfully!"
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Invalid Scenario JSON: {e}")

    # Quick Load & Download Templates under the Uploader
    template_files = sorted(list(scenario_dir.glob("template_*.json")))
    if template_files:
        st.sidebar.markdown("**📥 Templates (Quick Load & Download):**")
        for t_file in template_files:
            t_name = t_file.stem.replace("template_", "").replace("_", " ").title()
            
            try:
                with open(t_file, "r", encoding="utf-8") as f:
                    template_content = f.read()
            except Exception as e:
                template_content = "{}"
                
            col_load, col_down = st.sidebar.columns([3, 1])
            with col_load:
                if st.button(f"📋 {t_name}", key=f"quick_tpl_{t_file.stem}", use_container_width=True):
                    try:
                        st.session_state.active_scenario = load_scenario_from_file(str(t_file))
                        st.session_state.selected_file = t_file
                        st.session_state.scenario_edited = True
                        st.sidebar.success(f"Loaded template: {t_name}!")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Error: {e}")
            with col_down:
                st.download_button(
                    label="📥",
                    data=template_content,
                    file_name=t_file.name,
                    mime="application/json",
                    key=f"dl_tpl_{t_file.stem}",
                    help=f"Download {t_file.name} JSON file",
                    use_container_width=True
                )

    # Interactive Scenario Editors
    if st.session_state.active_scenario:
        st.sidebar.markdown("### 🛠️ Scenario Modifiers (Curveballs)")
        
        # Edit Stations & Chargers Expander
        with st.sidebar.expander("🚉 Edit Stations & Chargers"):
            st.write("**Double Chargers or Edit Counts:**")
            updated_stations = []
            for station in st.session_state.active_scenario.stations:
                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    st.write(f"Station {station.id} ({station.name})")
                with col_c2:
                    new_count = st.number_input(
                        f"Chargers at {station.id}",
                        min_value=0,
                        max_value=20,
                        value=station.chargers_count,
                        key=f"chg_cnt_{station.id}",
                        label_visibility="collapsed"
                    )
                    if new_count != station.chargers_count:
                        station.chargers_count = new_count
                        st.session_state.scenario_edited = True
                updated_stations.append(station)
            
            st.session_state.active_scenario.stations = updated_stations
            
            st.markdown("---")
            st.write("**➕ Add New Station:**")
            new_st_id = st.text_input("Station ID (e.g., E)", value="", max_chars=5, key="new_st_id").strip()
            new_st_name = st.text_input("Station Name (e.g., Station E)", value="", key="new_st_name").strip()
            new_st_chargers = st.number_input("Chargers Count", min_value=1, max_value=10, value=1, key="new_st_chg")
            
            segments = st.session_state.active_scenario.route.segments
            segment_options = [f"{seg.from_node} → {seg.to_node} ({seg.distance_km} km)" for seg in segments]
            
            if segment_options:
                selected_seg_idx = st.selectbox("Select Segment to Split", range(len(segment_options)), format_func=lambda idx: segment_options[idx])
                split_seg = segments[selected_seg_idx]
                st.write(f"Splitting segment: `{split_seg.from_node} → {split_seg.to_node}` ({split_seg.distance_km} km)")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    d1 = st.number_input(f"Dist: {split_seg.from_node} → {new_st_id or 'New'} (km)", min_value=1.0, max_value=float(split_seg.distance_km), value=float(split_seg.distance_km)/2.0, step=1.0)
                with col_d2:
                    d2 = st.number_input(f"Dist: {new_st_id or 'New'} → {split_seg.to_node} (km)", min_value=1.0, max_value=float(split_seg.distance_km), value=float(split_seg.distance_km)/2.0, step=1.0)
                    
                if st.button("Insert Station"):
                    if not new_st_id or not new_st_name:
                        st.error("Station ID and Name are required.")
                    elif any(s.id == new_st_id for s in st.session_state.active_scenario.stations):
                        st.error("Station ID already exists.")
                    else:
                        new_st = Station(id=new_st_id, name=new_st_name, chargers_count=new_st_chargers)
                        
                        seg1 = RouteSegment(from_node=split_seg.from_node, to_node=new_st_id, distance_km=d1)
                        seg2 = RouteSegment(from_node=new_st_id, to_node=split_seg.to_node, distance_km=d2)
                        
                        new_segments = list(segments)
                        new_segments[selected_seg_idx] = seg1
                        new_segments.insert(selected_seg_idx + 1, seg2)
                        
                        st.session_state.active_scenario.stations.append(new_st)
                        st.session_state.active_scenario.route.segments = new_segments
                        st.session_state.scenario_edited = True
                        st.success(f"Station {new_st_name} inserted!")
                        st.rerun()
                        
        # Manage Fleet & Operators Expander
        with st.sidebar.expander("🚌 Manage Fleet & Operators"):
            st.write("**Swap Operator Name:**")
            operators = sorted(list(set(b.operator for b in st.session_state.active_scenario.buses)))
            if operators:
                col_op1, col_op2 = st.columns(2)
                with col_op1:
                    op_to_swap = st.selectbox("Operator to swap", operators, key="op_swap_select")
                with col_op2:
                    new_op_name = st.text_input("New name", value="", key="op_swap_new").strip()
                    
                if st.button("Swap Operator"):
                    if new_op_name:
                        for bus in st.session_state.active_scenario.buses:
                            if bus.operator == op_to_swap:
                                bus.operator = new_op_name
                        st.session_state.scenario_edited = True
                        st.success(f"Swapped '{op_to_swap}' with '{new_op_name}'!")
                        st.rerun()
                    else:
                        st.error("New operator name is required.")
                        
            st.markdown("---")
            st.write("**➕ Add New Bus:**")
            new_bus_id = st.text_input("Bus ID", value=f"bus-custom-{len(st.session_state.active_scenario.buses)+1}", key="new_bus_id").strip()
            
            all_ops = sorted(list(set(b.operator for b in st.session_state.active_scenario.buses)))
            col_b_op1, col_b_op2 = st.columns(2)
            with col_b_op1:
                new_bus_op_sel = st.selectbox("Select Operator", ["(New Operator)"] + all_ops, key="new_bus_op_sel")
            with col_b_op2:
                new_bus_op_txt = st.text_input("Or type new operator", value="", key="new_bus_op_txt").strip()
                
            new_bus_op = new_bus_op_txt if new_bus_op_txt else (new_bus_op_sel if new_bus_op_sel != "(New Operator)" else "kpn")
            
            forward_path = get_route_nodes(st.session_state.active_scenario.route, "forward")
            if forward_path:
                origin = forward_path[0]
                dest = forward_path[-1]
                dir_opts = [f"{origin}→{dest}", f"{dest}→{origin}"]
            else:
                dir_opts = ["Bengaluru→Kochi", "Kochi→Bengaluru"]
                
            new_bus_dir = st.selectbox("Direction", dir_opts, key="new_bus_dir")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                new_bus_dep = st.text_input("Departure (HH:MM)", value="19:00", key="new_bus_dep")
            with col_t2:
                new_bus_prior = st.slider("Priority", 1, 5, 1, key="new_bus_prior")
                
            new_bus_range = st.number_input("Max Range (km)", min_value=100.0, max_value=500.0, value=240.0, step=10.0, key="new_bus_range")
            
            if st.button("Add Bus"):
                if not new_bus_id:
                    st.error("Bus ID is required.")
                elif any(b.id == new_bus_id for b in st.session_state.active_scenario.buses):
                    st.error("Bus ID already exists.")
                else:
                    try:
                        p = new_bus_dep.split(":")
                        if len(p) != 2 or not (0 <= int(p[0]) < 24) or not (0 <= int(p[1]) < 60):
                            raise ValueError()
                    except:
                        st.error("Departure time must be HH:MM.")
                        st.stop()
                        
                    new_bus = Bus(
                        id=new_bus_id,
                        operator=new_bus_op,
                        direction=new_bus_dir,
                        departure_time=new_bus_dep,
                        priority=new_bus_prior,
                        max_range_km=new_bus_range
                    )
                    st.session_state.active_scenario.buses.append(new_bus)
                    st.session_state.scenario_edited = True
                    st.success(f"Bus {new_bus_id} added!")
                    st.rerun()
                    
            st.markdown("---")
            st.write("**🗑️ Delete Bus:**")
            bus_to_del = st.selectbox("Select Bus to delete", [b.id for b in st.session_state.active_scenario.buses], key="delete_bus_sel")
            if st.button("Delete Bus"):
                st.session_state.active_scenario.buses = [b for b in st.session_state.active_scenario.buses if b.id != bus_to_del]
                st.session_state.scenario_edited = True
                st.success(f"Bus {bus_to_del} deleted!")
                st.rerun()

        # General & Operational Configs Expander
        with st.sidebar.expander("⚡ General & Operational Configs"):
            new_speed = st.slider("Travel Speed (km/h)", min_value=30.0, max_value=120.0, value=float(st.session_state.active_scenario.travel_speed_kmh), step=5.0)
            new_duration = st.slider("Charging Duration (mins)", min_value=10.0, max_value=90.0, value=float(st.session_state.active_scenario.charging_duration_mins), step=5.0)
            
            if new_speed != st.session_state.active_scenario.travel_speed_kmh:
                st.session_state.active_scenario.travel_speed_kmh = new_speed
                st.session_state.scenario_edited = True
            if new_duration != st.session_state.active_scenario.charging_duration_mins:
                st.session_state.active_scenario.charging_duration_mins = new_duration
                st.session_state.scenario_edited = True

        # Raw JSON Editor Expander
        with st.sidebar.expander("📝 Raw JSON Editor (On the Spot)"):
            curr_json = json.dumps(st.session_state.active_scenario.model_dump(), indent=2)
            edited_json = st.text_area("Edit scenario JSON directly", value=curr_json, height=300, key="raw_json_textarea")
            if st.button("Apply Raw JSON Changes"):
                try:
                    content = json.loads(edited_json)
                    st.session_state.active_scenario = Scenario.model_validate(content)
                    st.session_state.scenario_edited = True
                    st.success("JSON applied!")
                    st.rerun()
                except Exception as e:
                    st.error(f"JSON validation error: {e}")

    base_scenario = st.session_state.active_scenario
    if not base_scenario:
        return dark_mode, {}

    # Weights Section in Sidebar
    st.sidebar.markdown("### ⚖️ Optimization Weights")
    st.sidebar.info(
        "Tune these weights to adjust the scheduler's behavior. "
        "Higher weights prioritize that specific objective."
    )

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

    # Export Scenario Input JSON button
    st.sidebar.download_button(
        label="💾 Export Scenario Input JSON",
        data=json.dumps(base_scenario.model_dump(), indent=2),
        file_name=f"{base_scenario.id}_input_scenario.json",
        mime="application/json"
    )

    # Reset Button
    if st.sidebar.button("Reset to Scenario Defaults"):
        if st.session_state.selected_file:
            st.session_state.active_scenario = load_scenario_from_file(str(st.session_state.selected_file))
        st.session_state.scenario_edited = False
        st.success("Reset to default scenario values.")
        st.rerun()

    custom_weights = {
        "individual": w_individual,
        "operator": w_operator,
        "overall": w_overall
    }

    return dark_mode, custom_weights
