"""
DEPRECATED: This tool has been superseded by metadata-driven any-table querying
and the Azure AI Search indexer. Please use:
 - agent\\main.py with prompts like "show records from <table>"
 - agent\\indexer.py to populate Azure AI Search for RAG
"""
import sys

if __name__ == "__main__":
    print("This diagnostic tool is deprecated. Use any-table querying in the agent or run agent/indexer.py.")
    sys.exit(0)
"""
DEPRECATED: This tool has been superseded by metadata-driven any-table querying
and the Azure AI Search indexer. Please use:
 - agent\main.py with prompts like "show records from <table>"
 - agent\indexer.py to populate Azure AI Search for RAG
"""
import sys

if __name__ == "__main__":
    print("This diagnostic tool is deprecated. Use any-table querying in the agent or run agent/indexer.py.")
    sys.exit(0)
            print(f"{'Display Name':<35} {'Logical Name':<35} {'Type Code':<10}")
            print("-" * 80)
            
            for table in standard_tables[:20]:  # Show first 20
                display_name = table.get('DisplayName', {}).get('UserLocalizedLabel', {}).get('Label', 'N/A') if isinstance(table.get('DisplayName'), dict) else str(table.get('DisplayName', 'N/A'))
                logical_name = table.get('LogicalName', 'N/A')
                type_code = table.get('ObjectTypeCode', 'N/A')
                
                print(f"{display_name[:34]:<35} {logical_name[:34]:<35} {type_code:<10}")
            
            if len(standard_tables) > 20:
                print(f"... and {len(standard_tables) - 20} more standard tables")
            
            # Display custom tables
            print(f"\n🎨 CUSTOM TABLES ({len(custom_tables)}):")
            print("-" * 80)
            print(f"{'Display Name':<35} {'Logical Name':<35} {'Type Code':<10}")
            print("-" * 80)
            
            if custom_tables:
                for table in custom_tables:
                    display_name = table.get('DisplayName', {}).get('UserLocalizedLabel', {}).get('Label', 'N/A') if isinstance(table.get('DisplayName'), dict) else str(table.get('DisplayName', 'N/A'))
                    logical_name = table.get('LogicalName', 'N/A')
                    type_code = table.get('ObjectTypeCode', 'N/A')
                    
                    print(f"{display_name[:34]:<35} {logical_name[:34]:<35} {type_code:<10}")
            else:
                print("No custom tables found")
            
            # Common tables to look for
            print(f"\n💡 COMMONLY USED TABLES:")
            print("-" * 80)
            common = ['account', 'contact', 'lead', 'opportunity', 'incident', 'invoice', 'quote', 'salesorder']
            found_common = [t for t in tables if t.get('LogicalName') in common]
            
            for table in found_common:
                display_name = table.get('DisplayName', {}).get('UserLocalizedLabel', {}).get('Label', 'N/A') if isinstance(table.get('DisplayName'), dict) else str(table.get('DisplayName', 'N/A'))
                logical_name = table.get('LogicalName', 'N/A')
                print(f"  • {display_name}: {logical_name}")
            
            print(f"\n📝 Use these logical names in dataverse_config.py")
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error listing Dataverse tables: {e}")
        import traceback
        traceback.print_exc()


def test_dataverse_query(table_name="account"):
    """Test querying a specific Dataverse table."""
    print("\n" + "="*80)
    print(f"🧪 TESTING DATAVERSE QUERY: {table_name}")
    print("="*80)
    
    if not ENABLE_DATAVERSE or not DATAVERSE_ENVIRONMENT_URL:
        print("❌ Dataverse not configured")
        return
    
    try:
        credential = get_credential()
        token = credential.get_token(f"{DATAVERSE_ENVIRONMENT_URL}/.default")
        
        # Determine plural form
        endpoint = table_name + 's' if not table_name.endswith('s') else table_name
        
        url = f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }
        
        params = {"$top": 5}
        
        print(f"📡 GET {url}")
        print(f"   Params: {params}\n")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            records = result.get('value', [])
            
            print(f"✅ Found {len(records)} records\n")
            
            if records:
                # Show first record fields
                print("📋 Available fields in first record:")
                first_record = records[0]
                for key, value in first_record.items():
                    if not key.startswith('@') and not key.startswith('_'):
                        print(f"  • {key}: {str(value)[:60]}")
                
                print(f"\n📊 All {len(records)} records:")
                for i, record in enumerate(records, 1):
                    name = record.get('name') or record.get('fullname') or record.get(list(record.keys())[0] if record else 'N/A')
                    print(f"  {i}. {name}")
            else:
                print("ℹ️  Table exists but contains no records")
                
        elif response.status_code == 404:
            print(f"❌ Table '{table_name}' not found")
            print("💡 Try running with --list-tables to see available tables")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def list_sharepoint_sites():
    """List SharePoint sites accessible to the user."""
    print("\n" + "="*80)
    print("📄 SHAREPOINT SITES")
    print("="*80)
    
    try:
        credential = get_credential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        
        print("✅ Connected to Microsoft Graph")
        print(f"\n🔍 Fetching SharePoint sites...\n")
        
        # Get sites
        url = "https://graph.microsoft.com/v1.0/sites?search=*"
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            sites = result.get('value', [])
            
            print(f"📋 FOUND {len(sites)} SITES:")
            print("-" * 80)
            print(f"{'Site Name':<40} {'Web URL':<40}")
            print("-" * 80)
            
            for site in sites:
                name = site.get('displayName', 'N/A')
                web_url = site.get('webUrl', 'N/A')
                print(f"{name[:39]:<40} {web_url[:39]:<40}")
            
            if not sites:
                print("ℹ️  No SharePoint sites found")
                
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error listing SharePoint sites: {e}")


