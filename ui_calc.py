# FILE: ui_quotecalc.py
# UPDATED: Moved the "Remove" button to the top row next to the identifier.

import streamlit as st
import uuid
import pandas as pd

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Universal Quote Calculator")
st.title("Universal Quote Calculator")

# --- Data Structures for Logic ---

# LIST 1: Sides Computation (Original)
SIDES_TIERS_MAP = {
    "STANDARD OVER 1sq'": 1.00,
    "SMALL Between 1sq' - 0.5sq'": 1.25,
    "SMALL BETWEEN 0.5 - .25 sq' /peice": 1.65,
    "SMALLER BETWEEN 0.25 - .1 sq' /peice": 1.75,
    "SMALLER BETWEEN 0.1 - .05 sq' /peice": 2.50,
    "SMALLEST UNDER 0.05 sq' /peice": 3.00,
    "NO PRINT": 0.65, "DOUBLE SIDED Over 1 SQ'": 1.60,
    "DOUBLE SIDED between 1sq' - 0.5sq' per peice": 2.25,
    "DOUBLE SIDED under 0.5 - .25 sq' /peice": 2.75,
    "DOUBLE SIDED under 0.25 - .1 sq' /peice": 3.50,
    "DOUBLE SIDED under 0.1 - .05 sq' /peice": 3.75,
    "DOUBLE SIDED under 0.05 sq' /peice": 4.00,
}
TIER_DESCRIPTIONS = list(SIDES_TIERS_MAP.keys())
SIDEDNESS_OPTIONS = ["Single Sided", "Double Sided", "No Print"]

# LIST 2: Specialty Finishing (Original)
SPECIALTY_FINISHING = {
    "Nothing Special": {"Nothing Special": 0.00},
    "Banner/Mesh": {
        "POCKET or HEMM AND GROMMETS EVERY 2'": [
            (500, 0.20, "OVER 500 sq' per piece"),
            (200, 0.42, "200 sq' - 500sq' per piece"),
            (100, 0.65, "100sq' - 250sq' per piece"),
            (50, 1.00, "50 sq' - 100sq' per piece"),
            (0, 1.32, "UNDER 50 sq' per piece")
        ]
    },
    "Laminate & Addons": {
        "Additional Laminate/sq'": 1.80,
        "textured floor/graffiti laminte/Dry Erase": 4.00,
        "Add Print on NO PRINT": 3.75, "ADD White Ink": 0.62,
        "IJ 35 Vinyl with 200G - applied": 3.79,
        "IJ 180CV3 with 8518": 5.75,
        "Meta Mark - Reflective Applied including 200G laminate": 6.25,
        "3M IJ680 - Reflective Applied including 8518 laminate": 7.25,
        "Wet or Dry mount on Acrylic": 8.00
    }
}
FINISHING_TYPES = list(SPECIALTY_FINISHING.keys())

# LIST 3: SQ' Discount (Original)
CUSTOMER_TYPES = ["Preferred", "Corporate", "Wholesale"]
CUSTOMER_BASE_PRICES = {"Preferred": 7.00, "Corporate": 6.50, "Wholesale": 5.00}
VOLUME_DISCOUNT_TIERS = {
    10000: ("10K+ sq'", [0.35, 0.351, 0.302]),
    5000:  ("5K - 10K sq'", [0.30, 0.301, 0.252]),
    3000:  ("3K - 5K sq'", [0.25, 0.251, 0.252]),
    1000:  ("1K - 3K sq'", [0.22, 0.221, 0.152]),
    500:   ("500 - 1000 sq'", [0.15, 0.151, 0.102]),
    300:   ("300 - 500 sq'", [0.10, 0.101, 0.082]),
    200:   ("200 - 300 sq'", [0.05, 0.051, 0.052]),
    100:   ("100 - 200 sq'", [0.03, 0.031, 0.032]),
    50:    ("50 - 100 sq'", [0.00, 0.00, 0.00]),
    0:     ("Under 50 sq'", [0.00, 0.00, 0.00])
}

