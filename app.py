# FILE: app.py
# UPDATED: Combined 'compact' and 'expanded' layouts with a user-selectable option in the sidebar.

import streamlit as st
import uuid
import pandas as pd
import json

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Universal Quote Calculator")
st.title("Universal Quote Calculator")

def load_config(file_path='config.json'):
    if hasattr(st, 'secrets') and 'config' in st.secrets:
        config_data = st.secrets['config']
    if isinstance(config_data, str):  # If TOML loads it as a string
        config_data = json.loads(config_data)
    else:
        with open(file_path, 'r') as f:
            config_data = json.load(f)
        # JSON loads dictionary keys as strings, so we must convert keys back to integers for tiers
        config_data['VOLUME_DISCOUNT_TIERS'] = {int(k): v for k, v in config_data['VOLUME_DISCOUNT_TIERS'].items()}
        config_data['PRINT_ADJUSTMENT_COMMODITY'] = {int(k): v for k, v in config_data['PRINT_ADJUSTMENT_COMMODITY'].items()}
        config_data['MULTIPLES_MAP'] = {int(k): v for k, v in config_data['MULTIPLES_MAP'].items()}
    return config_data

config = load_config()

# --- Unpack loaded data into variables the app expects ---
SIDES_TIERS_MAP = config['SIDES_TIERS_MAP']
SIDEDNESS_OPTIONS = config['SIDEDNESS_OPTIONS']
SPECIALTY_FINISHING = config['SPECIALTY_FINISHING']
CUSTOMER_TYPES = config['CUSTOMER_TYPES']
CUSTOMER_BASE_PRICES = config['CUSTOMER_BASE_PRICES']
VOLUME_DISCOUNT_TIERS = config['VOLUME_DISCOUNT_TIERS']
PRINT_ADJUSTMENT_FIXED = config['PRINT_ADJUSTMENT_FIXED']
PRINT_ADJUSTMENT_COMMODITY = config['PRINT_ADJUSTMENT_COMMODITY']
CUT_COST_MAP = config['CUT_COST_MAP']
MULTIPLES_MAP = config['MULTIPLES_MAP']


# --- IMPORTANT: Re-create variables that were derived from the dictionaries ---
TIER_DESCRIPTIONS = list(SIDES_TIERS_MAP.keys())
FINISHING_TYPES = list(SPECIALTY_FINISHING.keys())
CUT_COST_OPTIONS = list(CUT_COST_MAP.keys())

# --- Helper Functions ---
def get_discount_tier_details(total_sqft):
    for min_sqft, (description, discounts) in VOLUME_DISCOUNT_TIERS.items():
        if total_sqft >= min_sqft: return description, discounts
    return "N/A", [0.0, 0.0, 0.0]

def get_print_adjustment_details(total_sqft):
    options = PRINT_ADJUSTMENT_FIXED.copy()
    commodity_tier_desc = None
    default_selection = "no adjustment"
    for min_sqft, (description, discount) in PRINT_ADJUSTMENT_COMMODITY.items():
        if total_sqft >= min_sqft:
            full_desc = f"Commodity discount ({description})"
            options[full_desc] = discount
            commodity_tier_desc = description
            default_selection = full_desc
            break
    return options, commodity_tier_desc, default_selection

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
        if sqft >= 0.1: return "SMALLER BETWEEN 0.25 - .1 sq' /peice"
        if sqft >= 0.05: return "SMALLER BETWEEN 0.1 - .05 sq' /peice"
        return "SMALLEST UNDER 0.05 sq' /peice"
    if sidedness == "Double Sided":
        if sqft >= 1.0: return "DOUBLE SIDED Over 1 SQ'"
        if sqft >= 0.5: return "DOUBLE SIDED between 1sq' - 0.5sq' per peice"
        if sqft >= 0.25: return "DOUBLE SIDED under 0.5 - .25 sq' /peice"
        if sqft >= 0.1: return "DOUBLE SIDED under 0.25 - .1 sq' /peice"
        if sqft >= 0.05: return "DOUBLE SIDED under 0.1 - .05 sq' /peice"
        return "DOUBLE SIDED under 0.05 sq' /peice"
    return TIER_DESCRIPTIONS[0]

