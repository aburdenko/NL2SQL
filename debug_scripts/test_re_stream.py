
import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = "kallogjeri-project-345114"
LOCATION = "us-central1"
ENGINE_ID = "4518142867671089152"

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
}

# Try stream_query
url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}:streamQuery"

payload = {
    "input": {
        "input": "how many claims do I have?"
    }
}

print(f"Stream Querying Reasoning Engine {ENGINE_ID}...")
resp = requests.post(url, headers=headers, json=payload)
print(f"Status Code: {resp.status_code}")
print(resp.text)
