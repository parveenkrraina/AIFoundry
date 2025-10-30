"""
Dataverse Client for RAG Agent
Dataverse-only context retrieval with metadata-driven queries and aggregates.
"""
import os
import re
from typing import Optional, Tuple, List, Dict, Any
import requests
from dotenv import load_dotenv
from azure.identity import InteractiveBrowserCredential, DeviceCodeCredential, DefaultAzureCredential

# Load environment variables
load_dotenv()

# Try to load custom table configuration
try:
    from dataverse_config import DATAVERSE_TABLES, SALES_TABLE_CONFIG
except ImportError:
    # Default configuration if dataverse_config.py doesn't exist
    DATAVERSE_TABLES = ['account', 'contact', 'annotation']
    SALES_TABLE_CONFIG = None

AUTH_METHOD = os.getenv("GRAPH_AUTH_METHOD", "interactive")  # interactive, device_code, or default

# Dataverse configuration
DATAVERSE_ENVIRONMENT_URL = os.getenv("DATAVERSE_ENVIRONMENT_URL")
DATAVERSE_CLIENT_ID = os.getenv("DATAVERSE_CLIENT_ID")
DATAVERSE_TENANT_ID = os.getenv("DATAVERSE_TENANT_ID", "common")
ENABLE_DATAVERSE = os.getenv("ENABLE_DATAVERSE", "false").lower() == "true"
ENABLE_SALES_ADVANCED = os.getenv("ENABLE_SALES_ADVANCED", "false").lower() == "true"

# Dataverse scope
DATAVERSE_SCOPES = [f"{DATAVERSE_ENVIRONMENT_URL}/.default"]

# Global credential
_credential = None
_dataverse_token = None
_entity_definitions_cache: Dict[str, Dict[str, Any]] = {}
_entity_set_name_cache: Dict[str, str] = {}


# Note: Graph access removed for clean Dataverse-only version.


def get_dataverse_token():
    """
    Get access token for Dataverse API.
    Uses cached credential to avoid repeated authentication.
    
    Returns:
        str: Access token
    """
    global _credential, _dataverse_token
    
    if not ENABLE_DATAVERSE:
        return None
    
    if not DATAVERSE_ENVIRONMENT_URL:
        print("Warning: DATAVERSE_ENVIRONMENT_URL not configured")
        return None
    
    try:
        # Reuse credential from Graph API authentication if available
        if _credential is None:
            if AUTH_METHOD == "device_code":
                print("\n🔐 Authenticating with device code flow (Dataverse)...")
                _credential = DeviceCodeCredential(
                    client_id=DATAVERSE_CLIENT_ID,
                    tenant_id=DATAVERSE_TENANT_ID
                )
            elif AUTH_METHOD == "interactive":
                print("\n🔐 Authenticating with interactive browser (Dataverse)...")
                _credential = InteractiveBrowserCredential(
                    client_id=DATAVERSE_CLIENT_ID,
                    tenant_id=DATAVERSE_TENANT_ID
                )
            else:
                print("\n🔐 Using default Azure credential (Dataverse)...")
                _credential = DefaultAzureCredential()
        
        # Get token for Dataverse (credential handles caching)
        token = _credential.get_token(f"{DATAVERSE_ENVIRONMENT_URL}/.default")
        _dataverse_token = token.token
        
        if _credential and _dataverse_token:
            print("✅ Successfully authenticated with Dataverse")
        
        return _dataverse_token
        
    except Exception as e:
        print(f"Warning: Could not authenticate with Dataverse: {e}")
        return None