def get_suggested_finishing_type(main_product_type, width_in, height_in):
    if main_product_type == "Banner": return "Banner/Mesh"
    max_dim = max(width_in, height_in)
    if max_dim > 3: return "Over 3\" object"
    if max_dim >= 1: return "3\" - 1\" OBJECT"
    if max_dim > 0: return "UNDER 1\""
    return "Nothing Special"

def get_banner_mesh_details(sqft, option_details):
    option_name = list(option_details.keys())[0]
    tier_list = option_details[option_name]
    for min_sqft, price, desc_prefix in tier_list:
        if sqft >= min_sqft:
            full_description = f"{desc_prefix} - {option_name}"
            return full_description, price
    return "N/A", 0.0

# --- NEW: Layout Rendering Functions ---
def render_compact_layout(entry, i):
    """Renders the compact, two-column layout from compact.py"""
    
    identifier_label = entry.get('identifier') if entry.get('identifier') else f"Entry {i + 1}"
    
    with st.expander(f"Details for: {identifier_label}", expanded=True):
        st.markdown(f"<a name='entry-{entry['id']}'></a>", unsafe_allow_html=True)
        
        left_col, right_col = st.columns(2, gap="large")

        # --- ALL INPUTS AND CONTROLS ARE IN THE LEFT COLUMN ---
        with left_col:
            row1_col1, row1_col2, row1_col3 = st.columns([2, 3, 1])
            with row1_col1:
                entry['type'] = st.selectbox("Type", ["Banner", "Decal", "Other"], key=f"type_{entry['id']}", index=0)
            with row1_col2:
                entry['identifier'] = st.text_input("Identifier", key=f"id_{entry['id']}", value=entry.get('identifier', ''))
            with row1_col3:
                st.write("") 
                st.write("") 
                if st.button("❌", key=f"remove_{entry['id']}", help="Remove this entry"):
                    return "remove_entry", None, None
            
            st.divider()
            
            st.markdown("##### Dimensions & Quantity")
            dim_col1, dim_col2, dim_col3 = st.columns(3)
            with dim_col1:
                entry['w_ft'] = st.number_input("Width (ft)", min_value=0, key=f"w_ft_{entry['id']}", value=entry.get('w_ft', 0))
                entry['w_in'] = st.number_input("Width (in)", min_value=0, key=f"w_in_{entry['id']}", value=entry.get('w_in', 0))
            with dim_col2:
                entry['h_ft'] = st.number_input("Height (ft)", min_value=0, key=f"h_ft_{entry['id']}", value=entry.get('h_ft', 0))
                entry['h_in'] = st.number_input("Height (in)", min_value=0, key=f"h_in_{entry['id']}", value=entry.get('h_in', 0))
            with dim_col3:
                entry['qty'] = st.number_input("Quantity", min_value=1, key=f"qty_{entry['id']}", value=entry.get('qty', 1))
            
            st.divider()

            st.markdown("##### Add-ons")
            
            sqft_per_piece = ((entry.get('w_ft', 0) * 12 + entry.get('w_in', 0)) * (entry.get('h_ft', 0) * 12 + entry.get('h_in', 0))) / 144
            
            side_col1, side_col2 = st.columns(2)
            with side_col1:
                sidedness_index = SIDEDNESS_OPTIONS.index(entry.get('sidedness', SIDEDNESS_OPTIONS[0]))
                entry['sidedness'] = st.selectbox("Sidedness", options=SIDEDNESS_OPTIONS, key=f"side_{entry['id']}", index=sidedness_index)
            with side_col2:
                suggested_tier = get_suggested_sides_tier(sqft_per_piece, entry['sidedness'])
                try: tier_index = TIER_DESCRIPTIONS.index(suggested_tier)
                except ValueError: tier_index = 0
                def format_tier_option(option_name): return f"{option_name} - ${SIDES_TIERS_MAP.get(option_name, 0):.2f}"
                selected_tier_desc = st.selectbox("Tier", options=TIER_DESCRIPTIONS, index=tier_index, key=f"sides_tier_{entry['id']}", format_func=format_tier_option)
                entry['sides_tier_selection'] = selected_tier_desc
            
            finish_col1, finish_col2 = st.columns(2)
            with finish_col1:
                # If type is 'Banner' and finishing is the default, suggest 'Banner/Mesh'
                if entry['type'] == "Banner" and entry.get('finishing_type') == 'Nothing Special':
                    entry['finishing_type'] = "Banner/Mesh"

                # Determine the index from the current entry state
                try:
                    finishing_type_index = FINISHING_TYPES.index(entry.get('finishing_type', 'Nothing Special'))
                except ValueError:
                    finishing_type_index = 0 # Default to first item if not found

                selected_type = st.selectbox("Finishing Type", options=FINISHING_TYPES, key=f"fin_type_{entry['id']}", index=finishing_type_index)
                entry['finishing_type'] = selected_type
            with finish_col2:
                options_for_type = SPECIALTY_FINISHING.get(selected_type, {})
                if selected_type == "Banner/Mesh":
                    st.text_input("Finishing Option", value=list(options_for_type.keys())[0], key=f"fin_opt_{entry['id']}", disabled=True)
                else:
                    selected_option = st.selectbox("Finishing Option", options=list(options_for_type.keys()), key=f"fin_opt_{entry['id']}", index=0)
                    entry['finishing_option'] = selected_option
            
            def format_cut_cost_option(option_name): return f"{option_name} - ${CUT_COST_MAP.get(option_name, 0):.2f}"
            selected_cut_cost_desc = st.selectbox("Cut Option", options=CUT_COST_OPTIONS, key=f"cut_cost_{entry['id']}", index=0, format_func=format_cut_cost_option)
            entry['cut_cost_selection'] = selected_cut_cost_desc

        # --- ALL CALCULATIONS AND DISPLAY HAPPEN IN THE RIGHT COLUMN ---
        with right_col:
            st.markdown("#### Entry Summary")
            
            total_width_inches = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
            total_height_inches = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
            sqft_per_piece = (total_width_inches * total_height_inches) / 144
            total_sqft_entry = sqft_per_piece * entry.get('qty', 1)
            
            sides_cost_per_unit = SIDES_TIERS_MAP.get(entry.get('sides_tier_selection'), 0)
            
            options_for_type = SPECIALTY_FINISHING.get(entry.get('finishing_type'), {})
            if entry.get('finishing_type') == "Banner/Mesh":
                _ , finishing_price_per_unit = get_banner_mesh_details(sqft_per_piece, options_for_type)
                dynamic_option_name = list(options_for_type.keys())[0]
            else:
                finishing_price_per_unit = options_for_type.get(entry.get('finishing_option'), 0)
                dynamic_option_name = entry.get('finishing_option')
            
            cut_cost_per_unit = CUT_COST_MAP.get(entry.get('cut_cost_selection'), 0)
            
            label_col, value_col = st.columns(2)
            summary_items = {
                "Width (ft)": entry.get('w_ft', 0), "Width (in)": entry.get('w_in', 0),
                "Height (ft)": entry.get('h_ft', 0), "Height (in)": entry.get('h_in', 0),
                "Quantity": entry.get('qty', 1)
            }
            for label, value in summary_items.items():
                label_col.markdown(f"**{label}**")
                value_col.markdown(f"`{value}`")

            label_col.divider(); value_col.divider()
            
            label_col.markdown("**SQ'/piece**"); value_col.markdown(f"`{sqft_per_piece:.2f}`")
            label_col.markdown("**Total SQ' for Entry**"); value_col.markdown(f"`{total_sqft_entry:.2f}`")

            label_col.divider(); value_col.divider()

            label_col.markdown("**Sides Cost/Unit**"); value_col.markdown(f"`${sides_cost_per_unit:,.2f}`")
            label_col.markdown("**Finishing Cost/Unit**"); value_col.markdown(f"`${finishing_price_per_unit:,.2f}`")
            label_col.markdown("**Cut Cost/Unit**"); value_col.markdown(f"`${cut_cost_per_unit:,.2f}`")

    total_addons_cost_entry = (sides_cost_per_unit + finishing_price_per_unit + cut_cost_per_unit) * entry.get('qty', 1)
    
    export_data = {
        "Type": entry.get('type'), "Identifier": entry.get('identifier'), "Num of pieces": entry.get('qty'), "Yearly pieces": entry.get('yearly_qty'),
        "Width (in)": total_width_inches, "Height (in)": total_height_inches, "SQ' per piece": f"{sqft_per_piece:.2f}",
        "Total SQ'": f"{total_sqft_entry:.2f}", "Sides Tier": entry.get('sides_tier_selection'), "Finishing Type": entry.get('finishing_type'),
        "Finishing Option": dynamic_option_name, "Cut Cost Option": entry.get('cut_cost_selection'), "Line Item Add-on Cost": f"{total_addons_cost_entry:.2f}"
    }
    return "ok", total_sqft_entry, total_addons_cost_entry, export_data

