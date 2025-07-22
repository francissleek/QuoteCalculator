import streamlit as st
import uuid
import pandas as pd
import json
import math
import os
from collections import Counter
from modules.config_loader import load_config
from modules.calculations import calculate_material_price
from modules.helpers import get_discount_tier_details, get_multiplier

os.environ.setdefault('TERM', 'xterm')
# --- Page Configuration (BEST PRACTICE FIX: Must be the first st command) ---
st.set_page_config(layout="wide", page_title="Quote Calculator")

st.markdown("""
<style>
    /* Target all widget labels */
    .st-emotion-cache-ue6h4q {
        font-size: 14px;
    }
    /* Target the text inside all selectboxes */
    .stSelectbox div[data-baseweb="select"] > div {
        font-size: 14px;
    }
    /* Target the text inside all number inputs */
    .st-emotion-cache-12h6tpf {
        font-size: 14px;
    }
    /* Target the "Total SQ' IN ORDER" metric label */
    .st-emotion-cache-1g8sf3i {
        font-size: 14px;
    }
    /* Target the main metric labels (e.g., "Preferred (36.00%)") */
    div[data-testid="stMetricLabel"] {
        font-size: 13px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 35px;
    }
</style>
""", unsafe_allow_html=True)


st.title("Quote Calculator")

if 'config' not in st.session_state:
    st.session_state.config = load_config()

config = st.session_state.config

# --- Unpack loaded data from config ---
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

# --- DYNAMIC COST CALCULATION (Original) ---
def calculate_additional_costs(cost_config):
    bx4_vars = cost_config.get("cons_bx_4", {})
    bx4_v1 = bx4_vars.get("variable_1", 0)
    bx4_v2 = bx4_vars.get("variable_2", 1)
    bx4_v3 = bx4_vars.get("variable_3", 0)
    calculated_bx4 = (bx4_v1 / bx4_v2) * bx4_v3 if bx4_v2 != 0 else 0

    bx6_vars = cost_config.get("cons_bx_6", {})
    bx6_v1 = bx6_vars.get("variable_1", 0)
    bx6_v2 = bx6_vars.get("variable_2", 1)
    bx6_v3 = bx6_vars.get("variable_3", 0)
    calculated_bx6 = (bx6_v1 / bx6_v2) * bx6_v3 if bx6_v2 != 0 else 0

    default_prodcuts_an = cost_config.get("prodcuts_an", 16.21)
    return calculated_bx4, calculated_bx6, default_prodcuts_an

ADDITIONAL_COSTS_CONFIG = config.get('ADDITIONAL_COSTS', {})
cons_bx_4, cons_bx_6, default_prodcuts_an = calculate_additional_costs(ADDITIONAL_COSTS_CONFIG)

# --- NEW: DYNAMIC PRODCUTS_AN CALCULATION ---
def calculate_dynamic_prodcuts_an(vars, Q_Quantity):
    if not vars or Q_Quantity == 0:
        return 0, 0
    AW_Roll_Costs = vars.get("AW_Roll_Costs", 0)
    AU_Material_Length = vars.get("AU_Material_Length", 1)
    AV_Material_Width = vars.get("AV_Material_Width", 1)
    AQ_SQ = vars.get("AQ_SQ", 0)
    AS_Laminate_Loading = vars.get("AS_Laminate_Loading", 0)
    AT_Labour = vars.get("AT_Labour", 0)
    constant_BY8 = vars.get("constant_BY8", 0)
    Per_hour_rate = vars.get("Per_hour_rate", 0)
    denominator_ax = (AU_Material_Length * AV_Material_Width) / 144
    AX_Sq_material = AW_Roll_Costs / denominator_ax if denominator_ax != 0 else 0
    form_response_bx8 = (constant_BY8 / 60) * Per_hour_rate
    AO = (AX_Sq_material * AQ_SQ) + AS_Laminate_Loading + AT_Labour
    AN = AO + (form_response_bx8 / Q_Quantity) + AS_Laminate_Loading
    return AO, AN

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
            return f"{desc_prefix} - {option_name}", price
    return "N/A", 0.0

