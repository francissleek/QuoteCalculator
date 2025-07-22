import math

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
        p_base = excel_floor(p_vars.get('preferred_historical_price', 0) * p_vars.get('preferred_fine_tune_modifier', 0))
        results['preferred_base'] = p_base
        results['preferred_value'] = p_base * (1 - p_vars.get('preferred_discount_value', 0))

        c_vars = material_data['Corporate']
        c_base = excel_ceiling(p_base * c_vars.get('corporate_historical_price', 0))
        results['corporate_base'] = c_base
        results['corporate_value'] = c_base * (1 - c_vars.get('corporate_discount_value', 0))

        w_vars = material_data['Wholesale']
        w_base = excel_ceiling(p_base * w_vars.get('wholesale_historical_price', 0))
        results['wholesale_base'] = w_base
        results['wholesale_value'] = w_base * (1 - w_vars.get('wholesale_discount_value', 0))
    except (KeyError, TypeError):
        pass
    return results