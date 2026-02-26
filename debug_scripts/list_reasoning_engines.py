
import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "kallogjeri-project-345114"
LOCATION = "us-central1"

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": PROJECT_ID
}

url = f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines"

try:
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        engines = resp.json().get('reasoningEngines', [])
        if engines:
            print(f"Found {len(engines)} reasoning engines:")
            # Sort by createTime descending to get the latest
            engines.sort(key=lambda x: x.get('createTime', ''), reverse=True)
            latest = engines[0]
            print(f"Latest: {latest.get('name')}")
            print(f"Display Name: {latest.get('displayName')}")
            print(f"Create Time: {latest.get('createTime')}")
            
            # Print all for debugging
            for e in engines:
                print(f" - {e.get('name')} ({e.get('createTime')})")
        else:
            print("No reasoning engines found.")
    else:
        print(f"Error: {resp.status_code} - {resp.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