# --- NEW CALCULATION LOGIC ---
def calculate_entry_total(calc_data, customer_type, selected_percentage, adjustment_percentage, multiples_value, prodcuts_an):
    """Calculates the total for a single line item based on the customer type."""
    multiples_value_for_entry = multiples_value
    entry_total = 0
    entry_quantity = calc_data.get('qty', 0)
    if entry_quantity == 0:
        return 0
    print(f"--------------------------------------------- {customer_type} ---------------------------------------------")
    # Part A
    part_a_base = calc_data['active_base_amount'] * calc_data['sqft_per_piece'] * calc_data['sides_cost_per_unit']
    print(f"Formula part_a_base: calc_data['active_base_amount'] * calc_data['sqft_per_piece'] * calc_data['sides_cost_per_unit']")
    print(f"calc_data['active_base_amount'] = {calc_data['active_base_amount']}, calc_data['sqft_per_piece'] = {calc_data['sqft_per_piece']}, calc_data['sides_cost_per_unit'] = {calc_data['sides_cost_per_unit']} = {calc_data['sides_cost_per_unit']}")
    print(f"part_a_base = {part_a_base}")

    part_a_discounted = part_a_base * (1 - (selected_percentage + adjustment_percentage))
    print(f"Formula part_a_discounted: part_a_base * (1 - (selected_percentage + adjustment_percentage))")
    print(f"part_a_base = {part_a_base}, selected_percentage = {selected_percentage}, adjustment_percentage = {adjustment_percentage}")
    print(f"part_a_discounted = {part_a_discounted}")

    # Part B
    part_b_original = calc_data['cut_cost_per_unit'] * calc_data['sqft_per_piece']
    print(f"Formula part_b_original: calc_data['cut_cost_per_unit'] * calc_data['sqft_per_piece']")
    print(f"calc_data['cut_cost_per_unit'] = {calc_data['cut_cost_per_unit']}, calc_data['sqft_per_piece'] = {calc_data['sqft_per_piece']}")
    print(f"part_b_original = {part_b_original}")

    part_b = part_b_original + part_a_discounted
    print(f"Formula part_b: part_b_original + part_a_discounted")
    print(f"part_b_original = {part_b_original}, part_a_discounted = {part_a_discounted}")
    print(f"part_b = {part_b}")

    # Part C - Uses the entry's own quantity
    part_c_numerator = (calc_data['finishing_price_per_unit'] * calc_data['sqft_per_piece'] * entry_quantity) + (prodcuts_an / multiples_value_for_entry)
    print(f"Formula part_c_numerator: (calc_data['finishing_price_per_unit'] * calc_data['sqft_per_piece'] * entry_quantity) + (prodcuts_an / multiples_value_for_entry)")
    print(f"prodcuts_an: {prodcuts_an}")
    print(f"part_c_numerator = {calc_data['finishing_price_per_unit']} * {calc_data['sqft_per_piece']} * {entry_quantity} + {prodcuts_an} / {multiples_value_for_entry}, part_a_discounted = {part_a_discounted}")
    print(f"part_c_numerator = {part_c_numerator}")

    part_c = part_c_numerator / entry_quantity
    print(f"Formula part_c: part_c_numerator / entry_quantity")
    print(f"part_c_numerator = {part_c_numerator}, entry_quantity = {entry_quantity}")
    print(f"={part_c}")

    if calc_data['cut_cost_per_unit'] == 0.0:
        part_d = 0
        print(f"Formula part_d: 0")
    elif customer_type == 'Preferred':
        part_d = (cons_bx_4 / multiples_value_for_entry) / entry_quantity
        print(f"Formula part_d: (cons_bx_4 / multiples_value_for_entry) / entry_quantity")
        print(f"cons_bx_4 = {cons_bx_4}, multiples_value_for_entry = {multiples_value_for_entry}, entry_quantity = {entry_quantity}")
        print(f"part_d={part_d}")
    elif customer_type in ['Corporate', 'Wholesale']:
        part_d = (cons_bx_4 / (multiples_value_for_entry + 0.5)) / entry_quantity
        print(f"Formula part_d: (cons_bx_4 / multiples_value_for_entry + 0.5) / entry_quantity")
        print(f"cons_bx_4 = {cons_bx_4}, multiples_value_for_entry = {multiples_value_for_entry}, entry_quantity = {entry_quantity}")
        print(f"part_d={part_d}")

    if calc_data['finishing_price_per_unit'] == 0:
        part_e = 0
        print(f"Formula part_e: 0")
    elif customer_type == 'Preferred':
        part_e = (cons_bx_6 / multiples_value_for_entry) / entry_quantity
        print(f"Formula part_e: (cons_bx_6 / multiples_value_for_entry) / entry_quantity")
        print(f"cons_bx_6 = {cons_bx_6}, multiples_value_for_entry = {multiples_value_for_entry}, entry_quantity = {entry_quantity}")
        print(f"part_e={part_e}")
    elif customer_type in ['Corporate', 'Wholesale']:
        part_e = (cons_bx_6 / (multiples_value_for_entry + 0.5)) / entry_quantity
        print(f"Formula part_e: (cons_bx_6 / multiples_value_for_entry  + 0.5) / entry_quantity")
        print(f"cons_bx_6 = {cons_bx_6}, multiples_value_for_entry = {multiples_value_for_entry}, entry_quantity = {entry_quantity}")
        print(f"part_e={part_e}")

    part_f = (calc_data['additional_time_cost_per_unit'] / entry_quantity) + calc_data['added_install_cost_per_unit']
    print(f"Formula part_f: (calc_data['additional_time_cost_per_unit'] / entry_quantity) + calc_data['added_install_cost_per_unit']")
    print(f"calc_data['additional_time_cost_per_unit'] = {calc_data['additional_time_cost_per_unit']}, entry_quantity = {entry_quantity}")
    print(f"part_f={part_f}")

    price_per_single_piece = part_b + part_c + part_d + part_e + part_f
    print(f"Formula price_per_single_piece: part_b + part_c + part_d + part_e + part_f")
    print(f"part_b = {part_b}, part_c = {part_c}, part_d = {part_d}, part_e = {part_e}, part_f = {part_f}")
    print(f"price_per_single_piece={price_per_single_piece}")

    entry_total = (price_per_single_piece) * 1.1
    print(f"Formula entry_total: (price_per_single_piece) * 1.1")
    print(f"price_per_single_piece = {price_per_single_piece}")
    return entry_total