# LIST 4: Print Adjustment (Original)
PRINT_ADJUSTMENT_FIXED = {
    "no adjustment": 0.0,
    "retail": 0.101,
    "Promo": 0.05,
    "OT 24 hour rush": 0.25,
    "weekend hour rush": 0.15,
    "Charitable": -0.15
}
PRINT_ADJUSTMENT_COMMODITY = {
    10000: ("10k+ sq'", -0.27),
    5000: ("5K - 10K sq'", -0.25),
    3000: ("3K-5K sq'", -0.23),
    1000: ("1K - 3Ksq'", -0.22),
    500: ("500 - 1000 sq'", -0.20),
    300: ("300 - 500 SQ'", -0.17),
    200: ("200 - 300 sq'", -0.15),
    100: ("100 - 200 sq'", -0.10),
    50: ("50 - 100 sq'", -0.051),
}

# NEW - LIST 5: Cut Cost
CUT_COST_MAP = {
    "NO CUT": 0.00, "tiling cut": 0.00,
    "Rigid Blade cut: Less than 5 cuts per sheet": 0.00,
    "Rigid Blade cut: 5 to 10 cuts per sheet": 0.25,
    "Rigid Blade cut: 10+ cuts per sheet over 6\"": 0.45,
    "Rigid Router cut: Less than 5 cuts per sheet": 0.50,
    "Rigid Router cut: Up to 10 cuts per sheet": 0.75,
    "Rigid Router cut: 10+ cuts per sheet over 6\"": 1.25,
    "+ 3 object - Kiss/Rigid cut: Perimeter square": 0.20,
    "+ 3 object - Kiss/Rigid cut: Simple Shape - Circle/Triangle/bubble cut": 0.28,
    "+ 3 object - Kiss/Rigid cut: Medium letter shape and interior": 0.61,
    "+ 3 object - Kiss/Rigid cut: Complex shape and interiors": 1.82,
    "3\" - 1\" OBJECT Kiss/Rigid cut: Simple Perimeter 3\"-1\"": 0.50,
    "3\" - 1\" OBJECT Kiss/Rigid cut: Kiss/Rigid simple Shape 3\"-1\"": 0.66,
    "3\" - 1\" OBJECT Kiss/Rigid cut: medium letter shape and interior 3\"-1\"": 1.05,
    "3\" - 1\" OBJECT Kiss/Rigid cut: complex shape and interiors 3\"-1\"": 2.15,
    "UNDER 1\" Kiss/Rigid: Perimeter simple": 0.55,
    "UNDER 1\" Kiss/Rigid: simple Shape": 0.94,
    "UNDER 1\" Kiss/Rigid: medium letter shape and interior": 1.93,
    "UNDER 1\" Kiss/Rigid: complex shape and interiors": 3.14,
    "ROUTER Over 3\" object: perimeter simple": 2.75,
    "ROUTER Over 3\" object: simple shape": 3.85,
    "ROUTER Over 3\" object: medium letter": 4.24,
    "ROUTER Over 3\" object: complex": 7.15,
    "ROUTER 3\" - 1\" OBJECT ROUTER: simple perimeter": 4.40,
    "ROUTER 3\" - 1\" OBJECT ROUTER: simple shape": 6.16,
    "ROUTER 3\" - 1\" OBJECT ROUTER: medium letter": 6.78,
    "ROUTER 3\" - 1\" OBJECT ROUTER: complex": 8.50,
    "UNDER 1\" ROUTER: simple perimeter": 6.05,
    "UNDER 1\" ROUTER: Router simple shape": 5.50,
    "UNDER 1\" ROUTER: router medium letter": 7.50,
    "UNDER 1\" ROUTER: router complex": 9.75,
}
CUT_COST_OPTIONS = list(CUT_COST_MAP.keys())

# NEW - LIST 6: Multpiles
MULTIPLES_MAP = {
    20: 100000,
    10: 8,
    5: 5,
    4: 3,
    3: 2,
    2: 1.5,
    1: 1
}

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

