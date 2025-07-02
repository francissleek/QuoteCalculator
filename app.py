# FILE: app.py
# CORRECTED: Restored the 'BASE AMOUNT' and 'MAX DISCOUNT' display metrics in each entry.

import streamlit as st
import uuid
import pandas as pd
import json
import math

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Universal Quote Calculator")
st.title("Universal Quote Calculator")

# --- CORRECTED DUAL-ENVIRONMENT CONFIGURATION LOADER ---
def load_config(file_path='config.json'):
    """
    Loads configuration with a clear distinction between deployed (secrets)
    and local (file) environments.
    """
    try:
        if "config" in st.secrets:
            config_str = st.secrets["config"]
            return json.loads(config_str)
    except (st.errors.StreamlitAPIException, KeyError, json.JSONDecodeError):
        pass

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"FATAL: Configuration could not be loaded. Ensure a 'config.json' file exists for local development, or that secrets are configured correctly for deployment.")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"FATAL: Error decoding local file '{file_path}'. Please ensure it is valid JSON. Error: {e}")
        st.stop()


# --- Load config into session state to share across pages ---
if 'config' not in st.session_state:
    st.session_state.config = load_config()

config = st.session_state.config

# --- Unpack loaded data ---
MATERIALS = config.get('MATERIALS', {})
SIDES_TIERS_MAP = config.get('SIDES_TIERS_MAP', {})
SIDEDNESS_OPTIONS = config.get('SIDEDNESS_OPTIONS', [])
SPECIALTY_FINISHING = config.get('SPECIALTY_FINISHING', {})
CUSTOMER_TYPES = config.get('CUSTOMER_TYPES', [])
VOLUME_DISCOUNT_TIERS = {int(k): v for k, v in config.get('VOLUME_DISCOUNT_TIERS', {}).items()}
PRINT_ADJUSTMENT_FIXED = config.get('PRINT_ADJUSTMENT_FIXED', {})
MULTIPLES_MAP = {int(k): v for k, v in config.get('MULTIPLES_MAP', {}).items()}
FALL_BACK_VALUE = config.get('FALL_BACK_VALUE', 0.25)
CUT_COST_MAP = config.get('CUT_COST_MAP', {})
ADDITIONAL_TIME_MAP = config.get('ADDITIONAL_TIME_MAP', {})
ADDED_INSTALL_MAP = config.get('ADDED_INSTALL_MAP', {})

TIER_DESCRIPTIONS = list(SIDES_TIERS_MAP.keys())
FINISHING_TYPES = list(SPECIALTY_FINISHING.keys())
CUT_COST_OPTIONS = list(CUT_COST_MAP.keys())
ADDITIONAL_TIME_OPTIONS = list(ADDITIONAL_TIME_MAP.keys())
ADDED_INSTALL_OPTIONS = list(ADDED_INSTALL_MAP.keys())


# --- Helper functions ---
def excel_floor(number, significance):
    if significance == 0: return 0
    return math.floor(number / significance) * significance

def excel_ceiling(number, significance):
    if significance == 0: return 0
    return math.ceil(number / significance) * significance

def calculate_material_price(material_data):
    results = {
        'preferred_base': 0, 'preferred_value': 0,
        'corporate_base': 0, 'corporate_value': 0,
        'wholesale_base': 0, 'wholesale_value': 0
    }
    try:
        p_vars = material_data['Preferred']
        p_variable_1 = p_vars.get('p_variable_1', 0)
        p_variable_2 = p_vars.get('p_variable_2', 0)
        p_discount_value = p_vars.get('p_discount_value', 0)
        
        preferred_base = excel_floor(p_variable_1 * p_variable_2, FALL_BACK_VALUE)
        preferred_value = preferred_base * (1 - p_discount_value)
        results['preferred_base'] = preferred_base
        results['preferred_value'] = preferred_value

        c_vars = material_data['Corporate']
        c_variable_1 = c_vars.get('c_variable_1', 0)
        c_discount_value = c_vars.get('c_discount_value', 0)

        corporate_base = excel_ceiling(preferred_base * c_variable_1, FALL_BACK_VALUE)
        corporate_value = corporate_base * (1 - c_discount_value)
        results['corporate_base'] = corporate_base
        results['corporate_value'] = corporate_value

        w_vars = material_data['Wholesale']
        w_variable_1 = w_vars.get('w_variable_1', 0)
        w_discount_value = w_vars.get('w_discount_value', 0)
        
        wholesale_base = excel_ceiling(preferred_base * w_variable_1, FALL_BACK_VALUE)
        wholesale_value = wholesale_base * (1 - w_discount_value)
        results['wholesale_base'] = wholesale_base
        results['wholesale_value'] = wholesale_value
    except (KeyError, TypeError):
        pass
    return results

