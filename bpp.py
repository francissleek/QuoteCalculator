import streamlit as st
import uuid
import pandas as pd
import json
import math

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Universal Quote Calculator")
st.title("Universal Quote Calculator")

# --- CONFIGURATION LOADER ---
def load_config(file_path='config.json'):
    try:
        if "config" in st.secrets:
            return json.loads(st.secrets["config"])
    except (st.errors.StreamlitAPIException, KeyError, json.JSONDecodeError):
        pass
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"FATAL: Configuration could not be loaded. Ensure 'config.json' exists.")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"FATAL: Error decoding '{file_path}'. Please ensure it is valid JSON. Error: {e}")
        st.stop()

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
    
    # This default is now a fallback
    default_prodcuts_an = cost_config.get("prodcuts_an", 16.21)
    return calculated_bx4, calculated_bx6, default_prodcuts_an

ADDITIONAL_COSTS_CONFIG = config.get('ADDITIONAL_COSTS', {})
cons_bx_4, cons_bx_6, default_prodcuts_an = calculate_additional_costs(ADDITIONAL_COSTS_CONFIG)

# --- NEW: DYNAMIC PRODCUTS_AN CALCULATION ---
def calculate_dynamic_prodcuts_an(vars, Q_Quantity):
    """Calculates the dynamic 'prodcuts_an' value based on material-specific variables."""
    if not vars or Q_Quantity == 0:
        return 0, 0

    # Unpack variables with defaults
    AW_Roll_Costs = vars.get("AW_Roll_Costs", 0)
    AU_Material_Length = vars.get("AU_Material_Length", 1) # Avoid division by zero
    AV_Material_Width = vars.get("AV_Material_Width", 1) # Avoid division by zero
    AQ_SQ = vars.get("AQ_SQ", 0)
    AS_Laminate_Loading = vars.get("AS_Laminate_Loading", 0)
    AT_Labour = vars.get("AT_Labour", 0)
    constant_BY8 = vars.get("constant_BY8", 0)
    Per_hour_rate = vars.get("Per_hour_rate", 0)

    # AX_Sq_material = AW/((AU*AV)/144)
    denominator_ax = (AU_Material_Length * AV_Material_Width) / 144
    AX_Sq_material = AW_Roll_Costs / denominator_ax if denominator_ax != 0 else 0

    # 'Form Responses 1'!$BX$8 = (constant_BY8/60) * Per_hour_rate
    form_response_bx8 = (constant_BY8 / 60) * Per_hour_rate

    # AO = (AX_Sq_material*AQ) + AS + AT
    AO = (AX_Sq_material * AQ_SQ) + AS_Laminate_Loading + AT_Labour
    
    # AN = (AO+('Form Responses 1'!$BX$8/Q)+AS,"")
    AN = AO + (form_response_bx8 / Q_Quantity) + AS_Laminate_Loading

    return AO, AN

# --- Helper functions ---
def excel_floor(number, significance):
    if significance == 0: return 0
    return math.floor(number / significance) * significance

def excel_ceiling(number, significance):
    if significance == 0: return 0
    return math.ceil(number / significance) * significance

def calculate_material_price(material_data):
    results = {'preferred_base': 0, 'preferred_value': 0, 'corporate_base': 0, 'corporate_value': 0, 'wholesale_base': 0, 'wholesale_value': 0}
    try:
        p_vars = material_data['Preferred']
        p_variable_1, p_variable_2, p_discount_value = p_vars.get('p_variable_1', 0), p_vars.get('p_variable_2', 0), p_vars.get('p_discount_value', 0)
        preferred_base = excel_floor(p_variable_1 * p_variable_2, FALL_BACK_VALUE)
        results['preferred_base'] = preferred_base
        results['preferred_value'] = preferred_base * (1 - p_discount_value)

        c_vars = material_data['Corporate']
        c_variable_1, c_discount_value = c_vars.get('c_variable_1', 0), c_vars.get('c_discount_value', 0)
        corporate_base = excel_ceiling(preferred_base * c_variable_1, FALL_BACK_VALUE)
        results['corporate_base'] = corporate_base
        results['corporate_value'] = corporate_base * (1 - c_discount_value)

        w_vars = material_data['Wholesale']
        w_variable_1, w_discount_value = w_vars.get('w_variable_1', 0), w_vars.get('w_discount_value', 0)
        wholesale_base = excel_ceiling(preferred_base * w_variable_1, FALL_BACK_VALUE)
        results['wholesale_base'] = wholesale_base
        results['wholesale_value'] = wholesale_base * (1 - w_discount_value)
    except (KeyError, TypeError): pass
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
            return f"{desc_prefix} - {option_name}", price
    return "N/A", 0.0