def search_dataverse_tables(query, max_results=5, table_names=None):
    """
    Search Dataverse tables for relevant records.
    Now includes smart field detection and aggregation support.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results
        table_names (list): List of table logical names to search (e.g., ['account', 'contact', 'cr123_sales'])
        
    Returns:
        str: Combined context from Dataverse records
    """
    if not ENABLE_DATAVERSE:
        return ""
    
    try:
        token = get_dataverse_token()
        if not token:
            return ""

        # If the query explicitly names a table (e.g., "from cr5cd_sales" or "table account"), prioritize it
        explicit_table = _extract_table_name_from_query(query or "")
        search_term = _extract_search_term(query or "")

        # Use tables from config file if available, otherwise use defaults
        if table_names is None:
            table_names = [explicit_table] if explicit_table else DATAVERSE_TABLES
        
        context_parts = []
        
        for table_name in table_names:
            try:
                # If the user asked for an aggregate (sum/avg/count), try generic $apply aggregation first
                agg_intent = _parse_aggregate_intent(query, table_name)
                if agg_intent:
                    op, field, year = agg_intent
                    agg_summary = _dataverse_aggregate(table_name, op, field, year)
                    if agg_summary:
                        context_parts.append(agg_summary)
                        # When explicit aggregate is fulfilled for an explicit table, continue to next table
                        if explicit_table:
                            continue
                # Resolve the entity set name (robust for ANY table)
                endpoint = _get_entity_set_name(table_name) or _heuristic_entity_set_name(table_name)
                
                # Use Dataverse Web API
                url = f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/{endpoint}"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "OData-MaxVersion": "4.0",
                    "OData-Version": "4.0",
                    "Prefer": "odata.include-annotations=*"
                }
                
                # Build parameters based on table type
                params = {
                    "$top": max_results
                }
                
                # Table-specific field selection and filters
                if table_name == 'account':
                    params["$select"] = "name,description,revenue,createdon"
                    if search_term:
                        params["$filter"] = f"contains(name,'{search_term}')"
                elif table_name == 'contact':
                    params["$select"] = "fullname,emailaddress1,jobtitle,createdon"
                    if search_term:
                        params["$filter"] = f"contains(fullname,'{search_term}') or contains(emailaddress1,'{search_term}')"
                elif table_name == 'cr5cd_sales' and ENABLE_SALES_ADVANCED:
                    # Your specific sales table with actual field names
                    params["$select"] = "cr5cd_itemname,cr5cd_salesordernumber,cr5cd_customerid"
                    params["$select"] += ",cr5cd_unitprice,cr5cd_quantityordered,cr5cd_taxamount"
                    params["$select"] += ",cr5cd_orderdate,createdon"
                    
                    # Filter by year in orderdate if query mentions a year
                    if query and any(year in query for year in ['2024', '2023', '2025', '2026']):
                        for year in ['2024', '2023', '2025', '2026']:
                            if year in query:
                                # Filter by order date year
                                params["$filter"] = f"Microsoft.Dynamics.CRM.Between(PropertyName='cr5cd_orderdate',PropertyValues=['{year}-01-01','{year}-12-31'])"
                                break
                elif 'sales' in table_name.lower():
                    # Generic sales table handling
                    params["$select"] = "name,createdon"
                    params["$select"] += ",cr123_amount,cr123_salesamount,cr123_totalamount,salesamount,totalamount,amount"
                    params["$select"] += ",cr123_date,cr123_salesdate,salesdate,transactiondate"
                    params["$select"] += ",cr123_product,cr123_productname,productname"
                    
                    # Check if query mentions years for filtering
                    if query and any(year in query for year in ['2024', '2023', '2025']):
                        for year in ['2024', '2023', '2025']:
                            if year in query:
                                params["$filter"] = f"Microsoft.Dynamics.CRM.Between(PropertyName='createdon',PropertyValues=['{year}-01-01','{year}-12-31'])"
                                break
                else:
                    # Generic approach for any other table
                    # Try to filter by year on createdon if year mentioned
                    year = _extract_year_from_query(query)
                    if year:
                        params["$filter"] = (
                            f"Microsoft.Dynamics.CRM.Between(PropertyName='createdon',"
                            f"PropertyValues=['{year}-01-01','{year}-12-31'])"
                        )
                    # Otherwise, if a plain term query is provided, try contains on common text fields
                    elif search_term:
                        # We can't know field names up-front; most tables have 'name' or 'subject' or 'title'
                        # Use $filter with or-chain; fields not present are ignored by the service, so we try common ones.
                        params["$filter"] = (
                            f"contains(name,'{search_term}') or contains(subject,'{search_term}') or contains(title,'{search_term}')"
                        )
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('value'):
                        records = result['value'][:max_results]
                        
                        # Special handling for cr5cd_sales table (optional)
                        if table_name == 'cr5cd_sales' and ENABLE_SALES_ADVANCED and records:
                            total_revenue = 0
                            total_tax = 0
                            total_items = 0
                            
                            # Calculate totals from all records
                            for record in records:
                                unit_price = float(record.get('cr5cd_unitprice', 0) or 0)
                                quantity = int(record.get('cr5cd_quantityordered', 0) or 0)
                                tax = float(record.get('cr5cd_taxamount', 0) or 0)
                                
                                line_total = unit_price * quantity
                                total_revenue += line_total
                                total_tax += tax
                                total_items += quantity
                            
                            total_with_tax = total_revenue + total_tax
                            
                            # Add summary with totals
                            context_parts.append(f"[Sales Summary] Total Revenue: ${total_revenue:,.2f} + Tax: ${total_tax:,.2f} = ${total_with_tax:,.2f}")
                            context_parts.append(f"[Sales Summary] Total Items Sold: {total_items} across {len(records)} orders")
                            
                            # Add sample records
                            context_parts.append(f"\nSample Orders:")
                            for i, record in enumerate(records[:5], 1):
                                item_name = record.get('cr5cd_itemname', 'Unknown')
                                order_num = record.get('cr5cd_salesordernumber', 'N/A')
                                unit_price = float(record.get('cr5cd_unitprice', 0) or 0)
                                quantity = int(record.get('cr5cd_quantityordered', 0) or 0)
                                order_date = record.get('cr5cd_orderdate', '')[:10] if record.get('cr5cd_orderdate') else 'N/A'
                                line_total = unit_price * quantity
                                
                                context_parts.append(f"  {i}. Order {order_num}: {item_name} x{quantity} = ${line_total:,.2f} (Date: {order_date})")
                        
                        # Generic sales table handling
                        elif 'sales' in table_name.lower() and records:
                            total_amount = 0
                            amount_field = None
                            
                            # Find which amount field exists
                            for field in ['cr123_amount', 'cr123_salesamount', 'cr123_totalamount', 
                                         'salesamount', 'totalamount', 'amount']:
                                if field in records[0]:
                                    amount_field = field
                                    break
                            
                            # Calculate total
                            if amount_field:
                                for record in records:
                                    amount = record.get(amount_field, 0)
                                    if amount:
                                        total_amount += float(amount)
                                
                                # Add summary with total
                                context_parts.append(f"[{table_name}] Total Sales: ${total_amount:,.2f} ({len(records)} records)")
                                
                                # Add individual records
                                for record in records[:3]:  # Show first 3 records
                                    name = record.get('name', 'Sale')
                                    amount = record.get(amount_field, 0)
                                    date = record.get('createdon', '')[:10] if record.get('createdon') else ''
                                    context_parts.append(f"  - {name}: ${float(amount):,.2f} on {date}")
                            else:
                                # No amount field found, just list records
                                for record in records:
                                    name = record.get('name', 'Unnamed')
                                    context_parts.append(f"[{table_name}] {name}")
                        else:
                            # Generic ANY-table handling
                            summary = _summarize_generic_records(table_name, records)
                            context_parts.append(summary)
                    else:
                        print(f"No records found in {table_name}")
                
                elif response.status_code == 404:
                    print(f"Warning: Table '{table_name}' not found. Check the table logical name.")
                else:
                    print(f"Warning: Could not search {table_name}: HTTP {response.status_code}")
                    if response.status_code == 401:
                        print("  → Authentication failed. Check Dataverse permissions.")
                
            except Exception as table_error:
                print(f"Warning: Could not search {table_name}: {table_error}")
                continue
        
        if not context_parts:
            return "No relevant records found in Dataverse."

        return "\n".join(context_parts)

    except Exception as e:
        print(f"Error searching Dataverse: {e}")
        return ""


