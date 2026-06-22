import os
import sys
import tarfile
import shutil
import importlib.util
from google.adk.agents import Agent
from google.genai import types
from google.cloud import storage

# Configurations for dynamic loader
DYNAMIC_HOT_RELOAD = os.environ.get("DYNAMIC_HOT_RELOAD", "0") == "1"
bucket_name = os.environ.get("A2A_CARD_BUCKET_NAME")
bundle_blob_path = "live_agents/bq_proxy_bundle.tar.gz"
extract_dir = "/tmp/agent_live_bundle"

# Ensure current directory is in sys.path for cloud imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Try downloading and staging bundle at startup if hot reload is active
if DYNAMIC_HOT_RELOAD and bucket_name:
    print(f"[DynamicLoader] Hot reload active. Fetching bundle from gs://{bucket_name}/{bundle_blob_path}...")
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(bundle_blob_path)
        if blob.exists():
            local_tar = "/tmp/bq_proxy_bundle.tar.gz"
            blob.download_to_filename(local_tar)
            shutil.rmtree(extract_dir, ignore_errors=True)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(local_tar, "r:gz") as tar:
                tar.extractall(path=extract_dir)
            if extract_dir not in sys.path:
                sys.path.insert(0, extract_dir)
            print("[DynamicLoader] Staged bundle successfully loaded in sys.path.")
        else:
            print("[DynamicLoader] No bundle found in GCS. Using pre-baked staged files.")
    except Exception as e:
        print(f"[DynamicLoader] WARNING: Failed to load dynamic bundle: {e}")

# Standard Imports & Setup for local fallback
try:
    from tools import call_claims_agent
except Exception as e:
    import traceback
    err_msg = str(e)
    # Fallback tool
    def call_claims_agent(question: str) -> str:
         return f"Error: The Claims Agent tool is currently unavailable. (Error: {err_msg})"

MODEL = os.environ.get("MODEL_NAME", "gemini-2.0-flash")

# Define the Agent Object (Standard ADK)
real_agent = Agent(
    model=MODEL,
    name="enterprise_data_proxy_agent",
    description="A front-door agent that delegates data-related questions to specialized agents.",
    instruction="""You are a helpful assistant serving as a \
      front door to specialized enterprise data agents. \
      Your primary role is to route user questions about structured \
      data to the appropriate tool (e.g. the `call_claims_agent` tool). \
      The tool will return a JSON payload containing `explanation`, `sql`, `data`, `chart`, and `suggested_questions`. \
      You MUST formulate a beautiful, clean markdown response for the user: \
      1. Present the `explanation` clearly. \
      2. If data is present, present it as a formatted Markdown table. \
      3. If a chart is present in the tool response, generate a visual text-based Unicode bar chart (e.g., using block characters like █ or ░) to represent the chart's data points in your markdown answer so that it renders visually in the chat bubble. \
      4. Include the exact SQL query used in a ```sql code block. \
      5. Include a "Suggested Questions" section listing the suggested questions as bullet points. \
      6. At the very end of your response, append a hidden metadata JSON block inside an HTML comment: \
         <!-- METADATA: {"chart": <chart_dict_or_null>, "suggested_questions": <list_of_questions>} --> \
         where <chart_dict_or_null> is the raw chart dictionary from the tool response (or null) and <list_of_questions> is the list of suggested questions. \
      Do NOT attempt to generate SQL or query data yourself. \
      ALWAYS use the provided tools for data questions. \
      """,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[call_claims_agent]
)