# --- REFACTORED PRICE CALCULATION LOGIC ---

def perform_price_calculation(calc_data, customer_type, active_base_amount, discount_percentage, adjustment_percentage, multiples_value, prodcuts_an):
    """Performs the core price calculation for a given customer type and its specific inputs."""
    entry_quantity = calc_data.get('qty', 1)
    if entry_quantity == 0:
        return 0

    # For entry-level calculations, a stable multiples value of 1 is used.
    multiples_value_for_entry = 1

    # Part A: Material Cost
    part_a_base = active_base_amount * calc_data['sqft_per_piece'] * calc_data['sides_cost_per_unit']
    part_a_discounted = part_a_base * (1 - (discount_percentage + adjustment_percentage))

    # Part B: Cut Cost
    part_b_original = calc_data['cut_cost_per_unit'] * calc_data['sqft_per_piece']
    part_b = part_b_original + part_a_discounted

    # Part C: Finishing Cost
    part_c_numerator = (calc_data['finishing_price_per_unit'] * calc_data['sqft_per_piece'] * entry_quantity) + (prodcuts_an / multiples_value_for_entry)
    part_c = part_c_numerator / entry_quantity

    # Part D: Fixed Cut Cost
    if calc_data['cut_cost_per_unit'] == 0.0:
        part_d = 0
    elif customer_type == 'Preferred':
        part_d = (cons_bx_4 / multiples_value_for_entry) / entry_quantity
    else:  # Corporate and Wholesale
        part_d = (cons_bx_4 / multiples_value_for_entry + 0.5) / entry_quantity

    # Part E: Fixed Finishing Cost
    if calc_data['finishing_price_per_unit'] == 0:
        part_e = 0
    else:
        part_e = (cons_bx_6 / multiples_value_for_entry) / entry_quantity

    # Part F: Time and Install Costs
    part_f = (calc_data['additional_time_cost_per_unit'] / entry_quantity) + calc_data['added_install_cost_per_unit']

    # Combine all parts for the price of a single piece
    price_per_single_piece = part_b + part_c + part_d + part_e + part_f
    
    # Apply final markup to get the final price per piece
    final_price_per_piece = price_per_single_piece * 1.1

    return final_price_per_piece

def calculate_all_prices_for_entry(calculation_data, all_material_prices, all_discount_percentages, adjustment_percentage, multiples_value, prodcuts_an_for_entry):
    """Calculates the Preferred, Corporate, and Wholesale prices for a single entry."""
    all_prices = {}
    
    # Map customer types to their specific data for iteration
    customer_types_map = {
        'Preferred': {
            'base': all_material_prices.get('preferred_base', 0),
            'discount': all_discount_percentages[0]  # Index 0 for Preferred
        },
        'Corporate': {
            'base': all_material_prices.get('corporate_base', 0),
            'discount': all_discount_percentages[1]  # Index 1 for Corporate
        },
        'Wholesale': {
            'base': all_material_prices.get('wholesale_base', 0),
            'discount': all_discount_percentages[2]  # Index 2 for Wholesale
        }
    }

    for cust_type, data in customer_types_map.items():
        price = perform_price_calculation(
            calc_data=calculation_data,
            customer_type=cust_type,
            active_base_amount=data['base'],
            discount_percentage=data['discount'],
            adjustment_percentage=adjustment_percentage,
            multiples_value=multiples_value,
            prodcuts_an=prodcuts_an_for_entry
        )
        all_prices[cust_type] = price

    return all_prices