def calculate_all_prices_for_entry(calculation_data, all_material_prices, all_discount_percentages, adjustment_percentage, multiples_value, prodcuts_an_for_entry):
    all_prices = {}

    customer_types_map = {
        'Preferred': {'base': all_material_prices.get('preferred_base', 0), 'value': all_material_prices.get('preferred_value', 0), 'discount': all_discount_percentages[0]},
        'Corporate': {'base': all_material_prices.get('corporate_base', 0), 'value': all_material_prices.get('corporate_value', 0), 'discount': all_discount_percentages[1]},
        'Wholesale': {'base': all_material_prices.get('wholesale_base', 0), 'value': all_material_prices.get('wholesale_value', 0), 'discount': all_discount_percentages[2]}
    }
    os.system('cls' if os.name == 'nt' else 'clear')

    for cust_type, data in customer_types_map.items():
        # Assemble the specific calc_data for this customer type
        specific_calc_data = calculation_data.copy()
        print(f"ACTIVE BASE AMOUNT: {data['base']}")
        print(f"CUSTOMER MAPPING: {customer_types_map}")
        specific_calc_data['active_base_amount'] = data['base']
        specific_calc_data['base_price_per_sqft'] = data['value']
        all_prices[cust_type] = calculate_entry_total(
            specific_calc_data,
            cust_type,
            data['discount'],
            adjustment_percentage,
            multiples_value,
            prodcuts_an_for_entry
        )
    return all_prices

# --- INSTANT UPDATE SOLUTION: Callback Functions ---
def trigger_recalculation():
    """This callback recalculates the total SQFT from the main entries list and stores it in session_state."""
    total_sqft = sum(
        (((e.get('w_ft', 0) * 12 + e.get('w_in', 0)) * (e.get('h_ft', 0) * 12 + e.get('h_in', 0))) / 144) * e.get('qty', 1)
        for e in st.session_state.entries
    )
    st.session_state.total_sqft_order = total_sqft

def sync_entry_and_recalculate(entry_id, field_name):
    """
    This is the master callback. It syncs the widget's value to the
    st.session_state.entries list and then triggers the main recalculation.
    """
    for entry in st.session_state.entries:
        if entry['id'] == entry_id:
            widget_key = f"{field_name}_{entry_id}"
            if widget_key in st.session_state:
                entry[field_name] = st.session_state[widget_key]
                trigger_recalculation()
                # No st.rerun() here, it will be handled by the main loop check
            break