def get_discount_tier_details(total_sqft, all_tiers):
    best_tier_desc = "N/A"
    for min_sqft, (description, _) in sorted(all_tiers.items()):
        if total_sqft >= min_sqft:
            best_tier_desc = description
    return best_tier_desc

def get_multiplier(num_entries):
    for min_entries, value in sorted(MULTIPLES_MAP.items(), reverse=True):
        if num_entries >= min_entries:
            return f"{min_entries}+ entries" if min_entries != 1 else "1 entry", value
    return "N/A", 1
    
def get_suggested_sides_tier(sqft, sidedness):
    if sidedness == "No Print": return "NO PRINT"
    if sidedness == "Single Sided":
        if sqft >= 1.0: return "STANDARD OVER 1sq'"
        if sqft >= 0.5: return "SMALL Between 1sq' - 0.5sq'"
        if sqft >= 0.25: return "SMALL BETWEEN 0.5 - .25 sq' /peice"
        return "SMALLEST UNDER 0.05 sq' /peice"
    if sidedness == "Double Sided":
        if sqft >= 1.0: return "DOUBLE SIDED Over 1 SQ'"
        if sqft >= 0.5: return "DOUBLE SIDED between 1sq' - 0.5sq' per peice"
        if sqft >= 0.25: return "DOUBLE SIDED under 0.5 - .25 sq' /peice"
        return "DOUBLE SIDED under 0.05 sq' /peice"
    return TIER_DESCRIPTIONS[0] if TIER_DESCRIPTIONS else "N/A"

def get_banner_mesh_details(sqft, option_details):
    if not option_details: return "N/A", 0.0
    option_name = list(option_details.keys())[0]
    tier_list = option_details[option_name]
    for min_sqft, price, desc_prefix in tier_list:
        if sqft >= min_sqft:
            full_description = f"{desc_prefix} - {option_name}"
            return full_description, price
    return "N/A", 0.0

