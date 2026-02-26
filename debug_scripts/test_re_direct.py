import os
import vertexai
from vertexai.agent_engines import AdkApp
from google.adk.agents import Agent

agent_obj = Agent(name="test_agent", model="gemini-2.0-flash", tools=[])
adk_app = AdkApp(agent=agent_obj)

vertexai.init(project="kallogjeri-project-345114", location="us-central1")
client = vertexai.Client(project="kallogjeri-project-345114", location="us-central1")

try:
    print("Creating Agent Engine (should fail or give error message)...")
    res = client.agent_engines.create(
        config={
            "display_name": "test_direct",
            "entrypoint_module": "agent",
            "entrypoint_object": "adk_app",
            "source_packages": ["nl2sql_deploy"],
            "requirements_file": "nl2sql_deploy/requirements.txt"
        }
    )
    print(res)
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