# --- Layout Rendering Function ---
### MODIFIED: Added 'is_last_entry' parameter to the function signature
def render_expanded_layout(entry, i, total_sqft_order, multiples_value, multiples_label, is_last_entry):
    ### ADDED: Logic to create a summary label for the expander
    material_name = entry.get('material', 'New Entry')
    w_ft = entry.get('w_ft', 0)
    w_in = entry.get('w_in', 0)
    h_ft = entry.get('h_ft', 0)
    h_in = entry.get('h_in', 0)
    qty = entry.get('qty', 1)
    summary_label = f"#{i+1}: {material_name} — {w_ft}' {w_in}\" x {h_ft}' {h_in}\" (Qty: {qty})"

    ### MODIFIED: Replaced st.container with st.expander
    with st.expander(summary_label, expanded=is_last_entry):
        st.markdown(f"<a name='entry-{entry['id']}'></a>", unsafe_allow_html=True)

        type_col, material_col, remove_col = st.columns([2, 3, 1])
        with type_col:
            type_options = list(MATERIALS.keys())
            type_index = type_options.index(entry.get('type', type_options[0]))
            st.selectbox("Type", type_options, index=type_index, key=f"type_{entry['id']}", on_change=sync_entry_and_recalculate, args=(entry['id'], 'type'))
        with material_col:
            material_options = list(MATERIALS.get(entry['type'], {}).keys())
            if material_options:
                if entry.get('material') not in material_options: entry['material'] = material_options[0]
                material_index = material_options.index(entry.get('material', material_options[0]))
                st.selectbox("Material", material_options, index=material_index, key=f"material_{entry['id']}", on_change=sync_entry_and_recalculate, args=(entry['id'], 'material'))
            else:
                st.warning(f"No materials for type '{entry['type']}'"); entry['material'] = None
        with remove_col:
            st.write(""); st.write("")
            if st.button("❌", key=f"remove_{entry['id']}", help="Remove this entry"):
                return "remove_entry", None

        dim_col1, dim_col2, dim_col3 = st.columns([2, 2, 2])
        with dim_col1:
            w_ft_col, w_in_col = st.columns(2)
            with w_ft_col: st.number_input("Width (ft)", min_value=0, key=f"w_ft_{entry['id']}", value=entry.get('w_ft', 0), on_change=sync_entry_and_recalculate, args=(entry['id'], 'w_ft'))
            with w_in_col: st.number_input("Width (in)", min_value=0, key=f"w_in_{entry['id']}", value=entry.get('w_in', 0), on_change=sync_entry_and_recalculate, args=(entry['id'], 'w_in'))
        with dim_col2:
            h_ft_col, h_in_col = st.columns(2)
            with h_ft_col: st.number_input("Height (ft)", min_value=0, key=f"h_ft_{entry['id']}", value=entry.get('h_ft', 0), on_change=sync_entry_and_recalculate, args=(entry['id'], 'h_ft'))
            with h_in_col: st.number_input("Height (in)", min_value=0, key=f"h_in_{entry['id']}", value=entry.get('h_in', 0), on_change=sync_entry_and_recalculate, args=(entry['id'], 'h_in'))
        with dim_col3:
            st.number_input("Num of pieces", min_value=1, key=f"qty_{entry['id']}", value=entry.get('qty', 1), on_change=sync_entry_and_recalculate, args=(entry['id'], 'qty'))

        total_width_inches = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
        total_height_inches = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
        sqft_per_piece = (total_width_inches * total_height_inches) / 144
        total_sqft_entry = sqft_per_piece * entry.get('qty', 1)

        material_data = {}
        all_material_prices = {}
        print(f"ayoooooooooooooo material_data: {entry.get('material')}")
        if entry.get('material'):
            material_data = MATERIALS.get(entry['type'], {}).get(entry['material'], {})
            
            if material_data:
                all_material_prices = calculate_material_price(material_data)

        metric_col1, metric_col2, _ = st.columns(3)
        metric_col1.metric(label="SQ'/piece", value=f"{sqft_per_piece:.2f}")
        metric_col2.metric(label="Total SQ'", value=f"{total_sqft_entry:.2f}")

        st.markdown("---")
        st.write("Base Amount per SQ' (Before Volume Discounts)")
        pref_col, corp_col, whole_col = st.columns(3)
        pref_col.metric(label="Preferred Base", value=f"${all_material_prices.get('preferred_base', 0):.2f}")
        corp_col.metric(label="Corporate Base", value=f"${all_material_prices.get('corporate_base', 0):.2f}")
        whole_col.metric(label="Wholesale Base", value=f"${all_material_prices.get('wholesale_base', 0):.2f}")
        st.divider()

        sc1, sc2, sc3 = st.columns([1, 2, 3])
        sidedness_index = SIDEDNESS_OPTIONS.index(entry.get('sidedness', SIDEDNESS_OPTIONS[0]))
        entry['sidedness'] = sc1.selectbox("Sidedness", options=SIDEDNESS_OPTIONS, index=sidedness_index, key=f"side_{entry['id']}")
        suggested_tier = get_suggested_sides_tier(sqft_per_piece, entry['sidedness'])
        try: tier_index = TIER_DESCRIPTIONS.index(suggested_tier)
        except ValueError: tier_index = 0
        def format_tier_option(name): return f"{name} - ${SIDES_TIERS_MAP.get(name, 0):.2f}"
        selected_tier_desc = sc2.selectbox("Tier", options=TIER_DESCRIPTIONS, index=tier_index, key=f"sides_tier_{entry['id']}", format_func=format_tier_option)
        entry['sides_tier_selection'] = selected_tier_desc
        sides_cost_per_unit = SIDES_TIERS_MAP.get(selected_tier_desc, 0)
        # sc3.metric(label="Sides Cost/Unit", value=f"${sides_cost_per_unit:.2f}")

        fc1, fc2, fc3 = st.columns(3)
        if entry.get('finishing_type') is None: entry['finishing_type'] = 'Nothing Special'
        if entry['type'] == "Banner" and entry.get('finishing_type') == 'Nothing Special': entry['finishing_type'] = "Banner/Mesh"
        try: finishing_type_index = FINISHING_TYPES.index(entry.get('finishing_type'))
        except ValueError: finishing_type_index = 0
        selected_type = fc1.selectbox("Finishing Type", options=FINISHING_TYPES, index=finishing_type_index, key=f"fin_type_{entry['id']}")
        entry['finishing_type'] = selected_type
        options_for_type = SPECIALTY_FINISHING.get(selected_type, {})
        finishing_price_per_unit = 0
        if selected_type == "Banner/Mesh" and "POCKET or HEMM AND GROMMETS EVERY 2'" in options_for_type:
            dynamic_option_name, finishing_price_per_unit = get_banner_mesh_details(sqft_per_piece, options_for_type)
            fc2.text_input("Finishing Option", value=dynamic_option_name, key=f"fin_opt_{entry['id']}", disabled=True)
        else:
            if list(options_for_type.keys()):
                selected_option = fc2.selectbox("Finishing Option", options=list(options_for_type.keys()), key=f"fin_opt_{entry['id']}")
                entry['finishing_option'] = selected_option
                finishing_price_per_unit = options_for_type.get(selected_option, 0)
            else:
                fc2.text_input("Finishing Option", value="N/A", key=f"fin_opt_{entry['id']}", disabled=True)
        fc3.metric(label="Finishing Cost/Unit", value=f"${finishing_price_per_unit:.2f}")

        cc1, cc2, _ = st.columns(3)
        with cc1:
            def format_cut_option(option_name):
                price = CUT_COST_MAP.get(option_name, 0)
                return f"{option_name} - ${price:.2f}"

            selected_cut_cost_desc = st.selectbox(
                "Cut Option", 
                options=CUT_COST_OPTIONS, 
                key=f"cut_cost_{entry['id']}",
                format_func=format_cut_option  # Add this line
            )
            entry['cut_cost_selection'] = selected_cut_cost_desc
            cut_cost_per_unit = CUT_COST_MAP.get(selected_cut_cost_desc, 0)
        with cc2:
            def format_time_option(option_name):
                price = ADDITIONAL_TIME_MAP.get(option_name, 0)
                return f"{option_name} - ${price:.2f}"

            default_at_index = 0
            if entry.get('additional_time_selection') in ADDITIONAL_TIME_OPTIONS:
                default_at_index = ADDITIONAL_TIME_OPTIONS.index(entry['additional_time_selection'])

            selected_at_desc = st.selectbox(
                "Additional Time",
                options=ADDITIONAL_TIME_OPTIONS,
                index=default_at_index,
                key=f"add_time_{entry['id']}",
                format_func=format_time_option
            )
            entry['additional_time_selection'] = selected_at_desc
            additional_time_cost_per_unit = ADDITIONAL_TIME_MAP.get(selected_at_desc, 0)
                

        # at1, at2, _ = st.columns(3)
        # with at1:
        #     def format_time_option(option_name):
        #         price = ADDITIONAL_TIME_MAP.get(option_name, 0)
        #         return f"{option_name} - ${price:.2f}"

        #     default_at_index = 0
        #     if entry.get('additional_time_selection') in ADDITIONAL_TIME_OPTIONS:
        #         default_at_index = ADDITIONAL_TIME_OPTIONS.index(entry['additional_time_selection'])

        #     selected_at_desc = st.selectbox(
        #         "Additional Time",
        #         options=ADDITIONAL_TIME_OPTIONS,
        #         index=default_at_index,
        #         key=f"add_time_{entry['id']}",
        #         format_func=format_time_option
        #     )
        #     entry['additional_time_selection'] = selected_at_desc
        #     additional_time_cost_per_unit = ADDITIONAL_TIME_MAP.get(selected_at_desc, 0)
        # with at2:
        #     st.metric(label="Additional Time Cost/Unit", value=f"${additional_time_cost_per_unit:.2f}")

        ai1, ai2 = st.columns(2)
        with ai1:
            def format_install_option(option_name):
                price = ADDED_INSTALL_MAP.get(option_name, 0)
                return f"{option_name} - ${price:.2f}"

            default_ai_index = 0
            if entry.get('added_install_selection') in ADDED_INSTALL_OPTIONS:
                default_ai_index = ADDED_INSTALL_OPTIONS.index(entry['added_install_selection'])
                
            selected_ai_desc = st.selectbox(
                "Added Install/Item Per Piece",
                options=ADDED_INSTALL_OPTIONS,
                index=default_ai_index,
                key=f"added_install_{entry['id']}",
                format_func=format_install_option
            )
            entry['added_install_selection'] = selected_ai_desc
            added_install_cost_per_unit = ADDED_INSTALL_MAP.get(selected_ai_desc, 0)
        with ai2:
            #st.metric(label="Added Install Cost/Unit", value=f"${added_install_cost_per_unit:.2f}")
            def format_adjustment_option(name):
                value = PRINT_ADJUSTMENT_FIXED[name]
                return f"{name} ({value:+.2%})"

            options = list(PRINT_ADJUSTMENT_FIXED.keys())
            default_adj = entry.get('print_adjustment', options[0])
            adj_index = options.index(default_adj) if default_adj in options else 0

            selected_adjustment_label = st.selectbox(
                "Select Adjustment",
                options=options,
                index=adj_index,
                format_func=format_adjustment_option,
                key=f"adjustment_{entry['id']}"
            )
            entry['print_adjustment'] = selected_adjustment_label
            adjustment_percentage = PRINT_ADJUSTMENT_FIXED[selected_adjustment_label]

        export_data = { "Type": entry.get('type'), "Material": entry.get('material'), "Num of pieces": entry.get('qty'), "Width (in)": total_width_inches, "Height (in)": total_height_inches, "SQ' per piece": f"{sqft_per_piece:.2f}", "Total SQ'": f"{total_sqft_entry:.2f}"}

        calculation_data = {
            "qty": entry.get('qty', 1), "sqft_per_piece": sqft_per_piece, "total_sqft_entry": total_sqft_entry,
            "sides_cost_per_unit": sides_cost_per_unit, "finishing_price_per_unit": finishing_price_per_unit,
            "cut_cost_per_unit": cut_cost_per_unit, "additional_time_cost_per_unit": additional_time_cost_per_unit,
            "added_install_cost_per_unit": added_install_cost_per_unit,
        }


        # --- ADDED: Per-entry Print Adjustment ---
        # st.markdown("##### Print Adjustment")
        # adj_col1, adj_col2 = st.columns([1, 2])
        # with adj_col1:
        #     def format_adjustment_option(name):
        #         value = PRINT_ADJUSTMENT_FIXED[name]
        #         return f"{name} ({value:+.2%})"

        #     options = list(PRINT_ADJUSTMENT_FIXED.keys())
        #     default_adj = entry.get('print_adjustment', options[0])
        #     adj_index = options.index(default_adj) if default_adj in options else 0

        #     selected_adjustment_label = st.selectbox(
        #         "Select Adjustment",
        #         options=options,
        #         index=adj_index,
        #         format_func=format_adjustment_option,
        #         key=f"adjustment_{entry['id']}"
        #     )
        #     entry['print_adjustment'] = selected_adjustment_label
        #     adjustment_percentage = PRINT_ADJUSTMENT_FIXED[selected_adjustment_label]

        # with adj_col2:
        # st.markdown("##### Volume Discount")
        discount_col1, discount_col2 = st.columns([1, 2])
        with discount_col1:
            discount_tier_options = {desc: discounts for _, (desc, discounts) in sorted(VOLUME_DISCOUNT_TIERS.items())}
            options_list = list(discount_tier_options.keys())

            # Define the function to format the display text
            def format_discount_tier(description):
                discounts = discount_tier_options.get(description, [0, 0, 0])
                p_disc, c_disc, w_disc = discounts[0], discounts[1], discounts[2]
                return f"{description} (P:{p_disc:.1%} | C:{c_disc:.1%} | W:{w_disc:.1%})"

            auto_selected_tier = get_discount_tier_details(total_sqft_order, VOLUME_DISCOUNT_TIERS)
            try:
                default_index = options_list.index(auto_selected_tier)
            except ValueError:
                default_index = 0
            
            selected_tier_description = st.selectbox(
                "Discount Tier", 
                options=options_list, 
                index=default_index, 
                key=f"discount_tier_{entry['id']}",
                format_func=format_discount_tier # This formats the display
            )
            selected_tier_discounts = discount_tier_options[selected_tier_description]

        # --- END Per-entry Print Adjustment ---

        # with discount_col2:
        #     st.write("")
        #     st.write("")
        #     st.info(f"""Discounts Applied:\n- **Preferred:** `{selected_tier_discounts[0]:.2%}`\n- **Corporate:** `{selected_tier_discounts[1]:.2%}`\n- **Wholesale:** `{selected_tier_discounts[2]:.2%}`""")
        # st.markdown("---")

        prodcuts_an_vars = material_data.get("prodcuts_an_vars")
        if prodcuts_an_vars:
            _, prodcuts_an_for_entry = calculate_dynamic_prodcuts_an(prodcuts_an_vars, entry.get('qty', 1))
        else:
            prodcuts_an_for_entry = default_prodcuts_an

        entry_prices = calculate_all_prices_for_entry(
            calculation_data, all_material_prices, selected_tier_discounts,
            adjustment_percentage, multiples_value, prodcuts_an_for_entry
        )
        
        # Display the per-entry multiplier
        st.metric(label=f"Material Multiplier ({multiples_label})", value=f"x{multiples_value}")

        preferred_label = f"Preferred ({selected_tier_discounts[0]:.2%})"
        corporate_label = f"Corporate ({selected_tier_discounts[1]:.2%})"
        wholesale_label = f"Wholesale ({selected_tier_discounts[2]:.2%})"

        p_col, c_col, w_col = st.columns(3)
        with p_col:
            st.metric(label=preferred_label, value=f"${entry_prices.get('Preferred', 0):,.2f}")
        with c_col:
            st.metric(label=corporate_label, value=f"${entry_prices.get('Corporate', 0):,.2f}")
        with w_col:
            st.metric(label=wholesale_label, value=f"${entry_prices.get('Wholesale', 0):,.2f}")

        return "ok", export_data

