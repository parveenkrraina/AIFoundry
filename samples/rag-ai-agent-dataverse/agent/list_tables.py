"""
DEPRECATED: use metadata-driven any-table queries directly in the agent.
- Example: python main.py "show records from account"
This script is no longer needed and kept only as a stub.
"""

if __name__ == "__main__":
    print("This tool is deprecated. Use 'python main.py ""show records from <table>""' instead.")
    
    # Try to discover custom tables by querying a sample
    print(f"\n🎨 SEARCHING FOR CUSTOM TABLES:")
    print("-" * 80)
    print("ℹ️  Trying common custom table prefixes (cr, new, vnodeites)...\n")
    
    # Try common prefixes
    prefixes = ['cr5cd', 'new', 'vnodeites', 'vno']
    common_names = ['sales', 'order', 'product', 'customer', 'transaction', 'invoice', 'payment']
    
    for prefix in prefixes:
        for name in common_names:
            for suffix in ['', 's']:
                table_name = f"{prefix}_{name}{suffix}"
                try:
                    url = f"{DATAVERSE_URL}/api/data/v9.2/{table_name}"
                    response = requests.get(url, headers=headers, params={'$top': 1}, timeout=5)
                    
                    if response.status_code == 200:
                        result = response.json()
                        record_count = len(result.get('value', []))
                        print(f"  ✅ {table_name:<25} (Found! Sample records: {record_count})")
                        found_tables.append(table_name)
                        
                except:
                    pass
    
    print(f"\n📊 SUMMARY:")
    print("-" * 80)
    print(f"Found {len(found_tables)} accessible tables")
    
    if found_tables:
        print(f"\n💡 Add these to dataverse_config.py:")
        print("DATAVERSE_TABLES = [")
        for table in found_tables:
            print(f"    '{table}',")
        print("]")
    
    return found_tables


def query_specific_table(table_name):
    """Query a specific table and show its structure."""
    print(f"\n🔍 QUERYING TABLE: {table_name}\n")
    
    credential = InteractiveBrowserCredential(client_id=CLIENT_ID, tenant_id=TENANT_ID)
    token = credential.get_token(f"{DATAVERSE_URL}/.default")
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0"
    }
    
    # Try different endpoint variations
    variations = [table_name, table_name + 's', table_name + 'es']
    
    for endpoint in variations:
        try:
            url = f"{DATAVERSE_URL}/api/data/v9.2/{endpoint}"
            print(f"Trying: {url}")
            
            response = requests.get(url, headers=headers, params={'$top': 5}, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                records = result.get('value', [])
                
                print(f"\n✅ SUCCESS! Found {len(records)} records\n")
                
                if records:
                    print("📋 FIELDS IN FIRST RECORD:")
                    print("-" * 80)
                    first = records[0]
                    for key in sorted(first.keys()):
                        if not key.startswith('@') and not key.startswith('_'):
                            value = str(first[key])[:60]
                            print(f"  {key:<40} {value}")
                    
                    print(f"\n📊 ALL RECORDS:")
                    print("-" * 80)
                    for i, record in enumerate(records, 1):
                        # Try to find a name field
                        name = record.get('name') or record.get('fullname') or \
                               record.get(f"{table_name}name") or \
                               next((v for k, v in record.items() if 'name' in k.lower() and not k.startswith('_')), 'Record')
                        
                        # Try to find amount/value field
                        amount = record.get('amount') or record.get('totalamount') or \
                                record.get('salesamount') or \
                                next((v for k, v in record.items() if 'amount' in k.lower() or 'value' in k.lower()), None)
                        
                        if amount:
                            print(f"  {i}. {name} - Amount: {amount}")
                        else:
                            print(f"  {i}. {name}")
                else:
                    print("ℹ️  Table exists but has no records")
                
                return True
                
            elif response.status_code == 404:
                print(f"  ❌ Not found")
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n❌ Could not access table '{table_name}' with any endpoint variation")
    return False


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*80)
    print("🔍 SIMPLE DATAVERSE TABLE SCANNER")
    print("="*80)
    
    if len(sys.argv) > 1:
        # Query specific table
        table_name = sys.argv[1]
        query_specific_table(table_name)
    else:
        # List all tables
        found = list_tables_simple()
        
        if found:
            print(f"\n💡 To query a specific table, run:")
            print(f"   python list_tables.py <table_name>")
            print(f"\n   Example: python list_tables.py account")
