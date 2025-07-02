import streamlit as st
import json

st.set_page_config(layout="wide", page_title="Admin Panel")
st.title("Admin Panel - Material Variable Editor")

def reload_config():
    """Clears the config from session state, forcing a reload on the next run."""
    if 'config' in st.session_state:
        del st.session_state['config']

if 'config' not in st.session_state:
    st.error("Configuration not loaded. Please run the main Universal Quote Calculator page first.")
    st.stop()

config = st.session_state.config

# --- UI for selecting which material to edit ---
st.header("1. Select Material to Edit")

col1, col2 = st.columns(2)
with col1:
    selected_type = st.selectbox("Material Type", options=list(config['MATERIALS'].keys()))

with col2:
    if selected_type:
        material_options = list(config['MATERIALS'][selected_type].keys())
        selected_material_name = st.selectbox("Specific Material", options=material_options)

st.divider()

# --- UI for editing the variables of the selected material ---
if selected_type and selected_material_name:
    st.header(f"2. Edit Variables for: {selected_material_name}")

    material_data = config['MATERIALS'][selected_type][selected_material_name]
    pref_tab, corp_tab, wholesale_tab = st.tabs(["Preferred", "Corporate", "Wholesale"])

    with pref_tab:
        st.subheader("Preferred Customer Variables")
        p_data = material_data.get("Preferred", {})
        # --- FIX: Added format="%.4f" to handle decimals ---
        p_variable_1 = st.number_input("p_variable_1", value=float(p_data.get("p_variable_1", 0)), format="%.4f", key=f"{selected_material_name}_p1")
        p_variable_2 = st.number_input("p_variable_2", value=float(p_data.get("p_variable_2", 0)), format="%.4f", key=f"{selected_material_name}_p2")
        p_discount_value = st.number_input("p_discount_value", value=float(p_data.get("p_discount_value", 0)), format="%.4f", key=f"{selected_material_name}_p_disc")

    with corp_tab:
        st.subheader("Corporate Customer Variables")
        c_data = material_data.get("Corporate", {})
        # --- FIX: Added format="%.4f" to handle decimals ---
        c_variable_1 = st.number_input("c_variable_1", value=float(c_data.get("c_variable_1", 0)), format="%.4f", key=f"{selected_material_name}_c1")
        c_discount_value = st.number_input("c_discount_value", value=float(c_data.get("c_discount_value", 0)), format="%.4f", key=f"{selected_material_name}_c_disc")

    with wholesale_tab:
        st.subheader("Wholesale Customer Variables")
        w_data = material_data.get("Wholesale", {})
        # --- FIX: Added format="%.4f" to handle decimals ---
        w_variable_1 = st.number_input("w_variable_1", value=float(w_data.get("w_variable_1", 0)), format="%.4f", key=f"{selected_material_name}_w1")
        w_discount_value = st.number_input("w_discount_value", value=float(w_data.get("w_discount_value", 0)), format="%.4f", key=f"{selected_material_name}_w_disc")

    st.divider()
    
    # --- Save Button Logic ---
    save_col, reload_col = st.columns(2)
    with save_col:
        if st.button("Save Changes to Configuration File", use_container_width=True):
            # Update the config dictionary in session state with the new values
            config['MATERIALS'][selected_type][selected_material_name]['Preferred']['p_variable_1'] = p_variable_1
            config['MATERIALS'][selected_type][selected_material_name]['Preferred']['p_variable_2'] = p_variable_2
            config['MATERIALS'][selected_type][selected_material_name]['Preferred']['p_discount_value'] = p_discount_value
            
            config['MATERIALS'][selected_type][selected_material_name]['Corporate']['c_variable_1'] = c_variable_1
            config['MATERIALS'][selected_type][selected_material_name]['Corporate']['c_discount_value'] = c_discount_value

            config['MATERIALS'][selected_type][selected_material_name]['Wholesale']['w_variable_1'] = w_variable_1
            config['MATERIALS'][selected_type][selected_material_name]['Wholesale']['w_discount_value'] = w_discount_value
            
            # Write the updated config back to the JSON file
            try:
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                st.success(f"Successfully saved changes for {selected_material_name}!")
                st.info("Click 'Reload Configuration' to apply the changes to the app.")
            except Exception as e:
                st.error(f"Failed to save changes to config.json: {e}")
    
    with reload_col:
        if st.button("Reload Configuration", type="primary", use_container_width=True, help="Click here after saving to make the new configuration active in the app."):
            reload_config()
            st.rerun()