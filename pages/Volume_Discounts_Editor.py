import streamlit as st
import json
import os

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Volume Discounts Editor")
st.title("Volume Discount Tiers")

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
    if 'volume_tiers' in st.session_state:
        del st.session_state['volume_tiers']

# --- Initialize Config and Tiers in Session State if not present ---
if 'config' not in st.session_state:
    st.session_state.config = load_config()

if 'volume_tiers' not in st.session_state:
    # We work on a copy in session state to handle adds/removes before saving
    st.session_state.volume_tiers = st.session_state.config.get('VOLUME_DISCOUNT_TIERS', {})

# --- UI for Editing Existing Tiers ---
st.header("1. Edit Existing Discount Tiers")

if not st.session_state.volume_tiers:
    st.warning("No Volume Discount Tiers found in the configuration.")
else:
    # Sort tiers by minimum square footage for consistent order
    sorted_tiers = sorted(st.session_state.volume_tiers.items(), key=lambda item: int(item[0]))

    for min_sqft, tier_data in sorted_tiers:
        description = tier_data[0]
        discounts = tier_data[1]

        with st.container(border=True):
            # ALIGNMENT FIX: Subheader is now outside and above the columns.
            st.subheader(f"Tier: >= {min_sqft} sqft")
            
            col1, col2, col3, col4, col_remove = st.columns([2, 1, 1, 1, 0.5])

            with col1:
                new_description = st.text_input(
                    "Description",
                    value=description,
                    key=f"desc_{min_sqft}"
                )
            with col2:
                new_pref_discount = st.number_input(
                    "Preferred %",
                    value=float(discounts[0]),
                    format="%.4f",
                    key=f"pref_disc_{min_sqft}"
                )
            with col3:
                new_corp_discount = st.number_input(
                    "Corporate %",
                    value=float(discounts[1]),
                    format="%.4f",
                    key=f"corp_disc_{min_sqft}"
                )
            with col4:
                new_whole_discount = st.number_input(
                    "Wholesale %",
                    value=float(discounts[2]),
                    format="%.4f",
                    key=f"whole_disc_{min_sqft}"
                )
            with col_remove:
                # ALIGNMENT FIX: Spacers to vertically center the button.
                st.write("") 
                st.write("") 
                if st.button("❌", key=f"remove_{min_sqft}", help=f"Remove tier for {min_sqft} sqft"):
                    del st.session_state.volume_tiers[min_sqft]
                    st.rerun()

            # Update the session state with new values from the UI
            st.session_state.volume_tiers[min_sqft] = [
                new_description,
                [new_pref_discount, new_corp_discount, new_whole_discount]
            ]
st.divider()

# --- UI for Adding a New Tier ---
st.header("2. Add a New Tier")
with st.form("new_tier_form", clear_on_submit=True):
    st.write("Define the minimum square footage and discount values for a new tier.")
    add_col1, add_col2, add_col3, add_col4, add_col5 = st.columns(5)

    with add_col1:
        new_min_sqft = st.number_input("Min SQFT for Tier", min_value=0, step=50, key="new_min_sqft")
    with add_col2:
        new_tier_desc = st.text_input("New Tier Description", key="new_desc")
    with add_col3:
        new_tier_discounts_pref = st.number_input("Preferred %", min_value=0.0, format="%.4f", key="new_pref")
    with add_col4:
        new_tier_discounts_corp = st.number_input("Corporate %", min_value=0.0, format="%.4f", key="new_corp")
    with add_col5:
        new_tier_discounts_whole = st.number_input("Wholesale %", min_value=0.0, format="%.4f", key="new_whole")

    submitted = st.form_submit_button("Add New Tier")
    if submitted:
        new_key = str(int(new_min_sqft))
        if new_key in st.session_state.volume_tiers:
            st.error(f"A tier for '{new_key}' sqft already exists. Please remove or edit the existing one.")
        elif not new_tier_desc:
            st.error("The new tier must have a description.")
        else:
            st.session_state.volume_tiers[new_key] = [
                new_tier_desc,
                [new_tier_discounts_pref, new_tier_discounts_corp, new_tier_discounts_whole]
            ]
            st.success(f"Successfully added tier for {new_key} sqft. Click 'Save Changes' to finalize.")
            st.rerun()
st.divider()

# --- Save and Reload Logic ---
st.header("3. Save and Reload")
save_col, reload_col = st.columns(2)
with save_col:
    if st.button("Save Changes to Configuration File", use_container_width=True):
        # Update the main config object with the modified tiers
        st.session_state.config['VOLUME_DISCOUNT_TIERS'] = st.session_state.volume_tiers
        
        # Write the updated config back to the JSON file
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(st.session_state.config, f, indent=2)
            st.success("Successfully saved changes to 'config.json'!")
            st.info("Click 'Reload Configuration' to apply changes across the app.")
        except Exception as e:
            st.error(f"Failed to save changes to config.json: {e}")

with reload_col:
    if st.button("Reload Configuration", type="primary", use_container_width=True, help="Click to make the new configuration active in the app."):
        reload_config()
        st.rerun()