def render_expanded_layout(entry, i):
    """Renders the full-width, top-to-bottom layout from expanded.py"""
    
    with st.container(border=True):
        st.markdown(f"<a name='entry-{entry['id']}'></a>", unsafe_allow_html=True)
        
        row1_col1, row1_col2, row1_col3 = st.columns([2, 3, 1])
        with row1_col1:
            entry['type'] = st.selectbox("Type", ["Banner", "Decal", "Other"], key=f"type_{entry['id']}", index=0)
        with row1_col2:
            entry['identifier'] = st.text_input("Identifier", key=f"id_{entry['id']}", value=entry.get('identifier', ''))
        with row1_col3:
            st.write("") 
            st.write("") 
            if st.button("❌", key=f"remove_{entry['id']}", help="Remove this entry"):
                return "remove_entry", None, None, None

        dim_col1, dim_col2, dim_col3 = st.columns([2, 2, 2])
        with dim_col1:
            st.markdown("**Width**"); w_ft_col, w_in_col = st.columns(2)
            with w_ft_col: entry['w_ft'] = st.number_input("ft", min_value=0, key=f"w_ft_{entry['id']}", value=entry.get('w_ft', 0), label_visibility="collapsed")
            with w_in_col: entry['w_in'] = st.number_input("in", min_value=0, key=f"w_in_{entry['id']}", value=entry.get('w_in', 0), label_visibility="collapsed")
        with dim_col2:
            st.markdown("**Height**"); h_ft_col, h_in_col = st.columns(2)
            with h_ft_col: entry['h_ft'] = st.number_input("ft", min_value=0, key=f"h_ft_{entry['id']}", value=entry.get('h_ft', 0), label_visibility="collapsed")
            with h_in_col: entry['h_in'] = st.number_input("in", min_value=0, key=f"h_in_{entry['id']}", value=entry.get('h_in', 0), label_visibility="collapsed")
        with dim_col3:
            st.markdown("**Quantity**"); entry['qty'] = st.number_input("Num of pieces", min_value=1, key=f"qty_{entry['id']}", value=entry.get('qty', 1), label_visibility="collapsed")

        total_width_inches = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
        total_height_inches = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
        sqft_per_piece = (total_width_inches * total_height_inches) / 144
        total_sqft_entry = sqft_per_piece * entry.get('qty', 1)

        metric_col1, metric_col2 = st.columns(2)
        with metric_col1: st.metric(label="SQ'/piece", value=f"{sqft_per_piece:.2f}")
        with metric_col2: st.metric(label="Total SQ'", value=f"{total_sqft_entry:.2f}")

        st.divider()

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
            # If type is 'Banner' and finishing is the default, suggest 'Banner/Mesh'
            if entry['type'] == "Banner" and entry.get('finishing_type') == 'Nothing Special':
                entry['finishing_type'] = "Banner/Mesh"

            # Determine the index from the current entry state
            try:
                finishing_type_index = FINISHING_TYPES.index(entry.get('finishing_type', 'Nothing Special'))
            except ValueError:
                finishing_type_index = 0 # Default to first item if not found

            selected_type = st.selectbox("Finishing Type", options=FINISHING_TYPES, key=f"fin_type_{entry['id']}", index=finishing_type_index)
            entry['finishing_type'] = selected_type
        with fc2:
            options_for_type = SPECIALTY_FINISHING.get(selected_type, {})
            if selected_type == "Banner/Mesh":
                dynamic_option_name, finishing_price_per_unit = get_banner_mesh_details(sqft_per_piece, options_for_type)
                st.text_input("Finishing Option", value=dynamic_option_name, key=f"fin_opt_{entry['id']}", disabled=True)
            else:
                selected_option = st.selectbox("Finishing Option", options=list(options_for_type.keys()), key=f"fin_opt_{entry['id']}", index=0)
                entry['finishing_option'] = selected_option
                dynamic_option_name = selected_option
                finishing_price_per_unit = options_for_type.get(selected_option, 0)
        with fc3:
            st.metric(label="Finishing Cost/Unit", value=f"${finishing_price_per_unit:.2f}")

        cc1, cc2 = st.columns(2)
        with cc1:
            def format_cut_cost_option(option_name): return f"{option_name} - ${CUT_COST_MAP.get(option_name, 0):.2f}"
            selected_cut_cost_desc = st.selectbox("Cut Option", options=CUT_COST_OPTIONS, key=f"cut_cost_{entry['id']}", index=0, format_func=format_cut_cost_option)
            entry['cut_cost_selection'] = selected_cut_cost_desc
            cut_cost_per_unit = CUT_COST_MAP.get(selected_cut_cost_desc, 0)
        with cc2:
            st.metric(label="Cut Cost/Unit", value=f"${cut_cost_per_unit:.2f}")
        
    total_addons_cost_entry = (sides_cost_per_unit + finishing_price_per_unit + cut_cost_per_unit) * entry.get('qty', 1)
    
    export_data = {
        "Type": entry.get('type'), "Identifier": entry.get('identifier'), "Num of pieces": entry.get('qty'), "Yearly pieces": entry.get('yearly_qty'),
        "Width (in)": total_width_inches, "Height (in)": total_height_inches, "SQ' per piece": f"{sqft_per_piece:.2f}",
        "Total SQ'": f"{total_sqft_entry:.2f}", "Sides Tier": selected_tier_desc, "Finishing Type": selected_type,
        "Finishing Option": dynamic_option_name, "Cut Cost Option": selected_cut_cost_desc, "Line Item Add-on Cost": f"{total_addons_cost_entry:.2f}"
    }
    return "ok", total_sqft_entry, total_addons_cost_entry, export_data