# -----------------------------
# Dataverse metadata utilities
# -----------------------------

def _extract_table_name_from_query(query: str) -> Optional[str]:
    """
    Extract an explicit table name from a natural language query.
    Prefer patterns like:
      - "table <name>" or "table named <name>"
      - "from <name>"
      - "in table <name>"

    Avoid capturing stopwords like 'the', 'a', 'an' from phrases like 'in the table sales'.
    """
    if not query:
        return None

    stopwords = {"the", "a", "an", "this", "that", "my"}

    # Highest priority: "table <name>" (with optional "named")
    m = re.search(r"\btable\s+(?:named\s+)?([A-Za-z0-9_]+)\b", query, flags=re.IGNORECASE)
    if m:
        cand = m.group(1)
        if cand.lower() not in stopwords:
            return cand

    # Next: "from <name>"
    m = re.search(r"\bfrom\s+([A-Za-z0-9_]+)\b", query, flags=re.IGNORECASE)
    if m:
        cand = m.group(1)
        if cand.lower() not in stopwords:
            return cand

    # Next: "in table <name>"
    m = re.search(r"\bin\s+table\s+([A-Za-z0-9_]+)\b", query, flags=re.IGNORECASE)
    if m:
        cand = m.group(1)
        if cand.lower() not in stopwords:
            return cand

    return None


