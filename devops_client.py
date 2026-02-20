import os
import time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv


# ======================================================
# Load environment variables
# ======================================================

load_dotenv()

ORG = os.getenv("AZURE_ORG")
PROJECT = os.getenv("AZURE_PROJECT")
PAT = os.getenv("AZURE_PAT")

if not ORG or not PROJECT or not PAT:
    raise Exception("❌ Missing AZURE_ORG / AZURE_PROJECT / AZURE_PAT in .env")

BASE = f"https://dev.azure.com/{ORG}/{PROJECT}"
AUTH = HTTPBasicAuth("", PAT)

API_VERSION = "7.0"
TIMEOUT = 30
MAX_RETRIES = 3


# ======================================================
# Core Request Handler (with retry logic)
# ======================================================

def _request(method, url, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.request(
                method,
                url,
                auth=AUTH,
                timeout=TIMEOUT,
                **kwargs
            )

            # Retry on throttling or server errors
            if response.status_code in (429, 500, 502, 503, 504):
                print(f"⚠ Retry {attempt}/{MAX_RETRIES} due to {response.status_code}")
                time.sleep(2 * attempt)
                continue

            if not response.ok:
                raise Exception(
                    f"\n❌ Azure DevOps API Error\n"
                    f"URL: {url}\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text[:500]}"
                )

            return response.json()

        except Exception as e:
            if attempt == MAX_RETRIES:
                raise e
            time.sleep(2 * attempt)

    raise Exception("❌ Azure DevOps request failed after retries")


# ======================================================
# GET helper
# ======================================================

def _get_json(url):
    return _request("GET", url)


# ======================================================
# POST helper
# ======================================================

def _post_json(url, body):
    return _request(
        "POST",
        url,
        headers={"Content-Type": "application/json"},
        json=body
    )


# ======================================================
# PATCH helper
# ======================================================

def _patch_json(url, body):
    return _request(
        "PATCH",
        url,
        headers={"Content-Type": "application/json-patch+json"},
        json=body
    )


# ======================================================
# Execute Saved Query → Return Story IDs
# ======================================================

def get_story_ids(query_id):
    """
    Executes saved Azure DevOps query:
    1) Fetch WIQL
    2) Execute WIQL
    """

    print(f"\n🔍 Running query: {query_id}")

    # Step 1 — Fetch WIQL
    query_url = f"{BASE}/_apis/wit/queries/{query_id}?$expand=wiql&api-version={API_VERSION}"
    query_data = _get_json(query_url)

    wiql_data = query_data.get("wiql")

    if isinstance(wiql_data, str):
        wiql = wiql_data
    else:
        wiql = wiql_data.get("query")

    if not wiql:
        raise Exception("❌ Could not extract WIQL from query")

    # Step 2 — Execute WIQL
    wiql_url = f"{BASE}/_apis/wit/wiql?api-version={API_VERSION}"
    result = _post_json(wiql_url, {"query": wiql})

    ids = [w["id"] for w in result.get("workItems", [])]

    print(f"✅ Found {len(ids)} work items")

    return ids


# ======================================================
# Get Single Work Item (legacy support)
# ======================================================

def get_work_item(id):
    url = f"{BASE}/_apis/wit/workitems/{id}?$expand=relations&api-version={API_VERSION}"
    return _get_json(url)


# ======================================================
# 🚀 Batch Fetch Work Items (Recommended)
# ======================================================

def get_work_items_batch(ids, expand_relations=True):
    """
    Fetch multiple work items in one request.
    Much faster than individual calls.
    """

    if not ids:
        return []

    url = f"{BASE}/_apis/wit/workitemsbatch?api-version={API_VERSION}"

    body = {
        "ids": ids,
        "$expand": "relations" if expand_relations else "none"
    }

    response = _post_json(url, body)

    return response.get("value", [])


# ======================================================
# Update Work Item Fields
# ======================================================

def update_work_item(id, fields):
    """
    Updates work item fields via PATCH
    """

    url = f"{BASE}/_apis/wit/workitems/{id}?api-version={API_VERSION}"

    patch_body = [
        {
            "op": "add",
            "path": f"/fields/{k}",
            "value": v
        }
        for k, v in fields.items()
    ]

    try:
        _patch_json(url, patch_body)
        print(f"✔ Updated work item {id}")
    except Exception as e:
        print(f"❌ Update failed for {id}: {e}")