# --- Initialize session state ---
if 'entries' not in st.session_state:
    st.session_state.entries = []
    if MATERIALS.get("Banner") and list(MATERIALS["Banner"].keys()):
        st.session_state.entries.append({
            "id": str(uuid.uuid4()),"type": "Banner", "material": list(MATERIALS["Banner"].keys())[0],
            "w_ft": 0,"w_in": 0,"h_ft": 0,"h_in": 0,"qty": 1,
            "sidedness": "Single Sided", "finishing_type": "Nothing Special", "cut_cost_selection": "NO CUT",
            "additional_time_selection": ADDITIONAL_TIME_OPTIONS[0] if ADDITIONAL_TIME_OPTIONS else None,
            "added_install_selection": ADDED_INSTALL_OPTIONS[0] if ADDED_INSTALL_OPTIONS else None,
            "print_adjustment": list(PRINT_ADJUSTMENT_FIXED.keys())[0] if PRINT_ADJUSTMENT_FIXED else None
        })
if 'total_sqft_order' not in st.session_state:
    trigger_recalculation()

st.sidebar.header("Entries")
# st.sidebar.divider()

# --- Main App Logic ---
data_for_export, all_entry_totals = [], []
remove_entry_index = None
if not st.session_state.entries: st.warning("No quote entries yet. Click below to add one.")