# --- Initialize session state ---
if 'entries' not in st.session_state:
    st.session_state.entries = [{
        "id": str(uuid.uuid4()), "type": "Banner", "identifier": "", "w_ft": 0, "w_in": 0,
        "h_ft": 0, "h_in": 0, "qty": 1, "yearly_qty": 0, "sidedness": SIDEDNESS_OPTIONS[0],
        "cut_cost_selection": CUT_COST_OPTIONS[0], 'finishing_type': 'Nothing Special', 'finishing_option': 'Nothing Special',
        'sides_tier_selection': "STANDARD OVER 1sq'"
    }]
if 'layout_choice' not in st.session_state:
    st.session_state.layout_choice = 'Compact'

# --- Main App Logic ---
total_sqft_order = 0
total_order_addon_cost = 0
entries_to_keep = []
data_for_export = []
remove_entry_index = None

for i, entry in enumerate(st.session_state.entries):
    
    if st.session_state.layout_choice == 'Compact':
        status, sqft, addon_cost, export_data = render_compact_layout(entry, i)
    else: # Expanded layout
        status, sqft, addon_cost, export_data = render_expanded_layout(entry, i)

    if status == "remove_entry":
        remove_entry_index = i
    else:
        total_sqft_order += sqft
        total_order_addon_cost += addon_cost
        data_for_export.append(export_data)