# --- Initialize session state ---
if 'entries' not in st.session_state:
    st.session_state.entries = [{
        "id": str(uuid.uuid4()), "type": "Banner", "identifier": "", "w_ft": 0, "w_in": 0,
        "h_ft": 0, "h_in": 0, "qty": 1, "yearly_qty": 0, "sidedness": SIDEDNESS_OPTIONS[0],
        "cut_cost_selection": CUT_COST_OPTIONS[0]
    }]

# --- Main App Logic ---
total_sqft_order = 0
total_order_addon_cost = 0
entries_to_keep = []
has_been_removed = False
data_for_export = []

for i, entry in enumerate(st.session_state.entries):
    with st.container(border=True):
        st.markdown(f"<a name='entry-{entry['id']}'></a>", unsafe_allow_html=True)
        
        # --- ROW 1: Type, Identifier, and Remove Button ---
        row1_col1, row1_col2, row1_col3 = st.columns([2, 3, 1])
        with row1_col1:
            entry['type'] = st.selectbox("Type", ["Banner", "Decal", "Other"], key=f"type_{entry['id']}", index=0)
        with row1_col2:
            entry['identifier'] = st.text_input("Identifier", key=f"id_{entry['id']}", value=entry.get('identifier', ''))
        with row1_col3:
            st.write("") 
            st.write("") # For vertical alignment
            if st.button("❌", key=f"remove_{entry['id']}", help="Remove this entry"):
                has_been_removed = True
                continue

        # --- ROW 2: Dimensions and Quantity ---
        dim_col1, dim_col2, dim_col3 = st.columns([2, 2, 2])
        with dim_col1:
            w_ft_col, w_in_col = st.columns(2)
            with w_ft_col:
                st.caption("Width (ft)")
                entry['w_ft'] = st.number_input("ft", min_value=0, key=f"w_ft_{entry['id']}", value=entry.get('w_ft', 0), label_visibility="collapsed")
            with w_in_col:
                st.caption("Width (in)")
                entry['w_in'] = st.number_input("in", min_value=0, key=f"w_in_{entry['id']}", value=entry.get('w_in', 0), label_visibility="collapsed")
        with dim_col2:
            h_ft_col, h_in_col = st.columns(2)
            with h_ft_col:
                st.caption("Height (ft)")
                entry['h_ft'] = st.number_input("ft", min_value=0, key=f"h_ft_{entry['id']}", value=entry.get('h_ft', 0), label_visibility="collapsed")
            with h_in_col:
                st.caption("Height (in)")
                entry['h_in'] = st.number_input("in", min_value=0, key=f"h_in_{entry['id']}", value=entry.get('h_in', 0), label_visibility="collapsed")
        with dim_col3:
            st.caption("Quantity per material")
            entry['qty'] = st.number_input("Num of pieces", min_value=1, key=f"qty_{entry['id']}", value=entry.get('qty', 1), label_visibility="collapsed")

        # --- Calculations are performed after all inputs are defined ---
        total_width_inches = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
        total_height_inches = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
        sqft_per_piece = (total_width_inches * total_height_inches) / 144 if total_width_inches > 0 and total_height_inches > 0 else 0
        total_sqft_entry = sqft_per_piece * entry.get('qty', 1)

        # --- ROW 3: SQ' METRICS ---
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
             st.metric(label="SQ'/piece", value=f"{sqft_per_piece:.2f}")
        with metric_col2:
            st.metric(label="Total SQ'", value=f"{total_sqft_entry:.2f}")

        st.divider()

        # --- Add-on Sections ---
        sc1, sc2, sc3 = st.columns([1, 2, 3])
        with sc1:
            sidedness_index = SIDEDNESS_OPTIONS.index(entry.get('sidedness', SIDEDNESS_OPTIONS[0]))
            entry['sidedness'] = st.selectbox("Sidedness", options=SIDEDNESS_OPTIONS, key=f"side_{entry['id']}", index=sidedness_index)
        with sc2:
            suggested_tier = get_suggested_sides_tier(sqft_per_piece, entry['sidedness'])
            try: tier_index = TIER_DESCRIPTIONS.index(suggested_tier)
            except ValueError: tier_index = 0
            def format_tier_option(option_name):
                cost = SIDES_TIERS_MAP.get(option_name, 0)
                return f"{option_name} - ${cost:.2f}"
            selected_tier_desc = st.selectbox("Tier", options=TIER_DESCRIPTIONS, index=tier_index, key=f"sides_tier_{entry['id']}", format_func=format_tier_option)
            entry['sides_tier_selection'] = selected_tier_desc
        with sc3:
            sides_cost_per_unit = SIDES_TIERS_MAP.get(entry.get('sides_tier_selection'), 0)
            st.metric(label="Sides Cost/Unit", value=f"${sides_cost_per_unit:.2f}")

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            suggested_fin_type = get_suggested_finishing_type(entry['type'], total_width_inches, total_height_inches)
            try: fin_type_index = FINISHING_TYPES.index(entry.get('finishing_type', suggested_fin_type))
            except ValueError: fin_type_index = 0
            selected_type = st.selectbox("Finishing Type", options=FINISHING_TYPES, key=f"fin_type_{entry['id']}", index=fin_type_index)
            entry['finishing_type'] = selected_type
        with fc2:
            options_for_type = SPECIALTY_FINISHING.get(selected_type, {})
            finishing_price_per_unit = 0
            dynamic_option_name = "N/A"
            if selected_type == "Banner/Mesh":
                dynamic_option_name, finishing_price_per_unit = get_banner_mesh_details(sqft_per_piece, options_for_type)
                st.text_input("Finishing Option", value=dynamic_option_name, key=f"fin_opt_{entry['id']}", disabled=True)
            else:
                option_keys = list(options_for_type.keys())
                try: option_index = option_keys.index(entry.get('finishing_option', option_keys[0]))
                except (ValueError, IndexError): option_index = 0
                selected_option = st.selectbox("Finishing Option", options=option_keys, key=f"fin_opt_{entry['id']}", index=option_index)
                entry['finishing_option'] = selected_option
                dynamic_option_name = selected_option
                finishing_price_per_unit = options_for_type.get(selected_option, 0)
        with fc3:
            st.metric(label="Finishing Cost/Unit", value=f"${finishing_price_per_unit:.2f}")

        cc1, cc2 = st.columns(2)
        with cc1:
            try:
                cut_cost_index = CUT_COST_OPTIONS.index(entry.get('cut_cost_selection', CUT_COST_OPTIONS[0]))
            except ValueError as e:
                print(f"Error finding cut cost index: {e}")
                cut_cost_index = 0
            def format_cut_cost_option(option_name):
                cost = CUT_COST_MAP.get(option_name, 0)
                return f"{option_name} - ${cost:.2f}"
            selected_cut_cost_desc = st.selectbox("Cut Option", options=CUT_COST_OPTIONS, key=f"cut_cost_{entry['id']}", index=cut_cost_index, format_func=format_cut_cost_option)
            entry['cut_cost_selection'] = selected_cut_cost_desc
            cut_cost_per_unit = CUT_COST_MAP.get(selected_cut_cost_desc, 0)
        with cc2:
            st.metric(label="Cut Cost/Unit", value=f"${cut_cost_per_unit:.2f}")
        
        # --- AGGREGATION FOR THIS ENTRY (Corrected Location) ---
        total_addons_cost_entry = (sides_cost_per_unit + finishing_price_per_unit + cut_cost_per_unit) * entry.get('qty', 1)
        total_sqft_order += total_sqft_entry
        total_order_addon_cost += total_addons_cost_entry
        entries_to_keep.append(entry)
        data_for_export.append({
            "Type": entry.get('type'), "Identifier": entry.get('identifier'),
            "Num of pieces": entry.get('qty'), "Yearly pieces": entry.get('yearly_qty'),
            "Width (in)": total_width_inches, "Height (in)": total_height_inches,
            "SQ' per piece": f"{sqft_per_piece:.2f}", "Total SQ'": f"{total_sqft_entry:.2f}",
            "Sides Tier": selected_tier_desc, "Finishing Type": selected_type,
            "Finishing Option": dynamic_option_name, "Cut Cost Option": selected_cut_cost_desc,
            "Line Item Add-on Cost": f"{total_addons_cost_entry:.2f}"
        })

