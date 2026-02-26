import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "kallogjeri-project-345114"

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
    
    col_url = f"{base_url}/v1alpha/projects/{PROJECT_ID}/locations/{loc}/collections"
    try:
        resp = requests.get(col_url, headers=headers)
        if resp.status_code == 200:
            cols_data = resp.json().get('collections', [])
            for c in cols_data:
                print(f"Collection: {c.get('name')}")
        else:
            print(f"Error: {resp.status_code}")
    except:
        pass
