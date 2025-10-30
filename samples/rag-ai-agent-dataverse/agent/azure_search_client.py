"""
Minimal Azure AI Search client for hybrid/keyword retrieval.
Configure via environment variables:
- AZURE_SEARCH_ENDPOINT
- AZURE_SEARCH_KEY
- AZURE_SEARCH_INDEX
- ENABLE_AZURE_SEARCH=true
"""
import os
import requests
from typing import List

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
ENABLE_AZURE_SEARCH = os.getenv("ENABLE_AZURE_SEARCH", "false").lower() == "true"

API_VERSION = os.getenv("AZURE_SEARCH_API_VERSION", "2023-11-01")


def search(query: str, top: int = 5) -> List[str]:
    if not ENABLE_AZURE_SEARCH:
        return []
    if not (AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY and AZURE_SEARCH_INDEX):
        return []

    url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{AZURE_SEARCH_INDEX}/docs"
    params = {
        "api-version": API_VERSION,
        "search": query,
        "$top": top,
    }
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_SEARCH_KEY,
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json() or {}
        values = data.get("value") or []
        results: List[str] = []
        for v in values:
            # Heuristically use content fields commonly used in RAG pipelines
            title = v.get("title") or v.get("metadata_title") or v.get("name") or "Document"
            snippet = v.get("content") or v.get("chunk") or v.get("text") or ""
            if snippet and len(snippet) > 300:
                snippet = snippet[:300] + "..."
            results.append(f"{title}: {snippet}")
        return results
    except Exception:
        return []