# --- Main App Update Logic ---
st.session_state.entries = entries_to_keep
if has_been_removed: st.rerun()
st.divider()
if st.button("➕ Add New Entry", use_container_width=True):
    st.session_state.entries.append({
        "id": str(uuid.uuid4()), "type": "Banner", "identifier": "", "w_ft": 0, "w_in": 0,
        "h_ft": 0, "h_in": 0, "qty": 1, "yearly_qty": 0, "sidedness": SIDEDNESS_OPTIONS[0],
        "cut_cost_selection": CUT_COST_OPTIONS[0]
    })
    st.rerun()

# --- SIDEBAR ---
st.sidebar.header("Quote Summary")

with st.sidebar.expander("Go to Entry...", expanded=True):
    for i, entry in enumerate(st.session_state.entries):
        identifier = entry.get('identifier') if entry.get('identifier') else f"Entry {i + 1}"
        w_in = (entry.get('w_ft', 0) * 12) + entry.get('w_in', 0)
        h_in = (entry.get('h_ft', 0) * 12) + entry.get('h_in', 0)
        summary_text = f"**{identifier}**: {w_in}\" x {h_in}\" (Qty: {entry.get('qty', 1)})"
        st.markdown(
            f"[{summary_text}](#entry-{entry['id']})", 
            unsafe_allow_html=True
        )

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
st.sidebar.caption(f"Rate based on tier: {tier_description}")
discount_labels = [f"{perc:.2%} ({ctype})" for perc, ctype in zip(current_tier_discounts, CUSTOMER_TYPES)]
special_discount_label = "20.20% (Normal Discount - 3,060 sq')"
discount_labels.append(special_discount_label)
selected_label = st.sidebar.selectbox("SQ' Discount Rate", options=discount_labels, index=customer_type_index)
if selected_label == special_discount_label:
    selected_percentage = 0.2020