# --- Layout Rendering Function ---
def render_expanded_layout(entry, i, customer_type):
    with st.container(border=True):
        st.markdown(f"<a name='entry-{entry['id']}'></a>", unsafe_allow_html=True)
        
        # --- Type, Material, Remove Button ---
        type_col, material_col, remove_col = st.columns([2, 3, 1])
        with type_col:
            entry['type'] = st.selectbox("Type", list(MATERIALS.keys()), key=f"type_{entry['id']}", index=0)
        with material_col:
            material_options = list(MATERIALS.get(entry['type'], {}).keys())
            if not material_options:
                st.warning(f"No materials defined for type '{entry['type']}'")
                entry['material'] = None
            else:
                if entry.get('material') not in material_options:
                    entry['material'] = material_options[0]
                entry['material'] = st.selectbox("Material", material_options, key=f"material_{entry['id']}")
        with remove_col:
            st.write("")
            st.write("")
            if st.button("❌", key=f"remove_{entry['id']}", help="Remove this entry"):
                return "remove_entry", None, None

        # --- Dimensions and Quantity ---
        dim_col1, dim_col2, dim_col3 = st.columns([2, 2, 2])
        with dim_col1:
            w_ft_col, w_in_col = st.columns(2)
            with w_ft_col: entry['w_ft'] = st.number_input("Width (ft)", min_value=0, key=f"w_ft_{entry['id']}", value=entry.get('w_ft', 0))
            with w_in_col: entry['w_in'] = st.number_input("Width (in)", min_value=0, key=f"w_in_{entry['id']}", value=entry.get('w_in', 0))
        with dim_col2:
            h_ft_col, h_in_col = st.columns(2)
            with h_ft_col: entry['h_ft'] = st.number_input("Height (ft)", min_value=0, key=f"h_ft_{entry['id']}", value=entry.get('h_ft', 0))
            with h_in_col: entry['h_in'] = st.number_input("Height (in)", min_value=0, key=f"h_in_{entry['id']}", value=entry.get('h_in', 0))
        with dim_col3:
            entry['qty'] = st.number_input("Num of pieces", min_value=1, key=f"qty_{entry['id']}", value=entry.get('qty', 1))

        # --- Core Calculations ---
        total_width_inches = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
        total_height_inches = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
        sqft_per_piece = (total_width_inches * total_height_inches) / 144
        total_sqft_entry = sqft_per_piece * entry.get('qty', 1)

        base_price_per_sqft = 0
        active_base_amount = 0
        active_max_discount = 0 # RESTORED: Initialize variable
        
        if entry.get('material'):
            material_data = MATERIALS.get(entry['type'], {}).get(entry['material'], {})
            if material_data:
                calculated_prices = calculate_material_price(material_data)
                price_map = {'Preferred': 'preferred_value', 'Corporate': 'corporate_value', 'Wholesale': 'wholesale_value'}
                base_map = {'Preferred': 'preferred_base', 'Corporate': 'corporate_base', 'Wholesale': 'wholesale_base'}
                
                # RESTORED: Calculate all necessary price values
                active_base_amount = calculated_prices.get(base_map.get(customer_type, 'preferred_base'), 0)
                active_max_discount = calculated_prices.get(price_map.get(customer_type, 'preferred_value'), 0)
                base_price_per_sqft = active_max_discount

        # --- Display Metrics ---
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1: st.metric(label="SQ'/piece", value=f"{sqft_per_piece:.2f}")
        with metric_col2: st.metric(label="Total SQ'", value=f"{total_sqft_entry:.2f}")
        with metric_col3: st.metric(label="Applied Price/SQ'", value=f"${base_price_per_sqft:.2f}")
        
        # RESTORED: Display for BASE AMOUNT and MAX DISCOUNT
        st.markdown("---")
        price_col1, price_col2 = st.columns(2)
        with price_col1:
            st.metric(label="BASE AMOUNT", value=f"${active_base_amount:.2f}")
        with price_col2:
            st.metric(label="MAX DISCOUNT", value=f"${active_max_discount:.2f}")
        st.divider()

        # --- Addon Selections ---
        sc1, sc2, sc3 = st.columns([1, 2, 3])
        with sc1:
            sidedness_index = SIDEDNESS_OPTIONS.index(entry.get('sidedness', SIDEDNESS_OPTIONS[0]))
            entry['sidedness'] = st.selectbox("Sidedness", options=SIDEDNESS_OPTIONS, key=f"side_{entry['id']}", index=sidedness_index)
        with sc2:
            suggested_tier = get_suggested_sides_tier(sqft_per_piece, entry['sidedness'])
            try: tier_index = TIER_DESCRIPTIONS.index(suggested_tier)
            except ValueError: tier_index = 0
            def format_tier_option(option_name): return f"{option_name} - ${SIDES_TIERS_MAP.get(option_name, 0):.2f}"
            selected_tier_desc = st.selectbox("Tier", options=TIER_DESCRIPTIONS, index=tier_index, key=f"sides_tier_{entry['id']}", format_func=format_tier_option)
            entry['sides_tier_selection'] = selected_tier_desc
        with sc3:
            sides_cost_per_unit = SIDES_TIERS_MAP.get(entry.get('sides_tier_selection'), 0)
            st.metric(label="Sides Cost/Unit", value=f"${sides_cost_per_unit:.2f}")
        
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            if entry.get('finishing_type') is None: entry['finishing_type'] = 'Nothing Special'
            if entry['type'] == "Banner" and entry.get('finishing_type') == 'Nothing Special': entry['finishing_type'] = "Banner/Mesh"
            try: finishing_type_index = FINISHING_TYPES.index(entry.get('finishing_type'))
            except ValueError: finishing_type_index = 0
            selected_type = st.selectbox("Finishing Type", options=FINISHING_TYPES, key=f"fin_type_{entry['id']}", index=finishing_type_index)
            entry['finishing_type'] = selected_type
        with fc2:
            options_for_type = SPECIALTY_FINISHING.get(selected_type, {})
            finishing_price_per_unit = 0
            if selected_type == "Banner/Mesh" and "POCKET or HEMM AND GROMMETS EVERY 2'" in options_for_type:
                 dynamic_option_name, finishing_price_per_unit = get_banner_mesh_details(sqft_per_piece, options_for_type)
                 st.text_input("Finishing Option", value=dynamic_option_name, key=f"fin_opt_{entry['id']}", disabled=True)
            else:
                if list(options_for_type.keys()):
                    selected_option = st.selectbox("Finishing Option", options=list(options_for_type.keys()), key=f"fin_opt_{entry['id']}", index=0)
                    entry['finishing_option'] = selected_option
                    finishing_price_per_unit = options_for_type.get(selected_option, 0)
                else:
                    st.text_input("Finishing Option", value="N/A", key=f"fin_opt_{entry['id']}", disabled=True)
        with fc3:
            st.metric(label="Finishing Cost/Unit", value=f"${finishing_price_per_unit:.2f}")

        cc1, cc2 = st.columns(2)
        with cc1:
            selected_cut_cost_desc = st.selectbox("Cut Option", options=CUT_COST_OPTIONS, key=f"cut_cost_{entry['id']}", index=0)
            entry['cut_cost_selection'] = selected_cut_cost_desc
            cut_cost_per_unit = CUT_COST_MAP.get(selected_cut_cost_desc, 0)
        with cc2:
            st.metric(label="Cut Cost/Unit", value=f"${cut_cost_per_unit:.2f}")

        at1, at2 = st.columns(2)
        with at1:
            default_at_index = 0
            if entry.get('additional_time_selection') in ADDITIONAL_TIME_OPTIONS: default_at_index = ADDITIONAL_TIME_OPTIONS.index(entry['additional_time_selection'])
            selected_at_desc = st.selectbox("Additional Time", options=ADDITIONAL_TIME_OPTIONS, key=f"add_time_{entry['id']}", index=default_at_index)
            entry['additional_time_selection'] = selected_at_desc
            additional_time_cost_per_unit = ADDITIONAL_TIME_MAP.get(selected_at_desc, 0)
        with at2:
            st.metric(label="Additional Time Cost/Unit", value=f"${additional_time_cost_per_unit:.2f}")

        ai1, ai2 = st.columns(2)
        with ai1:
            default_ai_index = 0
            if entry.get('added_install_selection') in ADDED_INSTALL_OPTIONS: default_ai_index = ADDED_INSTALL_OPTIONS.index(entry['added_install_selection'])
            selected_ai_desc = st.selectbox("Added Install/Item Per Piece", options=ADDED_INSTALL_OPTIONS, key=f"added_install_{entry['id']}", index=default_ai_index)
            entry['added_install_selection'] = selected_ai_desc
            added_install_cost_per_unit = ADDED_INSTALL_MAP.get(selected_ai_desc, 0)
        with ai2:
            st.metric(label="Added Install Cost/Unit", value=f"${added_install_cost_per_unit:.2f}")
    
    # --- Data for Export and Calculation ---
    export_data = { "Type": entry.get('type'), "Material": entry.get('material'), "Num of pieces": entry.get('qty'), "Width (in)": total_width_inches, "Height (in)": total_height_inches, "SQ' per piece": f"{sqft_per_piece:.2f}", "Total SQ'": f"{total_sqft_entry:.2f}"}
    
    calculation_data = {
        "qty": entry.get('qty', 1),
        "sqft_per_piece": sqft_per_piece,
        "total_sqft_entry": total_sqft_entry,
        "base_price_per_sqft": base_price_per_sqft,
        "active_base_amount": active_base_amount,
        "sides_cost_per_unit": sides_cost_per_unit,
        "finishing_price_per_unit": finishing_price_per_unit,
        "cut_cost_per_unit": cut_cost_per_unit,
        "additional_time_cost_per_unit": additional_time_cost_per_unit,
        "added_install_cost_per_unit": added_install_cost_per_unit,
    }

    return "ok", export_data, calculation_data

