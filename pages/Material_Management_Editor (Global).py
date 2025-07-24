import streamlit as st
import json
import os

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Material Management Editor")
st.title("Material Management Editor")
st.write("A global page to add or remove specific materials from an existing material type.")

# --- CONFIGURATION LOADER (Consistent with other admin panels) ---
def load_config(file_path='config.json'):
    """
    Loads configuration from a local file.
    """
    if not os.path.exists(file_path):
        st.error(f"FATAL: The configuration file '{file_path}' was not found.")
        st.stop()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        st.error(f"FATAL: Error decoding '{file_path}'. Please ensure it is valid JSON. Error: {e}")
        st.stop()
    return {}

def reload_config():
    """Clears the config from session state, forcing a reload on the next run."""
    if 'config' in st.session_state:
        del st.session_state['config']

# --- Initialize Config in Session State if not present ---
if 'config' not in st.session_state:
    st.session_state.config = load_config()

# Use a working copy of the materials for UI operations
if 'materials_copy' not in st.session_state:
    st.session_state.materials_copy = st.session_state.config.get('MATERIALS', {})


# --- UI for Selecting Material Type ---
st.header("1. Select Material Type")
material_types = list(st.session_state.materials_copy.keys())
selected_type = st.selectbox(
    "Select a material type to manage",
    options=material_types
)
st.divider()


# --- UI for Managing Materials ---
if selected_type:
    # --- UI for Removing Existing Materials ---
    st.header(f"2. Manage Materials for '{selected_type}'")
    
    material_names = list(st.session_state.materials_copy.get(selected_type, {}).keys())

    if not material_names:
        st.warning(f"No specific materials found for the type '{selected_type}'.")
    else:
        for material_name in sorted(material_names):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text_input(
                    "Material Name",
                    value=material_name,
                    key=f"name_{selected_type}_{material_name}",
                    disabled=True
                )
            with col2:
                st.write("") # Spacer for alignment
                st.write("") # Spacer for alignment
                if st.button("❌ Remove", key=f"remove_{selected_type}_{material_name}", use_container_width=True):
                    # Remove from the session state copy
                    del st.session_state.materials_copy[selected_type][material_name]
                    st.success(f"'{material_name}' removed. Click 'Save Changes' to finalize.")
                    st.rerun()

    st.divider()

    # --- UI for Adding a New Material ---
    st.header("3. Add New Material")
    with st.form("new_material_form", clear_on_submit=True):
        st.write(f"Add a new material to the '{selected_type}' category.")
        new_material_name = st.text_input("New Specific Material Name")
        
        submitted = st.form_submit_button("Add New Material")
        if submitted:
            if not new_material_name:
                st.error("Material name cannot be empty.")
            elif new_material_name in st.session_state.materials_copy[selected_type]:
                st.error(f"A material named '{new_material_name}' already exists in '{selected_type}'.")
            else:
                # Define the default structure for a new material
                default_structure = {
                    "is_commodity": False, # Set default value for the new flag
                    "Preferred": {
                        "preferred_historical_price": 0.0,
                        "preferred_fine_tune_modifier": 1.0,
                        "preferred_discount_value": 0.0
                    },
                    "Corporate": {
                        "corporate_historical_price": 1.0,
                        "corporate_discount_value": 0.0
                    },
                    "Wholesale": {
                        "wholesale_historical_price": 1.0,
                        "wholesale_discount_value": 0.0
                    },
                    "prodcuts_an_vars": {
                        "AW_Roll_Costs": 0, "AV_Material_Width": 1,
                        "AU_Material_Length": 1, "AT_Labour": 0,
                        "AS_Laminate_Loading": 0, "AQ_SQ": 0,
                        "constant_BY8": 0, "Per_hour_rate": 0
                    }
                }
                # Add to the session state copy
                st.session_state.materials_copy[selected_type][new_material_name] = default_structure
                st.success(f"Successfully added '{new_material_name}'. Click 'Save Changes' to finalize.")
                st.rerun()

st.divider()

# --- Save and Reload Logic ---
st.header("4. Save and Reload")
save_col, reload_col = st.columns(2)
with save_col:
    if st.button("Save Changes to Configuration File", use_container_width=True):
        # Update the main config object with the modified materials
        st.session_state.config['MATERIALS'] = st.session_state.materials_copy
        
        # Write the updated config back to the JSON file
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(st.session_state.config, f, indent=2)
            st.success("Successfully saved material changes to 'config.json'!")
            st.info("Click 'Reload Configuration' to apply changes across the app.")
        except Exception as e:
            st.error(f"Failed to save changes to config.json: {e}")

with reload_col:
    if st.button("Reload Configuration", type="primary", use_container_width=True, help="Click to make the new configuration active in the app."):
        # Clear the working copy and the main config to force a full reload
        if 'materials_copy' in st.session_state:
            del st.session_state['materials_copy']
        reload_config()
        st.rerun()