else:
    selected_index = discount_labels.index(selected_label)
    selected_percentage = current_tier_discounts[selected_index]
price_after_sq_discount = subtotal * (1 - selected_percentage)
st.sidebar.divider()

st.sidebar.markdown("#### Print Adjustment")
adjustment_options, commodity_tier_desc, default_adjustment_key = get_print_adjustment_details(total_sqft_order)
if commodity_tier_desc:
    st.sidebar.caption(f"Commodity tier: {commodity_tier_desc}")
adjustment_labels = list(adjustment_options.keys())
default_index = adjustment_labels.index(default_adjustment_key)

def format_adjustment_option(option_name):
    percentage = adjustment_options.get(option_name, 0)
    return f"{option_name} ({percentage:+.1%})"

selected_adjustment_label = st.sidebar.selectbox(
    "Select Adjustment",
    options=adjustment_labels,
    index=default_index,
    format_func=format_adjustment_option
)
adjustment_percentage = adjustment_options[selected_adjustment_label]
st.sidebar.metric(label="Print Adjustment Rate", value=f"{adjustment_percentage:.2%}")

price_after_print_adjustment = price_after_sq_discount * (1 + adjustment_percentage)
st.sidebar.divider()

st.sidebar.markdown("#### Multiples")
num_entries = len(st.session_state.entries)
multiple_desc, multiples_value = get_multiplier(num_entries)
st.sidebar.metric(label=f"Multiplier ({multiple_desc})", value=f"x{multiples_value}")

grand_total = price_after_print_adjustment * multiples_value

# --- Final Display and Export ---
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
        "Customer Type": selected_customer_type,
        "SQ' Discount": selected_label,
        "Print Adjustment": selected_adjustment_label,
        "Multiplier": f"x{multiples_value} ({multiple_desc})",
        "GRAND TOTAL": f"{grand_total:,.2f}"
    }
    summary_df = pd.DataFrame([summary_data])
    combined_df = pd.concat([df, summary_df], ignore_index=True)

    csv = combined_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📄 Download Quote as CSV", data=csv,
        file_name='quote_summary.csv', mime='text/csv', use_container_width=True
    )