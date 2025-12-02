import asyncio
import logging
import os
import uuid
import certifi
from typing import Optional
from dotenv import load_dotenv

# --- 0. 关键修复：强制设置 SSL 证书路径 ---
# 这解决了 Windows 下 "FileNotFoundError: [Errno 2] No such file or directory" 的 SSL 问题
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# 加载 .env 文件
load_dotenv()

import aiohttp
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# --- 1. 配置日志 (Logging Setup) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("CustomerSupportClient")

# --- 2. 配置常量 (Configuration) ---
REMOTE_SERVICE_URL = "http://localhost:8001"
AGENT_CARD_URL = f"{REMOTE_SERVICE_URL}{AGENT_CARD_WELL_KNOWN_PATH}"

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
        logger.warning("💡 Hint: Is 'product_catalog_service.py' running in another terminal?")
        return False

# --- 3. 构建客户端 Agent (Agent Construction) ---
async def run_customer_support_flow(user_query: str):
    """
    Orchestrates the interaction between User -> Support Agent -> Remote Catalog Agent.
    """
    
    # Step 0: Pre-flight check
    if not await check_remote_service(AGENT_CARD_URL):
        return

    # Step 1: Define Remote Agent (The Proxy)
    # 这是一个“代理”，它负责将请求转发给我们在端口 8001 运行的服务
    remote_catalog_agent = RemoteA2aAgent(
        name="product_catalog_agent",
        description="Remote product catalog service. Use this to look up product details.",
        agent_card=AGENT_CARD_URL
    )

    # Step 2: Define Local Support Agent (The Consumer)
    retry_config = types.HttpRetryOptions(attempts=3, exp_base=2, initial_delay=1)
    
    support_agent = LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
        name="customer_support_agent",
        description="Customer support assistant.",
        instruction="""
        You are a helpful Customer Support Agent.
        1. Analyze the user's question.
        2. If they ask about a product, ALWAYS use the 'product_catalog_agent' tool to get real data.
        3. Do not guess prices or specs.
        4. Answer politely and concisely.
        """,
        sub_agents=[remote_catalog_agent]  # 关键：将远程 Agent 注册为子 Agent
    )

    # Step 3: Session & Runner Setup
    session_service = InMemorySessionService()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    app_name = "support_cli_app"
    user_id = "cli_user"

    # 创建会话
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
    logger.info("🤖 Support Agent is thinking... (may call remote agent)")
    
    try:
        user_msg = types.Content(parts=[types.Part(text=user_query)])
        
        async for event in runner.run_async(
            user_id=user_id, 
            session_id=session_id, 
            new_message=user_msg
        ):
            # 只处理最终响应，忽略中间的思考过程 (Thought Trace)
            if event.is_final_response() and event.content:
                response_text = event.content.parts[0].text
                print("\n" + "="*50)
                print(f"💬 Response:\n{response_text}")
                print("="*50 + "\n")
                
    except Exception as e:
        logger.error(f"Runtime error during agent execution: {e}", exc_info=True)

# --- 4. 入口点 (Entry Point) ---
if __name__ == "__main__":
    # 检查 API Key
    if "GOOGLE_API_KEY" not in os.environ:
        logger.error("❌ GOOGLE_API_KEY is missing from environment variables.")
    else:
        # 示例查询
        query = "Hi, do you have the iPhone 15 Pro in stock? And how much is it?"
        asyncio.run(run_customer_support_flow(query))
