# Dataverse Table Configuration
# Add your custom Dataverse tables here

# Instructions:
# 1. Find your table's logical name in Power Apps:
#    - Go to https://make.powerapps.com
#    - Select your environment
#    - Go to Tables
#    - Find your table and note the "Logical name" (e.g., cr123_sales)
#
# 2. Add the logical name to DATAVERSE_TABLES below
# 3. Restart the application

# Example for a sales table:
# If your table is called "Sales" and has logical name "cr123_sales"
# Add: 'cr123_sales'

# List of tables to search (use logical names, not display names)
DATAVERSE_TABLES = [
    'account',      # Standard Accounts table
    'contact',      # Standard Contacts table
    'cr5cd_sales',  # Custom Sales table
]

# Field names for common data (customize based on your schema)
SALES_TABLE_CONFIG = {
    # Your actual sales table logical name
    'table_name': 'cr5cd_sales',  
    
    # Amount/revenue fields from your table
    'amount_fields': [
        'cr5cd_unitprice',      # Unit price field
        'cr5cd_taxamount',      # Tax amount field
        'cr5cd_quantityordered' # Quantity field (for calculations)
    ],
    
    # Date fields (for filtering by year)
    'date_fields': [
        'cr5cd_orderdate',  # Order date field
        'createdon',        # Created date
        'modifiedon'        # Modified date
    ],
    
    # Product/item fields
    'product_fields': [
        'cr5cd_itemname',   # Item name field
    ]
}