# This check ensures that if a callback has updated the state, we rerun immediately
# to show the user the latest, correct information.
current_total_sqft = sum((((e.get('w_ft', 0) * 12 + e.get('w_in', 0)) * (e.get('h_ft', 0) * 12 + e.get('h_in', 0))) / 144) * e.get('qty', 1) for e in st.session_state.entries)
if st.session_state.get('total_sqft_order', -1) != current_total_sqft:
    trigger_recalculation()
    st.rerun()

# Count occurrences of each material type
material_type_counts = Counter(e.get('material') for e in st.session_state.entries)
total_sqft_order = st.session_state.get('total_sqft_order', 0)

for i, entry in enumerate(st.session_state.entries):
    # Get the count for the current entry's material
    material_count = material_type_counts.get(entry.get('material'), 1)
    
    # Find the specific multiplier and its label for this entry
    multiples_label, multiples_value = get_multiplier(material_count)

    ### MODIFIED: Check if the current entry is the last one in the list
    is_last_entry = (i == len(st.session_state.entries) - 1)

    ### MODIFIED: Pass the is_last_entry flag to the rendering function
    status, export_data = render_expanded_layout(
        entry, i, total_sqft_order, multiples_value, multiples_label, is_last_entry
    )
    if status == "remove_entry": remove_entry_index = i
    else:
        if export_data: data_for_export.append(export_data)

