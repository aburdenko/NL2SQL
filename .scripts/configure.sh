# Usage: source .scripts/configure.sh

ADK_PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")"
export PIP_INDEX_URL="https://pypi.org/simple"

# --- Antigravity CLI Verification ---
if [ -f "/app/antigravity" ]; then
    echo "Antigravity CLI verified at /app/antigravity."
    export PATH="/app:$PATH"
elif [ -f "$HOME/.local/bin/agy" ]; then
    echo "Antigravity CLI verified at $HOME/.local/bin/agy."
    export PATH="$HOME/.local/bin:$PATH"
elif command -v antigravity &> /dev/null; then
    echo "Antigravity CLI verified on PATH."
else
    echo "Warning: Antigravity CLI not found." >&2
fi

# --- Gemini CLI Installation/Update ---
if ! command -v npm &> /dev/null; then
  echo "Error: npm is not installed. Please install Node.js and npm to continue." >&2
  return 1
fi

if ! command -v gemini &> /dev/null; then
  echo "Checking for the latest Gemini CLI version..."
  LATEST_VERSION=$(npm view @google/gemini-cli version 2>/dev/null || echo "")
  if [ -n "$LATEST_VERSION" ]; then
    echo "Gemini CLI not found. Installing version $LATEST_VERSION..."
    sudo npm install -g @google/gemini-cli@latest || true
  else
    echo "WARNING: Could not fetch latest Gemini CLI version. Please check npm configuration or run gcert." >&2
  fi
else
  echo "Gemini CLI is already installed."
fi


# --- Environment Configuration ---
# This script now sources its configuration from the .env file in the project root.
ENV_FILE="$ADK_PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Configuration file '$ENV_FILE' not found." >&2
    echo "Please create it by copying from '.env.example' and filling in the values." >&2
    return 1 # Use return instead of exit to allow sourcing to fail gracefully
fi

# Read variables from .env, filter out comments, and export them.
# This pipeline filters out full-line comments, then strips inline comments,
# then exports the remaining VAR=value pairs.
export $(grep -v '^#' "$ENV_FILE" | sed 's/#.*//' | xargs)

# Sourced credentials paths will be verified and expanded at runtime below without modifying the .env file.

# --- Git User Configuration ---
# Set git user.name and user.email if they are defined in the .env file.
if [ -n "$GIT_USER_NAME" ] && [ -n "$GIT_USER_EMAIL" ]; then
  echo "Configuring git user name and email..."
  git config --global user.name "$GIT_USER_NAME"
  git config --global user.email "$GIT_USER_EMAIL"
else
  echo "Skipping git user configuration (GIT_USER_NAME or GIT_USER_EMAIL not set in .env)."
fi

# --- Google Credentials Setup ---
# This section determines the GCP Project ID and sets up credentials.
# The order of precedence is:
# 1. Service Account specified in .env (SERVICE_ACCOUNT_KEY_FILE)
# 2. User's Application Default Credentials (ADC) via gcloud

# Helper to expand ~ and environment variables in a path
expand_path() {
  local path="$1"
  path="${path/#\~/$HOME}"
  path="${path//\$HOME/$HOME}"
  path="${path//\$\{HOME\}/$HOME}"
  echo "$path"
}

# --- Step 0: Sanitize credentials to prevent DefaultCredentialsError on Cloud Shell ---
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  EXPANDED_GAC=$(expand_path "$GOOGLE_APPLICATION_CREDENTIALS")
  if [ ! -f "$EXPANDED_GAC" ]; then
    echo "WARNING: GOOGLE_APPLICATION_CREDENTIALS points to a non-existent file: $GOOGLE_APPLICATION_CREDENTIALS"
    echo "Unsetting GOOGLE_APPLICATION_CREDENTIALS to allow fallback authentication."
    unset GOOGLE_APPLICATION_CREDENTIALS
  else
    export GOOGLE_APPLICATION_CREDENTIALS="$EXPANDED_GAC"
  fi
