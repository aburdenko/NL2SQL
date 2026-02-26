
import os
import requests
import google.auth
from google.auth.transport.requests import Request
import time

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

url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines"

print(f"Waiting for new Reasoning Engine to be created...")

start_time = time.time()
while time.time() - start_time < 600: # Wait up to 10 mins
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            engines = resp.json().get('reasoningEngines', [])
            if engines:
                # Get the latest by createTime
                engines.sort(key=lambda x: x.get('createTime', ''), reverse=True)
                latest = engines[0]
                create_time = latest.get('createTime')
                # If created in the last 10 minutes (rough check)
                if "2026-02-25T21" in create_time or "2026-02-25T22" in create_time:
                     print(f"✅ Found new engine: {latest.get('displayName')} ({latest.get('name')})")
                     print(f"   Created at: {create_time}")
                     break
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Exception: {e}")
    
    print("Still waiting...")
    time.sleep(30)
