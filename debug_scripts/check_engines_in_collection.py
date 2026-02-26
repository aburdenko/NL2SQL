import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "kallogjeri-project-345114"
COLLECTION_ID = "77110326-4e07-4373-a1a3-3ca3296d7101"

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
    
    url = f"{base_url}/v1alpha/projects/{PROJECT_ID}/locations/{loc}/collections/{COLLECTION_ID}/engines"
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            print(f"✅ Found engines in collection {COLLECTION_ID}!")
            engines_data = resp.json().get('engines', [])
            for eng in engines_data:
                print(f" - Engine ID: {eng.get('name').split('/')[-1]} | Display: {eng.get('displayName')}")
        else:
            print(f"   Status: {resp.status_code}")
    except Exception as e:
        print(f"   Exception: {e}")