if remove_entry_index is not None:
    st.session_state.entries.pop(remove_entry_index)
    trigger_recalculation()
    st.rerun()

st.divider()
if st.button("➕ Add New Entry", use_container_width=True):
    if MATERIALS.get("Banner") and list(MATERIALS["Banner"].keys()):
        st.session_state.entries.append({
            "id": str(uuid.uuid4()), "type": "Banner", "material": list(MATERIALS["Banner"].keys())[0],
            "w_ft": 0, "w_in": 0, "h_ft": 0, "h_in": 0, "qty": 1,
            "sidedness": "Single Sided", "finishing_type": "Nothing Special", "cut_cost_selection": "NO CUT",
            "additional_time_selection": ADDITIONAL_TIME_OPTIONS[0] if ADDITIONAL_TIME_OPTIONS else None,
            "added_install_selection": ADDED_INSTALL_OPTIONS[0] if ADDED_INSTALL_OPTIONS else None,
            "print_adjustment": list(PRINT_ADJUSTMENT_FIXED.keys())[0] if PRINT_ADJUSTMENT_FIXED else None
        })
        trigger_recalculation()
        st.rerun()

# --- SIDEBAR FINAL DISPLAY ---
with st.sidebar.expander("Go to Entry...", expanded=True):
    for i, entry in enumerate(st.session_state.entries):
        # Get the full material name
        full_material_name = entry.get('material', 'N/A')

        # Truncate the name if it's longer than 20 characters
        material = (full_material_name[:10] + '...') if len(full_material_name) > 20 else full_material_name
        
        # Create the summary text with the (potentially truncated) name
        summary_text = f"**{material}**: {entry.get('w_ft', 0)}' {entry.get('w_in', 0)}\" x {entry.get('h_ft', 0)}' {entry.get('h_in', 0)}\" (Qty: {entry.get('qty', 1)})"
        st.markdown(f"[{summary_text}](#entry-{entry['id']})", unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.metric(label="TOTAL SQ' IN ORDER", value=f"{st.session_state.total_sqft_order:.2f}")
st.sidebar.divider()