def _extract_year_from_query(query: Optional[str]) -> Optional[str]:
    if not query:
        return None
    m = re.search(r"\b(20[0-9]{2})\b", query)
    return m.group(1) if m else None


def _extract_search_term(query: str) -> str:
    """Return a cleaned search term by stripping control phrases and table mentions."""
    if not query:
        return ""
    cleaned = query
    # Remove table mention phrases (ordered to avoid capturing 'the')
    cleaned = re.sub(r"\bin\s+table\s+[A-Za-z0-9_]+\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\btable\s+(?:named\s+)?[A-Za-z0-9_]+\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bfrom\s+[A-Za-z0-9_]+\b", " ", cleaned, flags=re.IGNORECASE)
    # Remove common control words
    control_words = [
        "show", "list", "records", "entries", "items", "get", "find", "display", "top", "all"
    ]
    cleaned = re.sub(r"\b(" + "|".join(control_words) + r")\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # If the remaining term is too short or contains only digits like a year, let year logic handle it
    return cleaned if len(cleaned) >= 3 and not re.fullmatch(r"\d{4}", cleaned) else ""


def _get_entity_set_name(table_name: str) -> Optional[str]:
    """
    Resolve the Entity Set Name (collection endpoint) for a Dataverse table using metadata.
    Returns None if not found.
    """
    if not table_name:
        return None
    key = table_name.lower()
    if key in _entity_set_name_cache:
        return _entity_set_name_cache[key]

    token = _dataverse_token or get_dataverse_token()
    if not token:
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }

    # First try exact logical name lookup
    url_exact = f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/EntityDefinitions(LogicalName='{table_name}')?$select=LogicalName,EntitySetName,SchemaName"
    try:
        resp = requests.get(url_exact, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            entity_set = data.get("EntitySetName")
            if entity_set:
                _entity_set_name_cache[key] = entity_set
                return entity_set
    except Exception:
        pass

    # Fallback: search by contains on logical/schema names
    try:
        url_search = (
            f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/EntityDefinitions?"
            f"$select=LogicalName,EntitySetName,SchemaName&$filter="
            f"contains(tolower(LogicalName),'{table_name.lower()}') or contains(tolower(SchemaName),'{table_name.lower()}')"
        )
        resp2 = requests.get(url_search, headers=headers, timeout=30)
        if resp2.status_code == 200:
            data = resp2.json() or {}
            for ent in (data.get("value") or []):
                entity_set = ent.get("EntitySetName")
                logical_name = (ent.get("LogicalName") or "").lower()
                if entity_set and (logical_name == key or key in logical_name):
                    _entity_set_name_cache[key] = entity_set
                    return entity_set
    except Exception:
        pass

    return None


def _heuristic_entity_set_name(table_name: str) -> str:
    """Best-effort pluralization if metadata not available."""
    if table_name == 'cr5cd_sales':
        return 'cr5cd_saleses'
    if table_name.endswith('s'):
        return table_name + 'es'
    return table_name + 's'


def _summarize_generic_records(table_name: str, records: List[Dict[str, Any]]) -> str:
    """
    Build a lightweight, readable summary for arbitrary table records:
    - Shows a few key fields if present
    - If numeric fields like amount/total/price/quantity exist, computes quick aggregates
    """
    if not records:
        return f"[{table_name}] No records found."

    # Heuristics: pick human-friendly title
    lines: List[str] = []
    numeric_totals: Dict[str, float] = {}

    # Determine candidate key fields to display
    key_fields = [
        'name', 'fullname', 'subject', 'title', 'cr5cd_itemname', 'description'
    ]
    date_fields = ['cr5cd_orderdate', 'createdon', 'modifiedon', 'overriddencreatedon']
    numeric_hints = ['amount', 'total', 'price', 'revenue', 'quantity', 'unit', 'linetotal', 'extendedamount']

    # Compute quick aggregates and assemble sample lines
    for i, rec in enumerate(records[:5], 1):
        display = None
        for k in key_fields:
            if k in rec and rec.get(k):
                display = f"{rec.get(k)}"
                break
        if not display:
            # fallback to first two string-like fields
            display = _first_stringy(rec)

        date_val = None
        for d in date_fields:
            if rec.get(d):
                date_val = str(rec.get(d))[:10]
                break

        # Tally numeric fields
        for field, val in rec.items():
            if isinstance(val, (int, float)) and any(h in field.lower() for h in numeric_hints):
                numeric_totals[field] = numeric_totals.get(field, 0.0) + float(val)

        if date_val:
            lines.append(f"  - {display} ({date_val})")
        else:
            lines.append(f"  - {display}")

    # Build header summary
    header = f"[{table_name}] {len(records)} record(s)"
    if numeric_totals:
        # Show up to two aggregate totals
        agg_parts = []
        for k, v in list(numeric_totals.items())[:2]:
            agg_parts.append(f"{k}: {v:,.2f}")
        header += " | totals → " + ", ".join(agg_parts)

    return "\n".join([header] + lines)


def _first_stringy(rec: Dict[str, Any]) -> str:
    """Return a concatenation of first two short stringish fields for display."""
    parts: List[str] = []
    for k, v in rec.items():
        if isinstance(v, str) and 1 <= len(v) <= 60:
            parts.append(v)
            if len(parts) >= 2:
                break
    return " - ".join(parts) if parts else "Record"


# -----------------------------
# Generic aggregation utilities
# -----------------------------

def _get_numeric_attributes(table_name: str) -> List[str]:
    """Return a list of numeric attribute logical names for a table via metadata."""
    token = _dataverse_token or get_dataverse_token()
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }

    url = (
        f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/EntityDefinitions(LogicalName='{table_name}')/Attributes"
        f"?$select=LogicalName,AttributeType"
    )
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json() or {}
        numeric_types = {"Integer", "BigInt", "Double", "Decimal", "Money"}
        attrs: List[str] = []
        for a in (data.get("value") or []):
            if (a.get("AttributeType") in numeric_types) and a.get("LogicalName"):
                attrs.append(a["LogicalName"])
        return attrs
    except Exception:
        return []


