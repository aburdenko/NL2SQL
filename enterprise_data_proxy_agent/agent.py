import os
import sys
from google.adk.agents import Agent
from google.genai import types

# Ensure current directory is in sys.path for cloud imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from tools import call_claims_agent
except Exception as e:
    import traceback
    err_msg = str(e)
    # Fallback tool
    def call_claims_agent(question: str) -> str:
         return f"Error: The Claims Agent tool is currently unavailable. (Error: {err_msg})"

MODEL = "gemini-2.0-flash"

# Define the Agent Object (Standard ADK)
root_agent = Agent(
    model=MODEL,
    name="enterprise_data_proxy_agent",
    description="A front-door agent that delegates data-related questions to specialized agents.",
    instruction="""You are a helpful assistant serving as a \
      front door to specialized enterprise data agents. \
      Your primary role is to route user questions about structured \
      data to the appropriate tool (e.g. the `call_claims_agent` tool). \
      Present the tool's output clearly to the user. \
      CRITICAL: You MUST include the exact SQL query that was used to fetch the data in your final response to the user. \
      Do NOT attempt to generate SQL or query data yourself. \
      ALWAYS use the provided tools for data questions. \
      """,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[call_claims_agent]
)
