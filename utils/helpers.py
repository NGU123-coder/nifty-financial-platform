import re

def clean_currency(value):
    if isinstance(value, str):
        # Remove commas, currency symbols and handle parentheses for negative numbers
        value = value.replace(',', '').replace('₹', '').strip()
        if value.startswith('(') and value.endswith(')'):
            value = '-' + value[1:-1]
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def parse_sql_insert(line):
    """
    Rudimentary parser for MySQL INSERT INTO statements.
    Extracts values between parentheses.
    """
    values_match = re.search(r"VALUES\s*(.*);", line, re.IGNORECASE)
    if not values_match:
        return []
    
    content = values_match.group(1)
    # Split by ),( but handle potential escaped commas within strings
    # This is a simplified version; production might need a more robust parser
    rows = re.split(r"\),\s*\(", content.strip("()"))
    return rows