if remove_entry_index is not None:
    st.session_state.entries.pop(remove_entry_index)
    st.rerun()

st.divider()
if st.button("➕ Add New Entry", use_container_width=True):
    st.session_state.entries.append({
        "id": str(uuid.uuid4()), "type": "Banner", "identifier": "", "w_ft": 0, "w_in": 0,
        "h_ft": 0, "h_in": 0, "qty": 1, "yearly_qty": 0, "sidedness": SIDEDNESS_OPTIONS[0],
        "cut_cost_selection": CUT_COST_OPTIONS[0], 'finishing_type': 'Nothing Special', 'finishing_option': 'Nothing Special',
        'sides_tier_selection': "STANDARD OVER 1sq'"
    })
    st.rerun()

# --- SIDEBAR ---
st.sidebar.header("Quote Summary")

# --- NEW: Layout Selector ---
st.sidebar.radio("Select Entry Layout", options=['Compact', 'Expanded'], key='layout_choice', horizontal=True)

with st.sidebar.expander("Go to Entry...", expanded=True):
    for i, entry in enumerate(st.session_state.entries):
        identifier = entry.get('identifier') if entry.get('identifier') else f"Entry {i + 1}"
        w_in = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
        h_in = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
        summary_text = f"**{identifier}**: {w_in}\" x {h_in}\" (Qty: {entry.get('qty', 1)})"
        st.markdown(f"[{summary_text}](#entry-{entry['id']})", unsafe_allow_html=True)