# Wrapper class to support dynamic reloading
class HotReloadProxyAgent(Agent):
    def __init__(self, real_agent):
        init_args = {
            "name": getattr(real_agent, "name", "root_agent"),
            "model": getattr(real_agent, "model", None),
            "instruction": getattr(real_agent, "instruction", None),
            "output_schema": getattr(real_agent, "output_schema", None),
        }
        init_args = {k: v for k, v in init_args.items() if v is not None}
        super().__init__(**init_args)
        self._real_agent = real_agent
        self.sub_agents = getattr(real_agent, "sub_agents", None)
        self.tools = getattr(real_agent, "tools", None)
        self.mode = getattr(real_agent, "mode", None)
        self.code_executor = getattr(real_agent, "code_executor", None)
        self.output_schema = getattr(real_agent, "output_schema", None)

    @property
    def canonical_model(self):
        return getattr(self._real_agent, "canonical_model", None)

    @property
    def canonical_live_model(self):
        return getattr(self._real_agent, "canonical_live_model", None)

    async def run_async(self, *args, **kwargs):
        is_trigger = False
        new_message = kwargs.get("new_message")
        if new_message:
            if hasattr(new_message, "parts"):
                text_content = "".join([p.text for p in new_message.parts if hasattr(p, "text")])
                if text_content.strip() == "__HOT_RELOAD_TRIGGER__":
                    is_trigger = True
            elif isinstance(new_message, str) and new_message.strip() == "__HOT_RELOAD_TRIGGER__":
                is_trigger = True

        if not is_trigger and "message" in kwargs:
            msg = kwargs["message"]
            if isinstance(msg, str) and msg.strip() == "__HOT_RELOAD_TRIGGER__":
                is_trigger = True
            elif hasattr(msg, "parts"):
                text_content = "".join([p.text for p in msg.parts if hasattr(p, "text")])
                if text_content.strip() == "__HOT_RELOAD_TRIGGER__":
                    is_trigger = True

        if not is_trigger:
            for arg in args:
                if isinstance(arg, str) and arg.strip() == "__HOT_RELOAD_TRIGGER__":
                    is_trigger = True
                    break

        if is_trigger:
            print("[DynamicLoader] Hot reload trigger received! Re-downloading bundle and reloading in-memory...")
            try:
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(bundle_blob_path)
                local_tar = "/tmp/bq_proxy_bundle.tar.gz"
                blob.download_to_filename(local_tar)
                
                shutil.rmtree(extract_dir, ignore_errors=True)
                os.makedirs(extract_dir, exist_ok=True)
                with tarfile.open(local_tar, "r:gz") as tar:
                    tar.extractall(path=extract_dir)
                
                if extract_dir not in sys.path:
                    sys.path.insert(0, extract_dir)
                
                # Clear sys.modules cached modules
                for name in list(sys.modules.keys()):
                    if name == "tools" or name.startswith("enterprise_data_proxy_agent") or name == "bundle_agent":
                        del sys.modules[name]
                
                # Load the new bundle's agent
                import importlib.util
                spec = importlib.util.spec_from_file_location("bundle_agent", os.path.join(extract_dir, "agent.py"))
                bundle_agent = importlib.util.module_from_spec(spec)
                sys.modules["bundle_agent"] = bundle_agent
                spec.loader.exec_module(bundle_agent)
                
                self._real_agent = bundle_agent.real_agent
                self.sub_agents = getattr(self._real_agent, "sub_agents", None)
                self.tools = getattr(self._real_agent, "tools", None)
                self.output_schema = getattr(self._real_agent, "output_schema", None)
                
                print("[DynamicLoader] Hot reload completed successfully in-memory!")
                yield "Hot reload completed successfully in-memory!"
                return
            except Exception as e:
                print(f"[DynamicLoader] Hot reload failed: {e}")
                yield f"Hot reload failed: {e}"
                return

        async for event in self._real_agent.run_async(*args, **kwargs):
            yield event

if DYNAMIC_HOT_RELOAD and os.path.exists(os.path.join(extract_dir, "agent.py")):
    try:
        spec = importlib.util.spec_from_file_location("bundle_agent", os.path.join(extract_dir, "agent.py"))
        bundle_agent = importlib.util.module_from_spec(spec)
        sys.modules["bundle_agent"] = bundle_agent
        spec.loader.exec_module(bundle_agent)
        
        root_agent = HotReloadProxyAgent(bundle_agent.real_agent)
        print("[DynamicLoader] Loaded real_agent from GCS bundle.")
    except Exception as e:
        print(f"[DynamicLoader] Failed to load from bundle at startup, using pre-baked: {e}")
        root_agent = HotReloadProxyAgent(real_agent)
elif DYNAMIC_HOT_RELOAD:
    root_agent = HotReloadProxyAgent(real_agent)
else:
    root_agent = real_agent