def list_onedrive_files():
    """List OneDrive root files."""
    print("\n" + "="*80)
    print("📁 ONEDRIVE FILES (Root)")
    print("="*80)
    
    try:
        credential = get_credential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        
        print("✅ Connected to Microsoft Graph")
        print(f"\n🔍 Fetching OneDrive files...\n")
        
        # Get OneDrive root items
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        params = {"$top": 20}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            items = result.get('value', [])
            
            print(f"📋 FOUND {len(items)} ITEMS:")
            print("-" * 80)
            print(f"{'Name':<40} {'Type':<15} {'Size':<15}")
            print("-" * 80)
            
            for item in items:
                name = item.get('name', 'N/A')
                item_type = 'Folder' if 'folder' in item else 'File'
                size = item.get('size', 0)
                size_str = f"{size:,} bytes" if size > 0 else "N/A"
                
                print(f"{name[:39]:<40} {item_type:<15} {size_str:<15}")
            
            if not items:
                print("ℹ️  OneDrive is empty")
                
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error listing OneDrive files: {e}")


def get_user_info():
    """Display current user information."""
    print("\n" + "="*80)
    print("👤 CURRENT USER")
    print("="*80)
    
    try:
        credential = get_credential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        
        url = "https://graph.microsoft.com/v1.0/me"
        headers = {
            "Authorization": f"Bearer {token.token}"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            user = response.json()
            
            print(f"Name: {user.get('displayName', 'N/A')}")
            print(f"Email: {user.get('mail') or user.get('userPrincipalName', 'N/A')}")
            print(f"ID: {user.get('id', 'N/A')}")
            print(f"Job Title: {user.get('jobTitle', 'N/A')}")
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error getting user info: {e}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔍 DATAVERSE & MICROSOFT 365 DIAGNOSTIC TOOL")
    print("="*80)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Diagnose Dataverse and Microsoft 365 connectivity')
    parser.add_argument('--list-tables', action='store_true', help='List all Dataverse tables')
    parser.add_argument('--test-table', type=str, help='Test querying a specific table (e.g., account, cr123_sales)')
    parser.add_argument('--list-sites', action='store_true', help='List SharePoint sites')
    parser.add_argument('--list-files', action='store_true', help='List OneDrive files')
    parser.add_argument('--all', action='store_true', help='Run all diagnostics')
    
    args = parser.parse_args()
    
    # Show user info first
    get_user_info()
    
    if args.all or (not any([args.list_tables, args.test_table, args.list_sites, args.list_files])):
        # Run all if no specific option or --all specified
        list_dataverse_tables()
        test_dataverse_query("account")
        list_sharepoint_sites()
        list_onedrive_files()
    else:
        if args.list_tables:
            list_dataverse_tables()
        
        if args.test_table:
            test_dataverse_query(args.test_table)
        
        if args.list_sites:
            list_sharepoint_sites()
        
        if args.list_files:
            list_onedrive_files()
    
    print("\n" + "="*80)
    print("✅ DIAGNOSTIC COMPLETE")
    print("="*80)
    print("\n💡 Next Steps:")
    print("  1. Copy the logical name of your sales table from the output above")
    print("  2. Edit agent/dataverse_config.py and add your table to DATAVERSE_TABLES")
    print("  3. Update SALES_TABLE_CONFIG with your table's actual field names")
    print("  4. Run: python main.py \"total sales for 2024\"\n")
