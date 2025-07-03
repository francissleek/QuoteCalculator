import streamlit as st
import json
import os

st.set_page_config(layout="wide", page_title="Admin Panel")
st.title("Admin Panel - Material & Cost Editor")

# --- CONFIGURATION LOADER ---
# This function makes the admin panel self-sufficient.
def load_config(file_path='config.json'):
    """
    Loads configuration from a local file.
    """
    if not os.path.exists(file_path):
        st.error(f"FATAL: The configuration file '{file_path}' was not found in the project directory.")
        st.stop()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        st.error(f"FATAL: Error decoding '{file_path}'. Please ensure it is valid JSON. Error: {e}")
        st.stop()

def reload_config():
    """Clears the config from session state, forcing a reload on the next run."""
    if 'config' in st.session_state:
        del st.session_state['config']

# --- Initialize Config if not present ---
if 'config' not in st.session_state:
    st.session_state.config = load_config()

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
    
    # Add the new tab for 'AN Formula Vars'
    pref_tab, corp_tab, wholesale_tab, an_formula_tab = st.tabs(["Preferred", "Corporate", "Wholesale", "AN Formula Vars"])

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

    # --- NEW UI for AN Formula Variables ---
    with an_formula_tab:
        st.subheader("Variables for 'prodcuts_an' Formula")
        an_vars = material_data.get("prodcuts_an_vars", {})

        new_AW_Roll_Costs = st.number_input("AW_Roll_Costs", value=float(an_vars.get("AW_Roll_Costs", 0)), format="%.2f", key=f"{selected_material_name}_aw")
        new_AV_Material_Width = st.number_input("AV_Material_Width", value=float(an_vars.get("AV_Material_Width", 0)), format="%.2f", key=f"{selected_material_name}_av")
        new_AU_Material_Length = st.number_input("AU_Material_Length", value=float(an_vars.get("AU_Material_Length", 0)), format="%.2f", key=f"{selected_material_name}_au")
        new_AT_Labour = st.number_input("AT_Labour", value=float(an_vars.get("AT_Labour", 0)), format="%.2f", key=f"{selected_material_name}_at")
        new_AS_Laminate_Loading = st.number_input("AS_Laminate_Loading", value=float(an_vars.get("AS_Laminate_Loading", 0)), format="%.2f", key=f"{selected_material_name}_as")
        new_AQ_SQ = st.number_input("AQ_SQ", value=float(an_vars.get("AQ_SQ", 0)), format="%.2f", key=f"{selected_material_name}_aq")
        new_constant_BY8 = st.number_input("constant_BY8", value=float(an_vars.get("constant_BY8", 0)), format="%.2f", key=f"{selected_material_name}_by8")
        new_Per_hour_rate = st.number_input("Per_hour_rate", value=float(an_vars.get("Per_hour_rate", 0)), format="%.2f", key=f"{selected_material_name}_phr")


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
            
            # --- SAVE NEW AN FORMULA VARS ---
            if 'prodcuts_an_vars' not in config['MATERIALS'][selected_type][selected_material_name]:
                config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars'] = {}

            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['AW_Roll_Costs'] = new_AW_Roll_Costs
            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['AV_Material_Width'] = new_AV_Material_Width
            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['AU_Material_Length'] = new_AU_Material_Length
            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['AT_Labour'] = new_AT_Labour
            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['AS_Laminate_Loading'] = new_AS_Laminate_Loading
            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['AQ_SQ'] = new_AQ_SQ
            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['constant_BY8'] = new_constant_BY8
            config['MATERIALS'][selected_type][selected_material_name]['prodcuts_an_vars']['Per_hour_rate'] = new_Per_hour_rate

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
