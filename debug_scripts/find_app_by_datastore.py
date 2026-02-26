import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "kallogjeri-project-345114"
DATA_STORE_ID = "claims-data_1762979629917"

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": PROJECT_ID
}

locations = ["global", "us"]

for loc in locations:
    print(f"\n--- Location: {loc} ---")
    if loc == "global":
        base_url = "https://discoveryengine.googleapis.com"
    else:
        base_url = f"https://{loc}-discoveryengine.googleapis.com"
    
    eng_url = f"{base_url}/v1alpha/projects/{PROJECT_ID}/locations/{loc}/collections/default_collection/engines"
    try:
        resp = requests.get(eng_url, headers=headers)
        if resp.status_code == 200:
            engines_data = resp.json().get('engines', [])
            for eng in engines_data:
                # Check data stores for this engine
                ds_url = f"{base_url}/v1alpha/{eng.get('name')}/dataStores"
                ds_resp = requests.get(ds_url, headers=headers)
                if ds_resp.status_code == 200:
                    data_stores = ds_resp.json().get('dataStores', [])
                    for ds in data_stores:
                        if DATA_STORE_ID in ds.get('name'):
                            print(f"✅ Found Data Store {DATA_STORE_ID} in Engine: {eng.get('displayName')} ({eng.get('name').split('/')[-1]})")
    except:
        pass
