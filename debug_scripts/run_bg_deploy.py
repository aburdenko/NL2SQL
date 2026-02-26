
import subprocess
import time
import os

cmd = "adk deploy agent_engine nl2sql_deploy --project=kallogjeri-project-345114 --region=us-central1 --display_name=nl2sql_test_final --adk_app=agent"
print(f"Starting background deploy: {cmd}")

with open("background_deploy.log", "w") as f:
    process = subprocess.Popen(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, text=True)
    print(f"Process started with PID: {process.pid}")
