import os
import sys
import subprocess
import time
import requests
import re
import google.auth
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GCP_PROJECT_ID = os.environ.get("PROJECT_ID", "kallogjeri-project-345114")
PROJECT_NUMBER = "273872083706"
DEPLOY_DIR = "enterprise_data_proxy_agent"
RE_DISPLAY_NAME = "bq_data_agent_proxy"
AGENT_DISPLAY_NAME = "BQ Data Agent Proxy"

# ==========================================
# 1. Ensure Service Account Roles
# ==========================================
# When Agent Engine executes your code, it runs under the Compute Engine Default Service Account.
# For the Agent to query BigQuery and talk to Conversational Data Agents, it requires:
# 1. Vertex AI User (roles/aiplatform.user) to invoke models/agents.
# 2. BigQuery Data Viewer (roles/bigquery.dataViewer) to read the schema and table data.
# 3. BigQuery Job User (roles/bigquery.jobUser) to execute query jobs.
# 
# Additionally, Google's internal service agents (Reasoning Engine, Data Analytics, and AI Platform) 
# must also have these underlying BigQuery permissions to fetch data on behalf of your deployment.
# This step dynamically looks up the project number and binds these roles to prevent silent failures.
print("--- Step 1: Ensuring Service Accounts have required roles ---")

# Dynamically get project number
try:
    proj_num_str = subprocess.check_output(
        f"gcloud projects describe {GCP_PROJECT_ID} --format='value(projectNumber)'", 
        shell=True, text=True
    ).strip()
    if proj_num_str:
        project_number_to_use = proj_num_str
    else:
        project_number_to_use = PROJECT_NUMBER
except Exception:
    project_number_to_use = PROJECT_NUMBER

service_accounts_roles = {
    f"{project_number_to_use}-compute@developer.gserviceaccount.com": [
        "roles/aiplatform.user",
        "roles/bigquery.dataViewer",
        "roles/bigquery.jobUser"
    ],
    f"service-{project_number_to_use}@gcp-sa-aiplatform-re.iam.gserviceaccount.com": [
        "roles/bigquery.dataViewer",
        "roles/bigquery.jobUser"
    ],
    f"service-{project_number_to_use}@gcp-sa-geminidataanalytics.iam.gserviceaccount.com": [
        "roles/bigquery.dataViewer",
        "roles/bigquery.jobUser"
    ],
    f"service-{project_number_to_use}@gcp-sa-aiplatform.iam.gserviceaccount.com": [
        "roles/bigquery.dataViewer"
    ]
}

for sa, roles in service_accounts_roles.items():
    for role in roles:
        print(f"Binding {role} to {sa}...")
        cmd_str = f"gcloud projects add-iam-policy-binding {GCP_PROJECT_ID} --member=\"serviceAccount:{sa}\" --role=\"{role}\" --quiet"
        subprocess.run(cmd_str, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ==========================================
# 2. Cleanup & 3. Deploy (Conditional)
# ==========================================
REASONING_ENGINE_RESOURCE_NAME = None

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
credentials, project = google.auth.default(scopes=SCOPES)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": GCP_PROJECT_ID
}

list_url = f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{GCP_PROJECT_ID}/locations/us-central1/reasoningEngines"

if str(os.environ.get("SKIP_DEPLOY")).lower() in ["1", "true"]:
    print("--- Steps 2 & 3: Skipping deployment based on SKIP_DEPLOY env var ---")
    try:
        resp = requests.get(list_url, headers=headers)
        if resp.status_code == 200:
            engines = resp.json().get('reasoningEngines', [])
            if engines:
                # Filter for our naming convention
                targets = [e for e in engines if e.get('displayName', '').startswith(RE_DISPLAY_NAME)]
                if targets:
                    targets.sort(key=lambda x: x.get('createTime', ''), reverse=True)
                    REASONING_ENGINE_RESOURCE_NAME = targets[0].get('name')
                    print(f"Found existing engine: {REASONING_ENGINE_RESOURCE_NAME} ({targets[0].get('displayName')})")
                else:
                    # Fallback to absolute latest
                    engines.sort(key=lambda x: x.get('createTime', ''), reverse=True)
                    REASONING_ENGINE_RESOURCE_NAME = engines[0].get('name')
                    print(f"No match for '{RE_DISPLAY_NAME}', using latest instead: {REASONING_ENGINE_RESOURCE_NAME}")
            else:
                print("No reasoning engines found.")
        else:
            print(f"Error listing engines: {resp.status_code}")
    except Exception as e:
        print(f"Exception while searching for engine: {e}")