st.sidebar.divider()

customer_type_index = CUSTOMER_TYPES.index(st.sidebar.selectbox("Select Customer Type", options=CUSTOMER_TYPES, index=0))
selected_customer_type = CUSTOMER_TYPES[customer_type_index]
base_price_per_sqft = CUSTOMER_BASE_PRICES.get(selected_customer_type, 0)
total_base_price = total_sqft_order * base_price_per_sqft
st.sidebar.metric(label="TOTAL SQ' IN ORDER", value=f"{total_sqft_order:.2f}")
st.sidebar.divider()

subtotal = total_base_price + total_order_addon_cost

st.sidebar.markdown("#### SQ' Discount")
tier_description, current_tier_discounts = get_discount_tier_details(total_sqft_order)
if st.sidebar.checkbox("Apply Special 20.20% Discount", key="special_discount_checkbox"):
    selected_percentage = 0.2020
else:
    selected_percentage = current_tier_discounts[customer_type_index]
price_after_sq_discount = subtotal * (1 - selected_percentage)
st.sidebar.divider()

st.sidebar.markdown("#### Print Adjustment")
def format_adjustment_option(option_name): return f"{option_name} ({PRINT_ADJUSTMENT_FIXED.get(option_name, 0):+.1%})"
selected_adjustment_label = st.sidebar.selectbox("Select Adjustment", options=list(PRINT_ADJUSTMENT_FIXED.keys()), index=0, format_func=format_adjustment_option)
adjustment_percentage = PRINT_ADJUSTMENT_FIXED[selected_adjustment_label]
price_after_print_adjustment = price_after_sq_discount * (1 + adjustment_percentage)
st.sidebar.divider()

st.sidebar.markdown("#### Multiples")
num_entries = len(st.session_state.entries)
multiple_desc, multiples_value = get_multiplier(num_entries)
st.sidebar.metric(label=f"Multiplier ({multiple_desc})", value=f"x{multiples_value}")

grand_total = price_after_print_adjustment * multiples_value

st.sidebar.markdown("### Grand Total")
st.sidebar.markdown(f"<h2 style='text-align: right; color: green;'>${grand_total:,.2f}</h2>", unsafe_allow_html=True)
st.sidebar.divider()

if data_for_export:
    df = pd.DataFrame(data_for_export)
    summary_data = {
        "Type": "---", "Identifier": "FINANCIAL SUMMARY", "Num of pieces": "---", "Yearly pieces": "---",
        "Width (in)": "---", "Height (in)": "---", "SQ' per piece": "---", "Total SQ'": "---",
        "Sides Tier": "---", "Finishing Type": "---", "Finishing Option": "---", "Cut Cost Option": "---",
        "Line Item Add-on Cost": "---",
        "Customer Type": selected_customer_type, "SQ' Discount": f"{selected_percentage:.2%}",
        "Print Adjustment": selected_adjustment_label, "Multiplier": f"x{multiples_value} ({multiple_desc})",
        "GRAND TOTAL": f"{grand_total:,.2f}"
    }
    summary_df = pd.DataFrame([summary_data])
    combined_df = pd.concat([df, summary_df], ignore_index=True)
    csv = combined_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(label="📄 Download Quote as CSV", data=csv, file_name='quote_summary.csv', mime='text/csv', use_container_width=True)