
import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "kallogjeri-project-345114"
APP_ID = "nl2sql-agent-app-us"

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": PROJECT_ID
}

base_url = "https://us-discoveryengine.googleapis.com"
url = f"{base_url}/v1alpha/projects/{PROJECT_ID}/locations/us/collections/default_collection/engines/{APP_ID}/assistants"

try:
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        assistants = resp.json().get('assistants', [])
        print(f"Found {len(assistants)} assistant(s) in App {APP_ID}:")
        for a in assistants:
            print(f" - {a.get('name')}")
    else:
        print(f"Error: {resp.status_code}")
except Exception as e:
    print(f"Exception: {e}")
