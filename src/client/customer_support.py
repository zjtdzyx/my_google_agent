import asyncio
import sys
import os
import uuid
import aiohttp

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from config import settings
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 初始化日志
logger = settings.setup_logging("CustomerSupportClient")

async def check_remote_service(url: str) -> bool:
    """Health check for the remote A2A service."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=2) as response:
                if response.status == 200:
                    logger.info(f"✅ Connected to remote agent at: {url}")
                    return True
                else:
                    logger.error(f"❌ Remote agent returned status: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to remote agent: {str(e)}")
        logger.warning("💡 Hint: Is the Product Catalog Service running?")
        return False

async def run_customer_support_flow(user_query: str):
    """
    Orchestrates the interaction between User -> Support Agent -> Remote Catalog Agent.
    """
    # Step 0: Pre-flight check
    if not await check_remote_service(settings.AGENT_CARD_FULL_URL):
        return

    # Step 1: Define Remote Agent (The Proxy)
    remote_catalog_agent = RemoteA2aAgent(
        name="product_catalog_agent",
        description="Remote product catalog service. Use this to look up product details.",
        agent_card=settings.AGENT_CARD_FULL_URL
    )

    # Step 2: Define Local Support Agent (The Consumer)
    retry_config = types.HttpRetryOptions(attempts=3, exp_base=2, initial_delay=1)
    
    support_agent = LlmAgent(
        model=Gemini(model=settings.DEFAULT_MODEL_NAME, retry_options=retry_config),
        name="customer_support_agent",
        description="Customer support assistant.",
        instruction="""
        You are a helpful Customer Support Agent.
        1. Analyze the user's question.
        2. If they ask about a product, ALWAYS use the 'product_catalog_agent' tool to get real data.
        3. Do not guess prices or specs.
        4. Answer politely and concisely.
        """,
        sub_agents=[remote_catalog_agent]
    )

    # Step 3: Session & Runner Setup
    session_service = InMemorySessionService()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    app_name = "support_cli_app"
    user_id = "cli_user"

    await session_service.create_session(
        app_name=app_name, 
        user_id=user_id, 
        session_id=session_id
    )

    runner = Runner(
        agent=support_agent, 
        app_name=app_name, 
        session_service=session_service
    )

    # Step 4: Execution
    logger.info(f"👤 User Query: {user_query}")
    logger.info("🤖 Support Agent is thinking...")
    
    try:
        user_msg = types.Content(parts=[types.Part(text=user_query)])
        
        async for event in runner.run_async(
            user_id=user_id, 
            session_id=session_id, 
            new_message=user_msg
        ):
            if event.is_final_response() and event.content:
                response_text = event.content.parts[0].text
                print("\n" + "="*50)
                print(f"💬 Response:\n{response_text}")
                print("="*50 + "\n")
                
    except Exception as e:
        logger.error(f"Runtime error during agent execution: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        settings.get_api_key()
        query = "Hi, do you have the iPhone 15 Pro in stock? And how much is it?"
        asyncio.run(run_customer_support_flow(query))
    except ValueError as e:
        logger.error(e)
