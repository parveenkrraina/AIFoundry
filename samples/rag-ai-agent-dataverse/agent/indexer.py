"""
Simple Azure AI Search indexer for Dataverse tables.
- Pulls records from a specified Dataverse table (any table) using metadata-based endpoint resolution
- Transforms into search documents
- Uploads to Azure AI Search index

Usage (PowerShell):
  # Index top 100 records from 'account'
  $env:DATAVERSE_TABLE=account; python indexer.py

  # Override count and table inline
  python indexer.py account 200

Prereqs:
  - Set .env with DATAVERSE_* values and Azure Search settings
  - ENABLE_AZURE_SEARCH=true
"""
import os
import sys
import json
import math
from typing import List, Dict, Any
from dotenv import load_dotenv
import requests

from dataverse_client import get_dataverse_token, _get_entity_set_name, _heuristic_entity_set_name

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

DATAVERSE_ENVIRONMENT_URL = os.getenv("DATAVERSE_ENVIRONMENT_URL")

API_VERSION = os.getenv("AZURE_SEARCH_API_VERSION", "2023-11-01")


def _search_upload(docs: List[Dict[str, Any]]):
    if not (AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY and AZURE_SEARCH_INDEX):
        print("Azure Search not configured; skipping upload.")
        return
    url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{AZURE_SEARCH_INDEX}/docs/index?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_SEARCH_KEY,
    }
    payload = {"value": [{"@search.action": "mergeOrUpload", **d} for d in docs]}
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code >= 300:
        print(f"Upload failed: {resp.status_code} {resp.text[:200]}")
    else:
        print(f"Uploaded {len(docs)} docs")


def _fetch_dataverse(table: str, top: int = 100) -> List[Dict[str, Any]]:
    token = get_dataverse_token()
    if not token:
        print("No Dataverse token.")
        return []
    entityset = _get_entity_set_name(table) or _heuristic_entity_set_name(table)
    url = f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/{entityset}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Prefer": "odata.maxpagesize=50"
    }
    results: List[Dict[str, Any]] = []
    skip = 0
    while len(results) < top:
        params = {"$top": min(50, top - len(results)), "$skip": skip}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"Fetch error: {resp.status_code} {resp.text[:200]}")
            break
        data = resp.json() or {}
        batch = data.get("value") or []
        if not batch:
            break
        results.extend(batch)
        skip += len(batch)
    return results[:top]


def _to_search_docs(table: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for r in rows:
        # Build id from primary keys if present, else fallback to hash of content
        rid = r.get(f"{table}id") or r.get("activityid") or r.get("id") or str(abs(hash(json.dumps(r, sort_keys=True))) )
        # Derive a short title/name for search results
        title = r.get("name") or r.get("fullname") or r.get("subject") or r.get("title") or table
        # Aggregate content into a single searchable text field
        # Keep it light; Azure Search can support vector fields if you extend this pipeline
        content_parts = []
        for k, v in r.items():
            if isinstance(v, str) and v:
                content_parts.append(f"{k}: {v}")
        content = "\n".join(content_parts)[:4000]
        docs.append({
            "id": f"{table}-{rid}",
            "table": table,
            "title": title,
            "content": content,
        })
    return docs


def main():
    table = None
    top = 100
    if len(sys.argv) >= 2:
        table = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            top = int(sys.argv[2])
        except Exception:
            pass
    if not table:
        table = os.getenv("DATAVERSE_TABLE", "account")

    print(f"Indexing table '{table}' (top {top}) → Azure AI Search index '{AZURE_SEARCH_INDEX}'")
    rows = _fetch_dataverse(table, top=top)
    print(f"Fetched {len(rows)} rows")
    docs = _to_search_docs(table, rows)
    _search_upload(docs)


if __name__ == "__main__":
    main()
