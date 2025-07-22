import math
from collections import Counter

def calculate_additional_costs(cost_config):
    """Calculate additional costs based on configuration."""
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

def calculate_dynamic_prodcuts_an(vars, Q_Quantity):
    """Calculate dynamic product costs."""
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

def get_multiplier(material_count, multiples_map):
    """Get the multiplier based on material count."""
    applicable_keys = [k for k in multiples_map.keys() if k <= material_count]
    if not applicable_keys:
        return "Single", 1.0
    
    highest_key = max(applicable_keys)
    label = f"{highest_key}+ Items" if highest_key > 1 else "Single"
    return label, multiples_map[highest_key]

def calculate_entry_total(calc_data, customer_type, selected_percentage, adjustment_percentage, 
                         multiples_value, prodcuts_an):
    """Calculate total for a single entry."""
    # Implementation based on your existing calculate_entry_total function
    # This would contain the logic from your original function
    # ...
    
    return entry_total