else:
    # Cleanup
    print("--- Step 2: Cleaning up old Reasoning Engines ---")
    try:
        resp = requests.get(list_url, headers=headers)
        if resp.status_code == 200:
            for engine in resp.json().get('reasoningEngines', []):
                display_name = engine.get('displayName', '')
                if display_name.startswith(RE_DISPLAY_NAME) or "nl2sql" in display_name.lower():
                    print(f"Deleting old engine: {display_name} ({engine.get('name')})...")
                    requests.delete(f"https://us-central1-aiplatform.googleapis.com/v1beta1/{engine.get('name')}?force=true", headers=headers)
                    time.sleep(2)
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")

    # Deploy
    print("--- Step 3: Deploying to Agent Engine ---")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    re_display_name = f"{RE_DISPLAY_NAME}_{timestamp}"
    
    # NOTE: --adk_app defines the generated entrypoint file. Do not use 'agent' as it overwrites your own agent.py
    deploy_command = (
        f"adk deploy agent_engine {DEPLOY_DIR} "
        f"--project={GCP_PROJECT_ID} "
        f"--region=us-central1 "
        f"--display_name={re_display_name} "
        f"--env_file=.env"
    )
    
    print(f"Running: {deploy_command}")
    
    # Run the process and stream output line by line
    process = subprocess.Popen(
        deploy_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1 # Line buffered
    )
    
    full_output = []
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            # Print to sys.stdout and immediately flush it to ensure it goes to the file right away
            sys.stdout.write(line)
            sys.stdout.flush()
            full_output.append(line)
            
    return_code = process.poll()
    result_stdout = "".join(full_output)
    
    if return_code != 0:
        print("❌ Deployment failed!")
        raise RuntimeError("Deployment to Agent Engine failed. Check logs above.")

    match = re.search(r"Created agent engine: (projects\/[\w\-\/]+)", result_stdout)
    if not match:
        print("Deployment log didn't show ID explicitly, polling for the one we just created...")
        time.sleep(15)
        resp = requests.get(list_url, headers=headers)
        engines = resp.json().get('reasoningEngines', [])
        engines.sort(key=lambda x: x.get('createTime', ''), reverse=True)
        
        # Verify the top one is indeed the one we just deployed
        latest = engines[0]
        if latest.get('displayName') == re_display_name:
             REASONING_ENGINE_RESOURCE_NAME = latest.get('name')
        else:
             raise RuntimeError(f"Latest engine '{latest.get('displayName')}' does not match our deployment '{re_display_name}'. Deployment likely failed.")
    else:
        REASONING_ENGINE_RESOURCE_NAME = match.group(1)

if not REASONING_ENGINE_RESOURCE_NAME:
    raise ValueError("REASONING_ENGINE_RESOURCE_NAME is not set.")

print(f"✅ Reasoning Engine ready: {REASONING_ENGINE_RESOURCE_NAME}")

# ==========================================
# 4. Register with Gemini Enterprise
# ==========================================
print("--- Step 4: Registering with Gemini Enterprise ---")
TARGET_APPS = [
    {"id": "nl2sql-agent-app-us", "loc": "us", "col": "default_collection"},
    {"id": "gemini-enterprise-17661519_1766151961003", "loc": "global", "col": "default_collection"}
]

for app in TARGET_APPS:
    app_id, loc, col = app["id"], app["loc"], app["col"]
    reg_base = "https://discoveryengine.googleapis.com" if loc == "global" else f"https://{loc}-discoveryengine.googleapis.com"
    agents_url = f"{reg_base}/v1alpha/projects/{GCP_PROJECT_ID}/locations/{loc}/collections/{col}/engines/{app_id}/assistants/default_assistant/agents"
    
    try:
        resp = requests.get(agents_url, headers=headers)
        if resp.status_code == 200:
            for a in resp.json().get('agents', []):
                if a.get('displayName') == AGENT_DISPLAY_NAME:
                    print(f"Deleting old agent from {app_id}...")
                    requests.delete(f"{reg_base}/v1alpha/{a.get('name')}", headers=headers)
    except:
        pass

    # Register
    payload = {
        "displayName": AGENT_DISPLAY_NAME,
        "description": "Dual-Compatible Data Agents Proxy",
        "adkAgentDefinition": {
            "toolSettings": {"toolDescription": "Claims data tool"},
            "provisionedReasoningEngine": {"reasoningEngine": f"projects/{PROJECT_NUMBER}/locations/us-central1/reasoningEngines/{REASONING_ENGINE_RESOURCE_NAME.split('/')[-1]}"}
        }
    }
    reg_resp = requests.post(agents_url, headers=headers, json=payload)
    if reg_resp.status_code == 200:
        print(f"✅ Successfully registered to {app_id}")
    else:
        print(f"❌ Failed to register to {app_id}: {reg_resp.text}")

print("\n🚀 DEPLOYMENT COMPLETE!")
