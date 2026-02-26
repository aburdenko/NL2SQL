
import os
import requests
import google.auth
from google.auth.transport.requests import Request
import json

PROJECT_ID = "kallogjeri-project-345114"
ENGINE_ID = "nl2sql-agent-app-central1"

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": PROJECT_ID
}

# ... (imports and auth same as before) ...

# Try to create default_collection in us-central1 using US multiregion endpoint
url_collection = f"https://us-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/us-central1/collections"
params_collection = {"collectionId": "default_collection"}
payload_collection = {"displayName": "Default Collection"}

print("Creating 'default_collection' in us-central1 (via us-discoveryengine)...")
try:
    resp = requests.post(url_collection, headers=headers, params=params_collection, json=payload_collection)
    print(f"Collection Status: {resp.status_code}")
    print(resp.text)
except Exception as e:
    print(f"Collection Exception: {e}")

# Create Data Store in 'us' multiregion
url_ds = f"https://us-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/us/collections/default_collection/dataStores"
params_ds = {"dataStoreId": "nl2sql-dummy-ds"}
payload_ds = {
    "displayName": "NL2SQL Dummy Data Store",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_CHAT"],
    "contentConfig": "NO_CONTENT" # Use NO_CONTENT for empty data store
}

print("Creating Data Store 'nl2sql-dummy-ds' in us multiregion...")
try:
    resp = requests.post(url_ds, headers=headers, params=params_ds, json=payload_ds)
    print(f"Data Store Status: {resp.status_code}")
    print(resp.text)
except Exception as e:
    print(f"Data Store Exception: {e}")

# Create Engine in 'us' multiregion
url = f"https://us-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/us/collections/default_collection/engines"
params = {"engineId": "nl2sql-agent-app-us"}

payload = {
    "displayName": "NL2SQL Agent App (US)",
    "solutionType": "SOLUTION_TYPE_CHAT",
    "commonConfig": {
        "companyName": "NL2SQL Demo"
    },
    "chatEngineConfig": {
        "agentCreationConfig": {
            "business": "NL2SQL Demo",
            "defaultLanguageCode": "en",
            "timeZone": "America/Los_Angeles"
        }
    },
    "dataStoreIds": ["nl2sql-dummy-ds"]
}

print("Creating Engine 'nl2sql-agent-app-us' in us multiregion...")
try:
    resp = requests.post(url, headers=headers, params=params, json=payload)
    print(f"Status: {resp.status_code}")
    print(resp.text)
    
    if resp.status_code == 200:
        print("✅ Engine creation initiated/completed.")
        print(f"Engine ID: nl2sql-agent-app-us")
except Exception as e:
    print(f"Exception: {e}")
