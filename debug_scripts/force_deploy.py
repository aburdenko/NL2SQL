
import os
import subprocess
import re
import time

DEPLOY_DIR = "nl2sql_deploy"
PROJECT_ID = "kallogjeri-project-345114"
REGION = "us-central1"

print(f"Starting force deployment from {DEPLOY_DIR}...")

deploy_command = [
    "adk", "deploy", "agent_engine", DEPLOY_DIR,
    f"--project={PROJECT_ID}",
    f"--region={REGION}",
    "--display_name=nl2sql_force_deploy"
]

# Use a longer timeout for the command execution
try:
    process = subprocess.Popen(deploy_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Poll for output
    full_stdout = ""
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(line.strip())
            full_stdout += line
            
    stderr = process.stderr.read()
    if stderr:
        print("--- Errors ---")
        print(stderr)
        
    # Extract Reasoning Engine ID
    match = re.search(r"Created agent engine: (projects\/[\w\-\/]+)", full_stdout)
    if match:
        re_id = match.group(1)
        print(f"
✅ SUCCESS: New Reasoning Engine: {re_id}")
        # Save to a file for the main script to pick up
        with open("latest_re_id.txt", "w") as f:
            f.write(re_id)
    else:
        print("
❌ FAILED to capture Reasoning Engine ID from output.")
        
except Exception as e:
    print(f"An error occurred: {e}")
