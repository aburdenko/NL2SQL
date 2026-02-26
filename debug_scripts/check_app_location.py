
import os
import requests
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account

# Hardcoded values from the notebook context
PROJECT_ID = "kallogjeri-project-345114"
APP_ID = "77110326-4e07-4373-a1a3-3ca3296d7101"

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": PROJECT_ID
}

locations = ["global", "us-central1"]

print(f"Listing all engines in project {PROJECT_ID}")

for loc in locations:
    print(f"\n--- Listing {loc} ---")
    if loc == "global":
        base_url = "https://discoveryengine.googleapis.com"
    else:
        # Correct endpoint for us-central1 seems to be us-discoveryengine
        base_url = f"https://us-discoveryengine.googleapis.com"
    
    url = f"{base_url}/v1alpha/projects/{PROJECT_ID}/locations/{loc}/collections/default_collection/engines"
    
    try:
        resp = requests.get(url, headers=headers)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            engines = resp.json().get('engines', [])
            print(f"Found {len(engines)} engines:")
            for e in engines:
                print(f" - Name: {e.get('name')}")
                print(f"   Display Name: {e.get('displayName')}")
                print(f"   ID: {e.get('name', '').split('/')[-1]}")
        else:
            print(f"Error listing in {loc}")
            print(resp.text[:200])
    except Exception as e:
        print(f"Exception: {e}")
