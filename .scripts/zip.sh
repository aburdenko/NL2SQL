#!/bin/bash

# Change to the project root directory, regardless of where the script is executed from.
cd "$(dirname "$0")/.." || exit

# Delete the archive if it already exists
rm -f enterprise_data_proxy_agent.tar.gz

# Create the archive in a temporary location to prevent "file changed as we read it" errors.
# The error happens because tar modifies the directory '.' while it is trying to read it.
tar -czvf /tmp/enterprise_data_proxy_agent.tar.gz \
   --exclude='.venv' \
   --exclude='__pycache__' \
   --exclude='.env' \
   --exclude='logs' \
   --exclude='*.log' \
   --exclude='deploy_archives/*' \
   --exclude='.gemini' \
   --exclude='.adk' \
   --exclude='*.tar.gz' \
   --exclude='.codeoss-cloudworkstations' \
   .

# Move the completed archive back into the project directory
mv /tmp/enterprise_data_proxy_agent.tar.gz ./enterprise_data_proxy_agent.tar.gz
