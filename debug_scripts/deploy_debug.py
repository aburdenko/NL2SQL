import sys
import os
import logging
logging.basicConfig(level=logging.DEBUG)

from google.adk.cli import cli_deploy

# Pass the absolute path so parent_folder is correct.
agent_folder = os.path.abspath("nl2sql_deploy")

cli_deploy.to_agent_engine(
    agent_folder=agent_folder,
    project="kallogjeri-project-345114",
    region="us-central1",
    display_name="test_deploy_debug",
    adk_app="agent_engine_app",
    adk_app_object="root_agent",
    skip_agent_import_validation=False
)