# --- Layout Rendering Function ---
def render_expanded_layout(entry, i, customer_type, all_tier_discounts, adjustment_percentage, multiples_value):
    with st.container(border=True):
        st.markdown(f"<a name='entry-{entry['id']}'></a>", unsafe_allow_html=True)
        
        type_col, material_col, remove_col = st.columns([2, 3, 1])
        with type_col: entry['type'] = st.selectbox("Type", list(MATERIALS.keys()), key=f"type_{entry['id']}")
        with material_col:
            material_options = list(MATERIALS.get(entry['type'], {}).keys())
            if material_options:
                if entry.get('material') not in material_options: entry['material'] = material_options[0]
                entry['material'] = st.selectbox("Material", material_options, key=f"material_{entry['id']}")
            else:
                st.warning(f"No materials for type '{entry['type']}'"); entry['material'] = None
        with remove_col:
            st.write(""); st.write("")
            if st.button("❌", key=f"remove_{entry['id']}", help="Remove this entry"):
                return "remove_entry", None, None

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

        total_width_inches = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
        total_height_inches = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
        sqft_per_piece = (total_width_inches * total_height_inches) / 144
        total_sqft_entry = sqft_per_piece * entry.get('qty', 1)

        base_price_per_sqft, active_base_amount = 0, 0
        material_data = {}
        all_material_prices = {}
        if entry.get('material'):
            material_data = MATERIALS.get(entry['type'], {}).get(entry['material'], {})
            if material_data:
                all_material_prices = calculate_material_price(material_data)
                price_map = {'Preferred': 'preferred_value', 'Corporate': 'corporate_value', 'Wholesale': 'wholesale_value'}
                base_map = {'Preferred': 'preferred_base', 'Corporate': 'corporate_base', 'Wholesale': 'wholesale_base'}
                active_base_amount = all_material_prices.get(base_map.get(customer_type, 'preferred_base'), 0)
                base_price_per_sqft = all_material_prices.get(price_map.get(customer_type, 'preferred_value'), 0)

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric(label="SQ'/piece", value=f"{sqft_per_piece:.2f}")
        metric_col2.metric(label="Total SQ'", value=f"{total_sqft_entry:.2f}")
        metric_col3.metric(label=f"Applied Price/SQ' ({customer_type})", value=f"${base_price_per_sqft:.2f}")
        
        st.markdown("---")
        price_col1, price_col2 = st.columns(2)
        price_col1.metric(label="BASE AMOUNT", value=f"${active_base_amount:.2f}")
        price_col2.metric(label="MAX DISCOUNT", value=f"${base_price_per_sqft:.2f}")
        st.divider()

        sc1, sc2, sc3 = st.columns([1, 2, 3])
        sidedness_index = SIDEDNESS_OPTIONS.index(entry.get('sidedness', SIDEDNESS_OPTIONS[0]))
        entry['sidedness'] = sc1.selectbox("Sidedness", options=SIDEDNESS_OPTIONS, key=f"side_{entry['id']}", index=sidedness_index)
        suggested_tier = get_suggested_sides_tier(sqft_per_piece, entry['sidedness'])
        try: tier_index = TIER_DESCRIPTIONS.index(suggested_tier)
        except ValueError: tier_index = 0
        def format_tier_option(name): return f"{name} - ${SIDES_TIERS_MAP.get(name, 0):.2f}"
        selected_tier_desc = sc2.selectbox("Tier", options=TIER_DESCRIPTIONS, index=tier_index, key=f"sides_tier_{entry['id']}", format_func=format_tier_option)
        entry['sides_tier_selection'] = selected_tier_desc
        sides_cost_per_unit = SIDES_TIERS_MAP.get(selected_tier_desc, 0)
        sc3.metric(label="Sides Cost/Unit", value=f"${sides_cost_per_unit:.2f}")
        
        fc1, fc2, fc3 = st.columns(3)
        if entry.get('finishing_type') is None: entry['finishing_type'] = 'Nothing Special'
        if entry['type'] == "Banner" and entry.get('finishing_type') == 'Nothing Special': entry['finishing_type'] = "Banner/Mesh"
        try: finishing_type_index = FINISHING_TYPES.index(entry.get('finishing_type'))
        except ValueError: finishing_type_index = 0
        selected_type = fc1.selectbox("Finishing Type", options=FINISHING_TYPES, key=f"fin_type_{entry['id']}", index=finishing_type_index)
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

        cc1, cc2, _ = st.columns(3) # Third column for spacing
        with cc1:
            selected_cut_cost_desc = st.selectbox("Cut Option", options=CUT_COST_OPTIONS, key=f"cut_cost_{entry['id']}")
            entry['cut_cost_selection'] = selected_cut_cost_desc
            cut_cost_per_unit = CUT_COST_MAP.get(selected_cut_cost_desc, 0)
        with cc2:
            st.metric(label="Cut Cost/Unit", value=f"${cut_cost_per_unit:.2f}")

        at1, at2, _ = st.columns(3) # Third column for spacing
        with at1:
            default_at_index = 0
            if entry.get('additional_time_selection') in ADDITIONAL_TIME_OPTIONS: default_at_index = ADDITIONAL_TIME_OPTIONS.index(entry['additional_time_selection'])
            selected_at_desc = st.selectbox("Additional Time", options=ADDITIONAL_TIME_OPTIONS, key=f"add_time_{entry['id']}", index=default_at_index)
            entry['additional_time_selection'] = selected_at_desc
            additional_time_cost_per_unit = ADDITIONAL_TIME_MAP.get(selected_at_desc, 0)
        with at2:
            st.metric(label="Additional Time Cost/Unit", value=f"${additional_time_cost_per_unit:.2f}")

        ai1, ai2, total_col = st.columns(3) # Third column for the total
        with ai1:
            default_ai_index = 0
            if entry.get('added_install_selection') in ADDED_INSTALL_OPTIONS: default_ai_index = ADDED_INSTALL_OPTIONS.index(entry['added_install_selection'])
            selected_ai_desc = st.selectbox("Added Install/Item Per Piece", options=ADDED_INSTALL_OPTIONS, key=f"added_install_{entry['id']}", index=default_ai_index)
            entry['added_install_selection'] = selected_ai_desc
            added_install_cost_per_unit = ADDED_INSTALL_MAP.get(selected_ai_desc, 0)
        with ai2:
            st.metric(label="Added Install Cost/Unit", value=f"${added_install_cost_per_unit:.2f}")
    
    export_data = { "Type": entry.get('type'), "Material": entry.get('material'), "Num of pieces": entry.get('qty'), "Width (in)": total_width_inches, "Height (in)": total_height_inches, "SQ' per piece": f"{sqft_per_piece:.2f}", "Total SQ'": f"{total_sqft_entry:.2f}"}
    
    calculation_data = {
        "qty": entry.get('qty', 1), "sqft_per_piece": sqft_per_piece, "total_sqft_entry": total_sqft_entry,
        "sides_cost_per_unit": sides_cost_per_unit, "finishing_price_per_unit": finishing_price_per_unit,
        "cut_cost_per_unit": cut_cost_per_unit, "additional_time_cost_per_unit": additional_time_cost_per_unit,
        "added_install_cost_per_unit": added_install_cost_per_unit,
    }

    # --- Calculate prodcuts_an for this specific entry ---
    prodcuts_an_vars = material_data.get("prodcuts_an_vars")
    if prodcuts_an_vars:
        _, prodcuts_an_for_entry = calculate_dynamic_prodcuts_an(prodcuts_an_vars, entry.get('qty', 1))
    else:
        prodcuts_an_for_entry = default_prodcuts_an

    # --- Calculate and display all prices for this entry ---
    entry_prices = calculate_all_prices_for_entry(
        calculation_data, all_material_prices, all_tier_discounts, 
        adjustment_percentage, multiples_value, prodcuts_an_for_entry
    )
    
    with total_col:
        # Create a horizontal layout for the prices
        p_col, c_col, w_col = st.columns(3)
        with p_col:
            st.metric(label="Preferred", value=f"${entry_prices.get('Preferred', 0):,.2f}")
        with c_col:
            st.metric(label="Corporate", value=f"${entry_prices.get('Corporate', 0):,.2f}")
        with w_col:
            st.metric(label="Wholesale", value=f"${entry_prices.get('Wholesale', 0):,.2f}")

    # Return the total for the currently selected customer type for any summary calculations
    selected_entry_total = entry_prices.get(customer_type, 0)
    
    return "ok", export_data, selected_entry_total

