#!/bin/bash
# Description: Register the already deployed Reasoning Engine agent with Gemini Enterprise.
# Usage: .scripts/expose_agent.sh

set -e

# Export PyPI as a fallback index for pip to resolve dependencies
export PIP_EXTRA_INDEX_URL="https://pypi.org/simple"
PYTHON_BIN="/usr/local/google/home/aburdenko/.venvs/gpu_procurement_lab/bin/python3"

# Load environment variables from .env
if [ -f ".env" ]; then
    echo "Loading configuration from .env..."
    export $(grep -v '^#' .env | sed 's/#.*//' | xargs)
elif [ -f "../.env" ]; then
    echo "Loading configuration from ../.env..."
    export $(grep -v '^#' ../.env | sed 's/#.*//' | xargs)
fi

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: GCP PROJECT_ID is not set." >&2
    exit 1
fi

# Run the deployment script with SKIP_DEPLOY=1 to perform registration only
echo "Skipping container rebuild. Registering the active reasoning engine with Gemini Enterprise..."
export SKIP_DEPLOY=1
"${PYTHON_BIN}" .scripts/deploy_agent.py
