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
    
    # Use v1beta
    col_url = f"{base_url}/v1beta/projects/{PROJECT_ID}/locations/{loc}/collections"
    try:
        col_resp = requests.get(col_url, headers=headers)
        if col_resp.status_code == 200:
            collections_data = col_resp.json().get('collections', [])
            for col in collections_data:
                print(f"Collection: {col.get('name')}")
    except:
        pass
