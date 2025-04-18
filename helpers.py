#!/usr/bin/env python3

# helpers.py                                                               #
# Solution Deployer, Version 7.6.x b130                                      #
# -------------------------------------------------------------------------- #
# Maintainers: CSE Telco/MSSP EMEA, Fortinet (internal use only)             #
# -------------------------------------------------------------------------- #

def print_table(data, columns=None, keyColumn="", title=None):
    """
    Prints a dictionary of dictionaries in a nicely formatted multi-column table.
    
    Args:
        data (dict): The dictionary where each value is another dictionary
        columns (dict, optional): The dictionary that maps columns to the keys of the "value dictionary"
        keyColumn (str, optional): The title of the leftmost column
        title (str, optional): Title for the table
    """
    if not data:
        return
    
    # Collect all keys from nested dictionaries
    if not columns:
        columns = {}
        for value in data.values():
            if isinstance(value, dict):
                for k in value.keys():
                    columns[k] = k

    # Prepare all rows (including header)
    rows = []
    header = [keyColumn] + list(columns.keys())
    rows.append(header)
        
    # Prepare data rows
    for key, value in data.items():
        if not isinstance(value, dict):
            value = {"Value": value}  # Wrap non-dict values
        
        row = [str(key)]
        for c in columns.values():
            row.append(str(value.get(c, "")))
        rows.append(row)
    
    # Calculate column widths
    col_widths = []
    for i in range(len(header)):
        col_widths.append(max(len(str(row[i])) for row in rows))
    
    # Calculate total table width
    total_width = sum(col_widths) + 3 * len(col_widths) + 1
    
    # Print title if provided
    if title:
        print(f"{title:^{total_width}}")
        # print()
    
    # Print table header separator
    print("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
    
    # Print header row
    print("| " + " | ".join(
        header[i].ljust(col_widths[i]) for i in range(len(header))) + " |")
    
    # Print header separator
    print("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
    
    # Print data rows
    for row in rows[1:]:
        print("| " + " | ".join(
            row[i].ljust(col_widths[i]) for i in range(len(row))) + " |")
    
    # Print table footer
    print("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")