# --- Initialize session state ---
if 'entries' not in st.session_state:
    st.session_state.entries = []
    if MATERIALS.get("Banner") and list(MATERIALS["Banner"].keys()):
        st.session_state.entries.append({
            "id": str(uuid.uuid4()),"type": "Banner", "material": list(MATERIALS["Banner"].keys())[0], 
            "w_ft": 0,"w_in": 0,"h_ft": 0,"h_in": 0,"qty": 1, 
            "sidedness": "Single Sided", "finishing_type": "Nothing Special", "cut_cost_selection": "NO CUT",
            "additional_time_selection": ADDITIONAL_TIME_OPTIONS[0] if ADDITIONAL_TIME_OPTIONS else None,
            "added_install_selection": ADDED_INSTALL_OPTIONS[0] if ADDED_INSTALL_OPTIONS else None
        })

# --- SIDEBAR (Gets customer type first) ---
st.sidebar.header("Quote Summary")
if not CUSTOMER_TYPES: st.sidebar.error("Customer types not defined."); st.stop()
customer_type_index = CUSTOMER_TYPES.index(st.sidebar.selectbox("Select Customer Type", options=CUSTOMER_TYPES))
selected_customer_type = CUSTOMER_TYPES[customer_type_index]

# --- Pre-calculate global values ---
total_sqft_order = sum(
    (((e.get('w_ft', 0) * 12 + e.get('w_in', 0)) * (e.get('h_ft', 0) * 12 + e.get('h_in', 0))) / 144) * e.get('qty', 1)
    for e in st.session_state.entries
)
num_entries = len(st.session_state.entries)
_, multiples_value = get_multiplier(num_entries)