def _parse_aggregate_intent(query: Optional[str], table_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    """
    Parse a simple aggregate intent from the query: sum/total, avg/average, count.
    Returns tuple: (op, field, year) where op in {"sum","avg","count"}
    field is chosen by keyword match over numeric attributes; fallback to first numeric attribute.
    """
    if not query:
        return None

    q = query.lower()
    op: Optional[str] = None
    if re.search(r"\b(count|how many)\b", q):
        op = "count"
    elif re.search(r"\b(total|sum)\b", q):
        op = "sum"
    elif re.search(r"\b(avg|average|mean)\b", q):
        op = "avg"
    elif re.search(r"\b(max|maxi?mum|highest|top)\b", q):
        op = "max"
    elif re.search(r"\b(min|mini?mum|lowest)\b", q):
        op = "min"
    if not op:
        return None

    year = _extract_year_from_query(query)

    numeric_attrs = _get_numeric_attributes(table_name)
    if not numeric_attrs:
        # No metadata available
        if op == "count":
            return (op, "", year)
        return None

    # Prefer fields that hint amount/total/price/quantity/revenue
    hints = ["amount", "total", "price", "quantity", "revenue"]
    chosen = None
    for na in numeric_attrs:
        if any(h in na.lower() for h in hints):
            chosen = na
            break
    if not chosen:
        chosen = numeric_attrs[0]

    return (op, chosen, year)


def _dataverse_aggregate(table_name: str, op: str, field: str, year: Optional[str]) -> Optional[str]:
    """Execute a generic aggregate via $apply and return a human summary string."""
    token = _dataverse_token or get_dataverse_token()
    if not token:
        return None
    entityset = _get_entity_set_name(table_name) or _heuristic_entity_set_name(table_name)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }

    # Choose a date field for year scoping: prefer domain-specific dates, else createdon
    date_field = _choose_date_field(table_name)
    filter_seg = ""
    if year and date_field:
        filter_seg = (
            f"filter({date_field} ge {year}-01-01 and {date_field} le {year}-12-31)/"
        )

    if op == "count":
        apply = f"$apply={filter_seg}aggregate($count as Count)"
    else:
        # sum or avg over a numeric field
        apply = f"$apply={filter_seg}aggregate({field} with {op} as Result)"

    url = f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/{entityset}?{apply}"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return None
        data = resp.json() or {}
        vals = data.get("value") or []
        if not vals:
            return None
        rec = vals[0]
        if op == "count":
            count = rec.get("Count") or rec.get("$count") or 0
            scope = f" in {year}" if year else ""
            return f"[{table_name}] Count{scope}: {int(count)}"
        else:
            result = rec.get("Result")
            scope = f" in {year}" if year else ""
            return f"[{table_name}] {op.upper()} of {field}{scope}: {float(result):,.2f}"
    except Exception:
        return None


