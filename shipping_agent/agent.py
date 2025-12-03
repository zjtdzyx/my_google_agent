import os
import logging
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.tools.function_tool import FunctionTool

# Import project settings
try:
    from config.settings import get_api_key, setup_logging, DEFAULT_MODEL_NAME
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import get_api_key, setup_logging, DEFAULT_MODEL_NAME

from .tools import place_shipping_order

# Setup Logging
logger = setup_logging("shipping_agent")

# Setup API Key
try:
    os.environ["GOOGLE_API_KEY"] = get_api_key()
except Exception as e:
    logger.error(f"Failed to set API Key: {e}")

# --- 1. Create Agent ---
shipping_agent = LlmAgent(
    name="shipping_agent",
    model=Gemini(model=DEFAULT_MODEL_NAME),
    instruction="""You are a shipping coordinator assistant.
  
  When users request to ship containers:
   1. Use the place_shipping_order tool with the number of containers and destination.
   2. If the order status is 'pending', inform the user that approval is required.
   3. After receiving the final result (approved or rejected), provide a clear summary.
   4. Keep responses concise.
  """,
    tools=[FunctionTool(func=place_shipping_order)],
)

# --- 2. Create Resumable App ---
# The App wrapper is CRITICAL for saving state during the pause
shipping_app = App(
    name="shipping_coordinator",
    root_agent=shipping_agent,
    resumability_config=ResumabilityConfig(is_resumable=True), # Enable persistence
)

# --- 3. Create Session Service & Runner ---
session_service = InMemorySessionService()

shipping_runner = Runner(
    app=shipping_app,  # Pass the App, not the Agent
    session_service=session_service,
)

logger.info("✅ Shipping Agent & Runner initialized.")
