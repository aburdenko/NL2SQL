#!/bin/bash
# Consolidated Deployment Script for BQ Data Agents Proxy
# Use SKIP_DEPLOY=1 to skip the cloud build and only re-register with Gemini Enterprise.
# Example: export SKIP_DEPLOY=1; ./deploy.sh

export SKIP_DEPLOY=${SKIP_DEPLOY:-0}

# Ensure we run from the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | sed 's/#.*//' | xargs)
fi

if [ "${DYNAMIC_HOT_RELOAD}" = "1" ]; then
    echo "⚡ DYNAMIC_HOT_RELOAD=1 detected. Attempting fast hot reload..."
    if .scripts/hot_reload.sh; then
        echo "🚀 Hot reload completed successfully!"
        exit 0
    else
        echo "⚠️ Hot reload failed or no active reasoning engine found. Falling back to full deployment..."
    fi
fi

# Resolve python binary
if [ -f "./.venv/python3.12/bin/python" ]; then
    PYTHON_BIN="./.venv/python3.12/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

$PYTHON_BIN .scripts/deploy_agent.py