# --- Initialize session state ---
if 'entries' not in st.session_state:
    st.session_state.entries = []
    if MATERIALS.get("Banner"):
        default_material = list(MATERIALS["Banner"].keys())[0]
        default_additional_time = ADDITIONAL_TIME_OPTIONS[0] if ADDITIONAL_TIME_OPTIONS else None
        default_added_install = ADDED_INSTALL_OPTIONS[0] if ADDED_INSTALL_OPTIONS else None
        st.session_state.entries.append({
            "id": str(uuid.uuid4()),"type": "Banner", "material": default_material, 
            "w_ft": 0,"w_in": 0,"h_ft": 0,"h_in": 0,"qty": 1, 
            "sidedness": "Single Sided", "finishing_type": "Nothing Special", 
            "cut_cost_selection": "NO CUT",
            "additional_time_selection": default_additional_time,
            "added_install_selection": default_added_install
        })

# --- SIDEBAR (Gets customer type first) ---
st.sidebar.header("Quote Summary")
if not CUSTOMER_TYPES:
    st.sidebar.error("Customer types not defined in config.")
    st.stop()
customer_type_index = CUSTOMER_TYPES.index(st.sidebar.selectbox("Select Customer Type", options=CUSTOMER_TYPES, index=0))
selected_customer_type = CUSTOMER_TYPES[customer_type_index]