def _get_date_attributes(table_name: str) -> List[str]:
    token = _dataverse_token or get_dataverse_token()
    if not token:
        return []
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    url = (
        f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/EntityDefinitions(LogicalName='{table_name}')/Attributes"
        f"?$select=LogicalName,AttributeType"
    )
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json() or {}
        date_types = {"DateTime"}
        attrs: List[str] = []
        for a in (data.get("value") or []):
            if (a.get("AttributeType") in date_types) and a.get("LogicalName"):
                attrs.append(a["LogicalName"])
        return attrs
    except Exception:
        return []


def _choose_date_field(table_name: str) -> Optional[str]:
    # Prefer common domain fields
    preferred = ["cr5cd_orderdate", "orderdate", "actualclosedate", "estimatedclosedate", "createdon"]
    available = set(_get_date_attributes(table_name))
    for p in preferred:
        if p in available:
            return p
    # Fallback to createdon if present
    return "createdon" if "createdon" in available else None


# SharePoint/OneDrive/OneNote search removed for clean Dataverse-only version.


 


 


def get_context_from_dataverse(query, max_results=5):
    """
    Retrieve relevant context from Dataverse tables only.
    
    Args:
        query (str): User's search query
        max_results (int): Maximum number of records to retrieve
        
    Returns:
        str: Combined context from retrieved records
    """
    print(f"🔍 Searching Dataverse for: '{query}'")
    
    context_parts = []
    
    # Search Dataverse tables (if enabled)
    if ENABLE_DATAVERSE:
        dataverse_context = search_dataverse_tables(query, max_results)
        if dataverse_context and "No relevant" not in dataverse_context:
            context_parts.append("💾 Dataverse Records:\n" + dataverse_context)
    
    if not context_parts:
        return "No relevant context found in Dataverse."
    
    return "\n\n".join(context_parts)


def search_dataverse_semantic(query):
    """
    Advanced semantic search (placeholder for future enhancement).
    Currently returns the same as get_context_from_dataverse.
    
    Args:
        query (str): User's search query
        
    Returns:
        str: Retrieved context
    """
    return get_context_from_dataverse(query)


# User info via Graph removed in Dataverse-only version.


if __name__ == "__main__":
    # Simple Dataverse connectivity test
    print("Testing Dataverse client...")
    
    try:
        # Test search
        test_query = "account"
        print(f"\nTesting search for: {test_query}")
        context = get_context_from_dataverse(test_query)
        print(f"\nRetrieved context:\n{context}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Set DATAVERSE_* variables in .env file")
        print("2. Registered an Azure AD app with Dataverse user_impersonation permission")
        print("3. Granted admin consent if required")
