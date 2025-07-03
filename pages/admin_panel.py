import streamlit as st
import json
import os

st.set_page_config(layout="wide", page_title="Admin Panel")
st.title("Admin Panel")

# --- CONFIGURATION LOADER ---
# This function makes the admin panel self-sufficient.
def load_config(file_path='config.json'):
    """
    Loads configuration from a local file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"FATAL: The configuration file '{file_path}' was not found in the project directory.")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"FATAL: Error decoding '{file_path}'. Please ensure it is valid JSON. Error: {e}")
        st.stop()

def reload_config():
    """Clears the config from session state, forcing a reload on the next run."""
    if 'config' in st.session_state:
        del st.session_state['config']

# --- Initialize Config if not present ---
# If config is not in the session, load it directly.
if 'config' not in st.session_state:
    st.session_state.config = load_config()

config = st.session_state.config

# --- Create top-level tabs for better UI organization ---
material_tab, costs_tab = st.tabs(["Material Variable Editor", "Additional Costs Editor"])

# --- TAB 1: Your existing material editor ---
with material_tab:
    st.header("1. Select Material to Edit")

    col1, col2 = st.columns(2)
    with col1:
        # Use a unique key for the selectbox to avoid conflicts with the other tab
        selected_type = st.selectbox("Material Type", options=list(config['MATERIALS'].keys()), key="material_type_select")

    with col2:
        if selected_type:
            material_options = list(config['MATERIALS'][selected_type].keys())
            selected_material_name = st.selectbox("Specific Material", options=material_options, key="specific_material_select")

    st.divider()

    # UI for editing the variables of the selected material
    if selected_type and selected_material_name:
        st.header(f"2. Edit Variables for: {selected_material_name}")

        material_data = config['MATERIALS'][selected_type][selected_material_name]
        pref_tab, corp_tab, wholesale_tab = st.tabs(["Preferred", "Corporate", "Wholesale"])

        with pref_tab:
            st.subheader("Preferred Customer Variables")
            p_data = material_data.get("Preferred", {})
            p_variable_1 = st.number_input("p_variable_1", value=float(p_data.get("p_variable_1", 0)), format="%.4f", key=f"{selected_material_name}_p1")
            p_variable_2 = st.number_input("p_variable_2", value=float(p_data.get("p_variable_2", 0)), format="%.4f", key=f"{selected_material_name}_p2")
            p_discount_value = st.number_input("p_discount_value", value=float(p_data.get("p_discount_value", 0)), format="%.4f", key=f"{selected_material_name}_p_disc")

        with corp_tab:
            st.subheader("Corporate Customer Variables")
            c_data = material_data.get("Corporate", {})
            c_variable_1 = st.number_input("c_variable_1", value=float(c_data.get("c_variable_1", 0)), format="%.4f", key=f"{selected_material_name}_c1")
            c_discount_value = st.number_input("c_discount_value", value=float(c_data.get("c_discount_value", 0)), format="%.4f", key=f"{selected_material_name}_c_disc")

        with wholesale_tab:
            st.subheader("Wholesale Customer Variables")
            w_data = material_data.get("Wholesale", {})
            w_variable_1 = st.number_input("w_variable_1", value=float(w_data.get("w_variable_1", 0)), format="%.4f", key=f"{selected_material_name}_w1")
            w_discount_value = st.number_input("w_discount_value", value=float(w_data.get("w_discount_value", 0)), format="%.4f", key=f"{selected_material_name}_w_disc")

        st.divider()
        
        # Save Button Logic for Materials
        if st.button("Save Material Changes", use_container_width=True, key="save_material"):
            config['MATERIALS'][selected_type][selected_material_name]['Preferred']['p_variable_1'] = p_variable_1
            config['MATERIALS'][selected_type][selected_material_name]['Preferred']['p_variable_2'] = p_variable_2
            config['MATERIALS'][selected_type][selected_material_name]['Preferred']['p_discount_value'] = p_discount_value
            
            config['MATERIALS'][selected_type][selected_material_name]['Corporate']['c_variable_1'] = c_variable_1
            config['MATERIALS'][selected_type][selected_material_name]['Corporate']['c_discount_value'] = c_discount_value

            config['MATERIALS'][selected_type][selected_material_name]['Wholesale']['w_variable_1'] = w_variable_1
            config['MATERIALS'][selected_type][selected_material_name]['Wholesale']['w_discount_value'] = w_discount_value
            
            try:
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                st.success(f"Successfully saved material changes for {selected_material_name}!")
                st.info("Configuration is updated. Click 'Reload Configuration' to apply changes across the app.")
            except Exception as e:
                st.error(f"Failed to save changes to config.json: {e}")

# --- TAB 2: The new editor for Additional Costs ---
with costs_tab:
    st.header("Edit Additional Cost Variables")

    additional_costs_config = config.get('ADDITIONAL_COSTS', {})

    with st.expander("View Formulas", expanded=False):
        st.latex(r'''\text{Cost (cons\_bx\_4 / cons\_bx\_6)} = \left( \frac{\text{Variable 1}}{\text{Variable 2}} \right) \times \text{Variable 3}''')

    with st.container(border=True):
        st.subheader("📦 `cons_bx_4` Variables")
        bx4_vars = additional_costs_config.get('cons_bx_4', {})
        c1, c2, c3 = st.columns(3)
        new_bx4_v1 = c1.number_input("Variable 1", value=float(bx4_vars.get('variable_1', 0)), key="bx4_v1")
        new_bx4_v2 = c2.number_input("Variable 2", value=float(bx4_vars.get('variable_2', 1)), key="bx4_v2")
        new_bx4_v3 = c3.number_input("Variable 3", value=float(bx4_vars.get('variable_3', 0)), key="bx4_v3")

    with st.container(border=True):
        st.subheader("📦 `cons_bx_6` Variables")
        bx6_vars = additional_costs_config.get('cons_bx_6', {})
        c4, c5, c6 = st.columns(3)
        new_bx6_v1 = c4.number_input("Variable 1", value=float(bx6_vars.get('variable_1', 0)), key="bx6_v1")
        new_bx6_v2 = c5.number_input("Variable 2", value=float(bx6_vars.get('variable_2', 1)), key="bx6_v2")
        new_bx6_v3 = c6.number_input("Variable 3", value=float(bx6_vars.get('variable_3', 0)), key="bx6_v3")

    with st.container(border=True):
        st.subheader("📎 `prodcuts_an` (Fixed Value)")
        new_prodcuts_an = st.number_input("Cost", value=float(additional_costs_config.get('prodcuts_an', 16.21)), key="prod_an")

    st.divider()

    # Save Button Logic for Additional Costs
    if st.button("Save Additional Cost Changes", use_container_width=True, key="save_costs"):
        config['ADDITIONAL_COSTS']['cons_bx_4']['variable_1'] = new_bx4_v1
        config['ADDITIONAL_COSTS']['cons_bx_4']['variable_2'] = new_bx4_v2
        config['ADDITIONAL_COSTS']['cons_bx_4']['variable_3'] = new_bx4_v3
        
        config['ADDITIONAL_COSTS']['cons_bx_6']['variable_1'] = new_bx6_v1
        config['ADDITIONAL_COSTS']['cons_bx_6']['variable_2'] = new_bx6_v2
        config['ADDITIONAL_COSTS']['cons_bx_6']['variable_3'] = new_bx6_v3

        config['ADDITIONAL_COSTS']['prodcuts_an'] = new_prodcuts_an

        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            st.success("Successfully saved Additional Cost changes!")
            st.info("Configuration is updated. Click 'Reload Configuration' to apply changes across the app.")
        except Exception as e:
            st.error(f"Failed to save changes to config.json: {e}")


# --- Universal Reload Button ---
st.sidebar.header("Configuration")
if st.sidebar.button("Reload Configuration", type="primary", use_container_width=True, help="Click here after saving to make the new configuration active in the app."):
    reload_config()
    st.rerun()