# --- Main App Logic ---
all_calculations = []
data_for_export = []
remove_entry_index = None

if not st.session_state.entries:
    st.warning("No quote entries yet. Click below to add one.")

for i, entry in enumerate(st.session_state.entries):
    status, export_data, calc_data = render_expanded_layout(entry, i, selected_customer_type)
    if status == "remove_entry": 
        remove_entry_index = i
    else:
        all_calculations.append(calc_data)
        data_for_export.append(export_data)

if remove_entry_index is not None:
    st.session_state.entries.pop(remove_entry_index)
    st.rerun()

st.divider()
if st.button("➕ Add New Entry", use_container_width=True):
    if MATERIALS.get("Banner"):
        default_material = list(MATERIALS["Banner"].keys())[0]
        default_additional_time = ADDITIONAL_TIME_OPTIONS[0] if ADDITIONAL_TIME_OPTIONS else None
        default_added_install = ADDED_INSTALL_OPTIONS[0] if ADDED_INSTALL_OPTIONS else None
        st.session_state.entries.append({
            "id": str(uuid.uuid4()),"type": "Banner","material": default_material,
            "w_ft": 0,"w_in": 0,"h_ft": 0,"h_in": 0,"qty": 1, 
            "sidedness": "Single Sided", "finishing_type": "Nothing Special", 
            "cut_cost_selection": "NO CUT",
            "additional_time_selection": default_additional_time,
            "added_install_selection": default_added_install
        })
        st.rerun()

# --- SIDEBAR (Calculations and Display) ---
with st.sidebar.expander("Go to Entry...", expanded=True):
    for i, entry in enumerate(st.session_state.entries):
        material = entry.get('material', 'N/A')
        summary_text = f"**{material}**: {entry.get('w_ft', 0)}' {entry.get('w_in', 0)}\" x {entry.get('h_ft', 0)}' {entry.get('h_in', 0)}\" (Qty: {entry.get('qty', 1)})"
        st.markdown(f"[{summary_text}](#entry-{entry['id']})", unsafe_allow_html=True)

st.sidebar.divider()
total_sqft_order = sum(c['total_sqft_entry'] for c in all_calculations)
st.sidebar.metric(label="TOTAL SQ' IN ORDER", value=f"{total_sqft_order:.2f}")
st.sidebar.divider()

