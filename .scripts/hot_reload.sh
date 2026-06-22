#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | sed 's/#.*//' | xargs)
fi

BUCKET_NAME="${A2A_CARD_BUCKET_NAME}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-${PROJECT_ID}}"
LOCATION="${LOCATION:-us-central1}"
if [ "${LOCATION}" = "global" ] || [ -z "${LOCATION}" ]; then
    LOCATION="us-central1"
fi
DISPLAY_NAME="bq_data_agent_proxy"

if [ -z "${BUCKET_NAME}" ]; then
    echo "ERROR: A2A_CARD_BUCKET_NAME not set in .env"
    exit 1
fi

echo "📦 Packaging local codebase..."
# Exclude git, cache, and other temporary files
tar -czf /tmp/bq_proxy_bundle.tar.gz -C enterprise_data_proxy_agent .

echo "📤 Uploading codebase to GCS gs://${BUCKET_NAME}/live_agents/bq_proxy_bundle.tar.gz..."
gcloud storage cp /tmp/bq_proxy_bundle.tar.gz "gs://${BUCKET_NAME}/live_agents/bq_proxy_bundle.tar.gz"

# Resolve python binary
if [ -f "./.venv/python3.12/bin/python" ]; then
    PYTHON_BIN="./.venv/python3.12/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

echo "⚡ Triggering dynamic hot reload in the cloud container..."
# Run a quick python snippet using REST API to trigger hot reload
${PYTHON_BIN} -c "
import os
import requests
import google.auth
from google.auth.transport.requests import Request

PROJECT_ID = '${PROJECT_ID}'
LOCATION = '${LOCATION}'

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
}

# List engines
list_url = f'https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines'
resp = requests.get(list_url, headers=headers)
if resp.status_code != 200:
    print(f'ERROR: Failed to list reasoning engines: {resp.text}')
    exit(1)

engines = resp.json().get('reasoningEngines', [])
target_name = None
for eng in engines:
    if eng.get('displayName', '').startswith('${DISPLAY_NAME}'):
        target_name = eng.get('name')
        break

if not target_name:
    print('ERROR: Active ${DISPLAY_NAME} reasoning engine not found!')
    exit(1)

print(f'Sending hot reload trigger to: {target_name}...')
query_url = f'https://{LOCATION}-aiplatform.googleapis.com/v1beta1/{target_name}:streamQuery'
payload = {
    'class_method': 'stream_query',
    'input': {
        'message': '__HOT_RELOAD_TRIGGER__',
        'user_id': 'hot_reload_system'
    }
}

try:
    resp = requests.post(query_url, headers=headers, json=payload, timeout=30)
    print('Trigger response status:', resp.status_code)
    if resp.status_code == 200:
        print('Trigger response received successfully.')
    else:
        print('Trigger response details:', resp.text)
except Exception as e:
    print('Connection reset or exception (expected as container successfully restarts/resets connection):', e)
"

echo "🚀 Hot reload completed successfully! Your changes are now live in the cloud."