fi

if [ -n "$SERVICE_ACCOUNT_KEY_FILE" ]; then
  EXPANDED_SA_KEY=$(expand_path "$SERVICE_ACCOUNT_KEY_FILE")
  if [ ! -f "$EXPANDED_SA_KEY" ]; then
    echo "WARNING: SERVICE_ACCOUNT_KEY_FILE points to a non-existent file: $SERVICE_ACCOUNT_KEY_FILE"
    echo "Unsetting SERVICE_ACCOUNT_KEY_FILE."
    unset SERVICE_ACCOUNT_KEY_FILE
  else
    export SERVICE_ACCOUNT_KEY_FILE="$EXPANDED_SA_KEY"
  fi
fi

echo "--- Configuring Google Cloud Authentication & Project ---"

# --- Step 1: Check for Service Account ---
# Use the service account key file if specified in .env and it exists,
# or fallback to the local service_account.json symlink/file if it exists and is a valid file.
KEY_FILE=""
if [ -n "$SERVICE_ACCOUNT_KEY_FILE" ] && [ -f "$SERVICE_ACCOUNT_KEY_FILE" ]; then
  KEY_FILE="$SERVICE_ACCOUNT_KEY_FILE"
elif [ -f "service_account.json" ]; then
  echo "Local service_account.json found and valid. Using it for authentication."
  export SERVICE_ACCOUNT_KEY_FILE="service_account.json"
  KEY_FILE="service_account.json"
fi

if [ -n "$KEY_FILE" ]; then
  echo "Service Account key found at '$KEY_FILE'. Using it for authentication."
  export GOOGLE_APPLICATION_CREDENTIALS="$KEY_FILE"
  # If PROJECT_ID is not already set in .env, extract it from the SA key.
  if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(jq -r .project_id "$KEY_FILE")
    if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" == "null" ]; then
      echo "ERROR: Could not extract project_id from service account key file." >&2
      echo "Please set PROJECT_ID in your .env file." >&2
      return 1
    fi
    echo "Inferred PROJECT_ID from Service Account: $PROJECT_ID"
  fi