# --- Sidebar Discount and Adjustment Controls ---
st.sidebar.markdown("#### SQ' Discount")
if VOLUME_DISCOUNT_TIERS:
    discount_tier_options = {desc: discounts for _, (desc, discounts) in sorted(VOLUME_DISCOUNT_TIERS.items())}
    options_list = list(discount_tier_options.keys())
    auto_selected_tier = get_discount_tier_details(total_sqft_order, VOLUME_DISCOUNT_TIERS)
    try: default_index = options_list.index(auto_selected_tier)
    except ValueError: default_index = 0
    def format_discount_option(description):
        discounts = discount_tier_options[description]
        return f"{description} ({discounts[0]:.2%}/{discounts[1]:.2%}/{discounts[2]:.2%})"
    selected_tier_description = st.sidebar.selectbox("Discount Tier", options=options_list, index=default_index, format_func=format_discount_option, help="This is automatically selected based on Total SQ', but you can override it.")
    selected_percentage = discount_tier_options[selected_tier_description][customer_type_index]
    st.sidebar.info(f"Applying **{selected_percentage:.2%}** discount for **{selected_customer_type}** customer.")
else:
    selected_percentage = 0
st.sidebar.divider()

st.sidebar.markdown("#### Print Adjustment")
if PRINT_ADJUSTMENT_FIXED:
    selected_adjustment_label = st.sidebar.selectbox("Select Adjustment", options=list(PRINT_ADJUSTMENT_FIXED.keys()), index=0)
    adjustment_percentage = PRINT_ADJUSTMENT_FIXED[selected_adjustment_label]
else:
    adjustment_percentage = 0
st.sidebar.divider()

st.sidebar.markdown("#### Additional Costs")
cons_bx_4 = st.sidebar.number_input("cons_bx_4", value=12.50, format="%.2f")
cons_bx_6 = st.sidebar.number_input("cons_bx_6", value=12.50, format="%.2f")
prodcuts_an = st.sidebar.number_input("prodcuts_an", value=16.21, format="%.2f")
st.sidebar.divider()

st.sidebar.markdown("#### Multiples")
num_entries = len(st.session_state.entries)
multiple_desc, multiples_value = get_multiplier(num_entries)
st.sidebar.metric(label=f"Multiplier ({multiple_desc})", value=f"x{multiples_value}")

# --- GRAND TOTAL CALCULATION ---
grand_total = 0