# --- Sidebar Discount and Adjustment Controls ---
st.sidebar.markdown("#### SQ' Discount")
selected_percentage = 0
selected_tier_discounts = [0, 0, 0]  # Default to no discount for [Pref, Corp, Whole]
if VOLUME_DISCOUNT_TIERS:
    discount_tier_options = {desc: discounts for _, (desc, discounts) in sorted(VOLUME_DISCOUNT_TIERS.items())}
    options_list = list(discount_tier_options.keys())
    auto_selected_tier = get_discount_tier_details(total_sqft_order, VOLUME_DISCOUNT_TIERS)
    try: default_index = options_list.index(auto_selected_tier)
    except ValueError: default_index = 0
    def format_discount_option(desc): return f"{desc} ({discount_tier_options[desc][0]:.2%}/{discount_tier_options[desc][1]:.2%}/{discount_tier_options[desc][2]:.2%})"
    selected_tier_description = st.sidebar.selectbox("Discount Tier", options=options_list, index=default_index, format_func=format_discount_option)
    
    selected_tier_discounts = discount_tier_options[selected_tier_description]
    selected_percentage = selected_tier_discounts[customer_type_index] # For display purposes
    
    st.sidebar.info(f"Applying **{selected_percentage:.2%}** discount for **{selected_customer_type}**.")

st.sidebar.markdown("#### Print Adjustment")
adjustment_percentage = 0
if PRINT_ADJUSTMENT_FIXED:
    selected_adjustment_label = st.sidebar.selectbox("Select Adjustment", options=list(PRINT_ADJUSTMENT_FIXED.keys()))
    adjustment_percentage = PRINT_ADJUSTMENT_FIXED[selected_adjustment_label]

# --- Main App Logic ---
data_for_export, all_entry_totals = [], []
remove_entry_index = None

if not st.session_state.entries: st.warning("No quote entries yet. Click below to add one.")

for i, entry in enumerate(st.session_state.entries):
    status, export_data, entry_total = render_expanded_layout(
        entry, i, selected_customer_type, selected_tier_discounts, 
        adjustment_percentage, multiples_value
    )
    if status == "remove_entry": remove_entry_index = i
    else:
        if export_data: data_for_export.append(export_data)
        if entry_total is not None: all_entry_totals.append(entry_total)

if remove_entry_index is not None:
    st.session_state.entries.pop(remove_entry_index)
    st.rerun()

st.divider()
if st.button("➕ Add New Entry", use_container_width=True):
    if MATERIALS.get("Banner") and list(MATERIALS["Banner"].keys()):
        st.session_state.entries.append({
            "id": str(uuid.uuid4()), "type": "Banner", "material": list(MATERIALS["Banner"].keys())[0],
            "w_ft": 0, "w_in": 0, "h_ft": 0, "h_in": 0, "qty": 1, 
            "sidedness": "Single Sided", "finishing_type": "Nothing Special", "cut_cost_selection": "NO CUT",
            "additional_time_selection": ADDITIONAL_TIME_OPTIONS[0] if ADDITIONAL_TIME_OPTIONS else None,
            "added_install_selection": ADDED_INSTALL_OPTIONS[0] if ADDED_INSTALL_OPTIONS else None
        })
        st.rerun()

# --- SIDEBAR FINAL DISPLAY ---
with st.sidebar.expander("Go to Entry...", expanded=True):
    for i, entry in enumerate(st.session_state.entries):
        material = entry.get('material', 'N/A')
        summary_text = f"**{material}**: {entry.get('w_ft', 0)}' {entry.get('w_in', 0)}\" x {entry.get('h_ft', 0)}' {entry.get('h_in', 0)}\" (Qty: {entry.get('qty', 1)})"
        st.markdown(f"[{summary_text}](#entry-{entry['id']})", unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.metric(label="TOTAL SQ' IN ORDER", value=f"{total_sqft_order:.2f}")
st.sidebar.divider()
st.sidebar.metric(label=f"Multiplier ({get_multiplier(num_entries)[0]})", value=f"x{multiples_value}")

# Note: The ORDER TOTAL is not currently displayed as `all_entry_totals` was not used.
# To show an order total for the selected customer, you could add:
#
# total_order_price = sum(price * data['Num of pieces'] for price, data in zip(all_entry_totals, data_for_export))
# st.sidebar.metric(label=f"ORDER TOTAL ({selected_customer_type})", value=f"${total_order_price:,.2f}")