#!/bin/bash
# Consolidated Deployment Script for BQ Data Agents Proxy
# Use SKIP_DEPLOY=1 to skip the cloud build and only re-register with Gemini Enterprise.
# Example: export SKIP_DEPLOY=1; ./deploy.sh

export SKIP_DEPLOY=${SKIP_DEPLOY:-0}

# Ensure we run from the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

python3 .scripts/deploy_agent.py