if selected_customer_type == 'Preferred':
    # NEW PREFERRED LOGIC: Switched to the new detailed formula for Preferred customers.
    total_pieces_in_quote = sum(c['qty'] for c in all_calculations)
    if total_pieces_in_quote > 0 and multiples_value > 0:
        preferred_total = 0
        for calc in all_calculations:
            # Part A
            part_a_base = calc['active_base_amount'] * calc['sqft_per_piece'] * calc['sides_cost_per_unit']
            print(f"part_a_base Formula: calc['active_base_amount'] * calc['sqft_per_piece'] * calc['sides_cost_per_unit']")
            print(f"calc['active_base_amount']: {calc['active_base_amount']}, calc['sqft_per_piece']: {calc['sqft_per_piece']}, calc['sides_cost_per_unit']: {calc['sides_cost_per_unit']}")
            print(f"part_a_base----------->: {part_a_base}")

            part_a_discounted = part_a_base * (1 - (selected_percentage + adjustment_percentage))
            print(f"part_a_discounted Formula: part_a_base * (1 - (selected_percentage + adjustment_percentage))")
            print(f"part_a_base: {part_a_base}, selected_percentage: {selected_percentage}, adjustment_percentage: {adjustment_percentage}")
            print(f"part_a_discounted----------->: {part_a_discounted}")

            # Part B
            part_b_original = calc['cut_cost_per_unit'] * calc['sqft_per_piece']
            part_b = part_b_original + part_a_discounted
            print(f"part_b Formula: calc['cut_cost_per_unit'] * calc['sqft_per_piece']")
            print(f"calc['cut_cost_per_unit']: {calc['cut_cost_per_unit']}, calc['sqft_per_piece']: {calc['sqft_per_piece']}")
            print(f"part_b----------->: {part_b}")

            # Part C
            part_c_numerator = (calc['finishing_price_per_unit'] * calc['sqft_per_piece'] * calc['qty']) + (prodcuts_an / multiples_value)
            part_c = part_c_numerator / total_pieces_in_quote
            print(f"part_c Formula: (calc['finishing_price_per_unit'] * calc['sqft_per_piece'] * calc['qty']) + (prodcuts_an / multiples_value) / total_pieces_in_quote")
            print(f"calc['finishing_price_per_unit']: {calc['finishing_price_per_unit']}, calc['sqft_per_piece']: {calc['sqft_per_piece']}, calc['qty']: {calc['qty']}, prodcuts_an: {prodcuts_an}, multiples_value: {multiples_value}")
            print(f"part_c----------->: {part_c}")

            # Part D
            part_d = (cons_bx_4 / multiples_value) / total_pieces_in_quote
            print(f"part_d Formula: (cons_bx_4 / multiples_value) / total_pieces_in_quote")
            print(f"cons_bx_4: {cons_bx_4}, multiples_value: {multiples_value}, total_pieces_in_quote: {total_pieces_in_quote}")
            print(f"part_d----------->: {part_d}")

            # Part E
            part_e = (cons_bx_6 / multiples_value) / total_pieces_in_quote
            print(f"part_e Formula: (cons_bx_6 / multiples_value) / total_pieces_in_quote")
            print(f"cons_bx_6: {cons_bx_6}, multiples_value: {multiples_value}, total_pieces_in_quote: {total_pieces_in_quote}")
            print(f"part_e----------->: {part_e}")

            # Part F
            part_f = (calc['additional_time_cost_per_unit'] / total_pieces_in_quote) + calc['added_install_cost_per_unit']
            print(f"part_f Formula: (calc['additional_time_cost_per_unit'] / total_pieces_in_quote) + calc['added_install_cost_per_unit']")
            print(f"calc['additional_time_cost_per_unit']: {calc['additional_time_cost_per_unit']}, total_pieces_in_quote: {total_pieces_in_quote}, calc['added_install_cost_per_unit']: {calc['added_install_cost_per_unit']}")
            print(f"part_f----------->: {part_f}")
            print("--------------------------------")
            # Sum of parts for a single piece of this line item
            price_per_single_piece = part_b + part_c + part_d + part_e + part_f
            print(f"price_per_single_piece Formula: part_a_discounted + part_b + part_c + part_d + part_e + part_f")
            print(f"part_a_discounted: {part_a_discounted}, part_b: {part_b}, part_c: {part_c}, part_d: {part_d}, part_e: {part_e}, part_f: {part_f}")
            print(f"price_per_single_piece----------->: {price_per_single_piece}")
            
            # Add the total for this line item (price per piece * its quantity) to the running total
            # preferred_total += price_per_single_piece * calc['qty']

        # Apply final markup
        # grand_total = preferred_total * 1.1
        grand_total = price_per_single_piece * 1.1


else:
    # Original logic for Corporate and Wholesale
    total_base_price = sum(c['total_sqft_entry'] * c['base_price_per_sqft'] for c in all_calculations)
    total_order_addon_cost = sum(
        (c['sides_cost_per_unit'] + c['finishing_price_per_unit'] + c['cut_cost_per_unit'] + c['additional_time_cost_per_unit'] + c['added_install_cost_per_unit']) * c['qty'] 
        for c in all_calculations
    )
    subtotal = total_base_price + total_order_addon_cost
    price_after_sq_discount = subtotal * (1 - selected_percentage)
    price_after_print_adjustment = price_after_sq_discount * (1 + adjustment_percentage)
    grand_total = price_after_print_adjustment * multiples_value

# --- Display Grand Total ---
st.sidebar.markdown("### Grand Total")
st.sidebar.markdown(f"<h2 style='text-align: right; color: green;'>${grand_total:,.2f}</h2>", unsafe_allow_html=True)
st.sidebar.divider()