
import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "kallogjeri-project-345114"
PROJECT_NUMBER = "273872083706"

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": PROJECT_ID
}

TARGET_APPS = [
    {"id": "nl2sql-agent-app-us", "loc": "us"},
    {"id": "gemini-enterprise-17661519_1766151961003", "loc": "global"}
]

TARGET_NAMES = ["NL2SQL Agent", "NL2SQL Claims Agent", "NL2SQL Claims Agent Final"]

print("Starting deep cleanup of NL2SQL agents...")

for app in TARGET_APPS:
    app_id = app["id"]
    loc = app["loc"]
    
    if loc == "global":
        base_url = "https://discoveryengine.googleapis.com"
    else:
        base_url = f"https://{loc}-discoveryengine.googleapis.com"
        
    # Try listing with PROJECT_ID
    url = f"{base_url}/v1alpha/projects/{PROJECT_ID}/locations/{loc}/collections/default_collection/engines/{app_id}/assistants/default_assistant/agents"
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            agents = resp.json().get('agents', [])
            for a in agents:
                display = a.get('displayName')
                name = a.get('name')
                if display in TARGET_NAMES:
                    print(f"Deleting duplicate agent '{display}' ({name})...")
                    del_url = f"{base_url}/v1alpha/{name}"
                    d_resp = requests.delete(del_url, headers=headers)
                    if d_resp.status_code == 200:
                        print("  ✅ Deleted.")
                    else:
                        print(f"  ❌ Failed to delete: {d_resp.status_code}")
    except Exception as e:
        print(f"Error cleaning {app_id}: {e}")

print("Cleanup finished.")
