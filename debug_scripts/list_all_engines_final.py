
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

url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines"

resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    engines = resp.json().get('reasoningEngines', [])
    for e in engines:
        print(f"ID: {e.get('name').split('/')[-1]} | Name: {e.get('displayName')}")
else:
    print(f"Error: {resp.status_code}")