else
  # --- Step 2: Fallback to Application Default Credentials (ADC) ---
  echo "Service Account key not found or not specified. Falling back to gcloud Application Default Credentials."
  unset GOOGLE_APPLICATION_CREDENTIALS

  # Ensure user is logged in for ADC. This avoids re-prompting on every `source`.
  if ! gcloud auth application-default print-access-token &>/dev/null; then
    echo "User is not logged in for ADC. Running 'gcloud auth application-default login'..."
    if ! gcloud auth application-default login --no-launch-browser --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform; then
      echo "ERROR: gcloud auth application-default login failed." >&2
      return 1
    fi
  else
    echo "User already logged in with Application Default Credentials."
  fi

  # If PROJECT_ID is not set from .env, try to get it from gcloud config.
  if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -n "$PROJECT_ID" ]; then
      echo "Using configured gcloud project: $PROJECT_ID"
    else
      # If still no PROJECT_ID, prompt the user to select one.
      echo "Could not determine gcloud project. Fetching available projects..."
      mapfile -t projects < <(gcloud projects list --format="value(projectId,name)" --sort-by=projectId)

      if [ ${#projects[@]} -eq 0 ]; then
        echo "No projects found. Please enter your Google Cloud Project ID manually:"
        read -p "Project ID: " PROJECT_ID
        if [ -z "$PROJECT_ID" ]; then
          echo "ERROR: Project ID is required." >&2
          return 1
        fi
      else
        echo "Please select a project:"
        for i in "${!projects[@]}"; do
          printf "%3d) %s\n" "$((i+1))" "${projects[$i]}"
        done
        read -p "Enter number: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#projects[@]}" ]; then
          PROJECT_ID=$(echo "${projects[$((choice-1))]}" | awk '{print $1}')
        else
          echo "ERROR: Invalid selection." >&2
          return 1
        fi
      fi
    fi
  fi
fi

# --- Step 3: Finalize Project Configuration ---
if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: Project ID could not be determined. Please check your configuration." >&2
  return 1
fi

echo "Setting active gcloud project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"
gcloud auth application-default set-quota-project "$PROJECT_ID"

# Get project number, which is needed for some service agent roles
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

# --- Virtual Environment Setup ---
# --- Virtual Environment Setup ---
LOCAL_VENV_DIR="$HOME/.venvs/python3.12-venv"
VENV_INITIALIZED=false

if [ ! -d "$LOCAL_VENV_DIR" ]; then
  # Ensure python3.12-venv is installed if not present
  if ! /usr/bin/python3.12 -c "import venv" &>/dev/null; then
    echo "python3.12-venv not found. Attempting to install..."
    sudo apt update && sudo apt install -y python3.12-venv
  fi

  echo "Creating Python virtual environment on local disk: $LOCAL_VENV_DIR..."
  mkdir -p "$HOME/.venvs"
  /usr/bin/python3.12 -m venv "$LOCAL_VENV_DIR"
  VENV_INITIALIZED=true
fi

mkdir -p .venv
if [ ! -L ".venv/python3.12" ] || [ "$(readlink -f ".venv/python3.12")" != "$LOCAL_VENV_DIR" ]; then
  echo "Setting up symlink .venv/python3.12 -> $LOCAL_VENV_DIR..."
  if [ -e ".venv/python3.12" ]; then
    OLD_VENV_TMP=".venv/python3.12.old.$(date +%s)"
    mv ".venv/python3.12" "$OLD_VENV_TMP"
    rm -rf "$OLD_VENV_TMP" &
  fi
  ln -sf "$LOCAL_VENV_DIR" ".venv/python3.12"
  VENV_INITIALIZED=true
fi

if [ "$VENV_INITIALIZED" = true ]; then
  echo "Initializing environment setup..."
  
  # Grant the Vertex AI Service Agent the necessary role on your staging bucket
  gcloud storage buckets add-iam-policy-binding gs://$SOURCE_GCS_BUCKET \
    --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-aiplatform.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

  # Grant the Vertex AI Service Agent the necessary role on your staging bucket
  gcloud storage buckets add-iam-policy-binding gs://$STAGING_GCS_BUCKET \
    --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-aiplatform.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

  # Grant the Vertex AI Service Agent the necessary role to create objects in the staging bucket
  gcloud storage buckets add-iam-policy-binding gs://$STAGING_GCS_BUCKET \
    --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-aiplatform.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"

  # Grant the Vertex AI Service Agent the necessary role to create objects in the staging bucket
  gcloud storage buckets add-iam-policy-binding gs://$STAGING_GCS_BUCKET \
    --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-aiplatform.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"
    
  # --- Ensure 'unzip' is installed for VSIX validation ---
  if ! command -v unzip &> /dev/null; then
    echo "'unzip' command not found. Attempting to install..."
    sudo apt-get update && sudo apt-get install -y unzip
  fi

  # --- Ensure 'jq' is installed for robust JSON parsing ---
  if ! command -v jq &> /dev/null; then
    echo "'jq' command not found. Attempting to install..."
    sudo apt-get update && sudo apt-get install -y jq
  fi

  # --- VS Code Extension Setup (One-time) ---
  echo "Checking for 'emeraldwalk.runonsave' VS Code extension..."
  # Use the full path to the executable, which we know from the environment
  CODE_OSS_EXEC="/opt/code-oss/bin/codeoss-cloudworkstations"

  if ! $CODE_OSS_EXEC --list-extensions | grep -q "emeraldwalk.runonsave"; then
    echo "Extension not found. Installing 'emeraldwalk.runonsave'..."

    # Using the static URL as requested. Note: This points to an older version (0.3.2)
    # and replaces the logic that dynamically finds the latest version.
    VSIX_URL="https://www.vsixhub.com/go.php?post_id=519&app_id=65a449f8-c656-4725-a000-afd74758c7e6&s=v5O4xJdDsfDYE&link=https%3A%2F%2Fmarketplace.visualstudio.com%2F_apis%2Fpublic%2Fgallery%2Fpublishers%2Femeraldwalk%2Fvsextensions%2FRunOnSave%2F0.3.2%2Fvspackage"
    VSIX_FILE="/tmp/emeraldwalk.runonsave.vsix" # Use /tmp for the download

    echo "Downloading extension from specified static URL..."
    # Use curl with -L to follow redirects and -o to specify output file
    # Add --fail to error out on HTTP failure and -A to specify a browser User-Agent
    if curl --fail -L -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36' -o "$VSIX_FILE" "$VSIX_URL"; then
      echo "Download complete. Installing..."
      # Add a check to ensure the downloaded file is a valid zip archive (.vsix)
      if unzip -t "$VSIX_FILE" &> /dev/null; then
        if $CODE_OSS_EXEC --install-extension "$VSIX_FILE"; then
          echo "Extension 'emeraldwalk.runonsave' installed successfully."
          echo "IMPORTANT: Please reload the VS Code window to activate the extension."
        else
          echo "Error: Failed to install the extension from '$VSIX_FILE'." >&2
        fi
      else
        echo "Error: Downloaded file is not a valid VSIX package. It may be an HTML page." >&2
        echo "Please check the VSIX_URL in the script or your network connection." >&2
      fi
      # Clean up the downloaded file
      rm -f "$VSIX_FILE" # This will run regardless of install success/failure
    else
      echo "Error: Failed to download the extension from '$VSIX_URL'." >&2
    fi
  else
    echo "Extension 'emeraldwalk.runonsave' is already installed."
  fi
else
  echo "Virtual environment '.python3.12' is already set up and linked."
fi

echo "Activating environment './venv/python3.12'..."
 . .venv/python3.12/bin/activate

# Ensure dependencies are installed/updated every time the script is sourced.
# This prevents ModuleNotFoundError if requirements.txt changes after the
# virtual environment has been created.
echo "Ensuring dependencies from requirements.txt are installed..."
 # Use the full path to the venv pip to ensure we're installing in the correct environment.
 # We use --quiet to reduce noise, but we do not redirect stderr to /dev/null.
 # This ensures that if pip encounters an error (e.g., a missing package), the error will be displayed.
if ! ./.venv/python3.12/bin/pip install --quiet --no-cache-dir -r requirements.txt; then
  echo "ERROR: Failed to install dependencies from requirements.txt. Please check the file for errors." >&2
fi

echo "Installing project packages (Phase 1, 2, and 3) in editable mode..."
# We run pip install from their respective folders to ensure relative paths resolve correctly
(cd labs/phase1 && ../../.venv/python3.12/bin/pip install --quiet -e .)
(cd labs/phase2 && ../../.venv/python3.12/bin/pip install --quiet -e .)
(cd labs/phase3 && ../../.venv/python3.12/bin/pip install --quiet -e .)

# --- Google Agent Development Kit Check ---
# This ensures the necessary libraries for agent development (including RAG and LangChain support) are installed.
AGENT_PKG_INSTALL="google-cloud-aiplatform[rag,eval]"
AGENT_PKG_CHECK="google-cloud-aiplatform" # pip show works on the base package name

# Explicitly install the AI Platform package if it's not already present.
if ! ./.venv/python3.12/bin/pip show "$AGENT_PKG_CHECK" &> /dev/null; then
  echo "Google Cloud AI Platform not found. Installing..."
  ./.venv/python3.12/bin/pip install --quiet "$AGENT_PKG_INSTALL"
fi

# --- Google ADK Installation/Update ---
echo "Checking for the latest google-adk version..."
LATEST_ADK_VERSION=$(curl -s https://pypi.org/pypi/google-adk/json | jq -r .info.version)

if ! ./.venv/python3.12/bin/pip show google-adk &> /dev/null; then
  echo "google-adk not found. Installing the latest version ($LATEST_ADK_VERSION)..."
  ./.venv/python3.12/bin/pip install --quiet "google-adk[eval]==$LATEST_ADK_VERSION"
else
  INSTALLED_ADK_VERSION=$(./.venv/python3.12/bin/pip show google-adk 2>/dev/null | grep '^Version:' | awk '{print $2}')
  if [ "$INSTALLED_ADK_VERSION" == "$LATEST_ADK_VERSION" ]; then
    echo "google-adk is already up to date (version $INSTALLED_ADK_VERSION)."
  else
    echo "A new version of google-adk is available."
    echo "Upgrading from version $INSTALLED_ADK_VERSION to $LATEST_ADK_VERSION..."
    ./.venv/python3.12/bin/pip install --quiet --upgrade "google-adk[eval]==$LATEST_ADK_VERSION"
  fi
fi
# This POSIX-compliant check ensures the script is sourced, not executed.
# (return 0 2>/dev/null) will succeed if sourced and fail if executed.
if ! (return 0 2>/dev/null); then
  echo "-------------------------------------------------------------------"
  echo "ERROR: This script must be sourced, not executed."
  echo "Usage: source .scripts/configure.sh"
  echo "-------------------------------------------------------------------"
  exit 1
fi

# Define a function to start the ADK web server.
# This function checks for the correct authenticated user before launching.
adkweb() {
  # First check if we have a valid service account configured
  if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Using Service Account defined in GOOGLE_APPLICATION_CREDENTIALS for adkweb."
    echo "Skipping interactive user authentication."
  else
    # Check if GCP_USER_ACCOUNT is set from the .env file
    if [ -z "$GCP_USER_ACCOUNT" ]; then
      echo "Error: GCP_USER_ACCOUNT is not set in your .env file." >&2
      return 1
    fi

    # Get the currently active gcloud account
    local current_user
    current_user=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")

    if [ "$current_user" != "$GCP_USER_ACCOUNT" ]; then
      echo "WARNING: You are currently authenticated as '$current_user'."
      echo "The ADK web server requires you to be '$GCP_USER_ACCOUNT'."

      # Use 'application-default login' to set the credentials that libraries like ADK use.
      echo "Updating Application Default Credentials. Please log in as '$GCP_USER_ACCOUNT' in the browser."
      gcloud auth application-default login --project="$PROJECT_ID" --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,openid" || return 1
    fi
  fi

  # Display the browser identity warning BEFORE starting the blocking server process.
  echo
  echo "-------------------------------------------------------------------"
  echo "IMPORTANT BROWSER NOTE (to avoid 401 errors):"
  echo "If you see a '401: ... does not have access' error in the browser,"
  echo "it means your BROWSER is signed into the wrong Google account."
  echo
  echo "The most reliable solution is to use an Incognito/Private window:"
  echo "1. Copy the server URL (e.g., http://127.0.0.1:8001)."
  echo "2. Open a new Incognito/Private browser window."
  echo "3. Paste the URL and you will be prompted to log in with the correct"
  echo "   account: '$GCP_USER_ACCOUNT'."
  echo
  echo "(Switching accounts in the main browser window can be unreliable.)"
  echo "-------------------------------------------------------------------"
  echo

  echo "Stopping any existing ADK web server..."
  local pids=$(lsof -t -i :8001) # Get all PIDs
  if [ -n "$pids" ]; then
    echo "Attempting graceful shutdown of processes $pids on port 8001..."
    for pid in $pids; do # Iterate over each PID
      kill "$pid" # Send SIGTERM
      sleep 1
    done
    sleep 2 # Give time for graceful shutdown
    for pid in $pids; do # Check if any are still running
      if ps -p "$pid" > /dev/null; then
        echo "Process $pid did not terminate gracefully, forcing shutdown..."
        kill -9 "$pid" # Force kill
        sleep 1
      fi
    done
  else
    echo "No process found listening on port 8001."
  fi
  # Determine target directory relative to where the command was called.
  local target_dir="${1:-$(pwd)}"
  target_dir=$(readlink -f "$target_dir")

  echo "Starting ADK web server on port 8001 for agents in: $target_dir"
  # Determine the absolute path to the project root directory.
  local project_root="${ADK_PROJECT_ROOT}"

  # Use an absolute path to the activate script to ensure it works regardless of
  # the current working directory.
  # Run the server in the foreground for easier debugging and control.
  # We must explicitly pass the environment variables to the new bash shell.
  # We run our custom logging script directly. The script is configured to start a uvicorn
  # server that loads the ADK app and injects our logging middleware. This approach
  # bypasses the `adk web` command, avoiding issues with older ADK versions that
  # lack the --bootstrap flag, and prevents the server from hanging.
  nohup "$project_root/.venv/python3.12/bin/adk" web --port 8001 --host 0.0.0.0 "$target_dir" > "$project_root/nohup.out" 2>&1 &
  
  (
    sleep 3
    echo "Opening ADK web URL in Google Chrome..."
    google-chrome "http://127.0.0.1:8001" & > /dev/null 2>&1
  ) &
}

export PATH=$PATH:$HOME/.local/bin:.scripts

uv tool install google-agents-cli

if ! command -v gh &>/dev/null; then
  echo "GitHub CLI (gh) not found. Attempting to install..."
  if sudo -n true 2>/dev/null; then
    (type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
            && sudo apt update && sudo apt install xvfb libxkbcommon0 libgtk-3-0 -y \
            && sudo mkdir -p -m 755 /etc/apt/keyrings \
            && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
            && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
            && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
            && sudo mkdir -p -m 755 /etc/apt/sources.list.d \
            && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
            && sudo apt update \
            && sudo apt install gh -y
  else
    echo "WARNING: gh command not found, and passwordless sudo is not available to install it."
  fi
else
  echo "GitHub CLI (gh) is already installed."
fi

unset GOOGLE_API_KEY GEMINI_API_KEY
# Alias gemini and agy to their respective CLIs with explicit auto-login project binding
if command -v agy &> /dev/null; then
    alias agy="PROJECT_ID=\$PROJECT_ID GOOGLE_CLOUD_PROJECT=\$PROJECT_ID agy"
elif command -v antigravity &> /dev/null; then
    alias agy="PROJECT_ID=\$PROJECT_ID GOOGLE_CLOUD_PROJECT=\$PROJECT_ID ELECTRON_DISABLE_SANDBOX=1 xvfb-run -a antigravity --no-sandbox"
fi

if command -v gemini &> /dev/null; then
    alias gemini="gemini -m $GEMINI_MODEL_NAME --yolo"
fi
npx --registry=https://registry.npmjs.org --yes skills install -y -g github.com/google/skills

# --- VS Code Extension Setup (BigQuery / Data tools) ---
echo "Checking for BigQuery querying capabilities..."
JETSKI_EXEC="/opt/jetski-ide/bin/jetski"

# Check if either 'googlecloudtools.datacloud' (pre-installed) or 'google-cloud-tools.bigquery-vscode-extension' is present
installed_extensions=$($JETSKI_EXEC --list-extensions 2>/dev/null)
if ! echo "$installed_extensions" | grep -q "googlecloudtools.datacloud" && ! echo "$installed_extensions" | grep -q "google-cloud-tools.bigquery-vscode-extension"; then
  echo "BigQuery querying extension not found. You can install it from the IDE Extensions gallery."
else
  echo "BigQuery querying capabilities are already enabled."
fi


# Google Drive mount block removed (handled natively on this workstation)
