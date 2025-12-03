import asyncio
import logging
import sys
import os

# Ensure the root directory is in sys.path to allow importing config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google.adk.agents import Agent, LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.genai import types

from config import settings

# --- 1. 配置日志 (Logging Configuration) ---
logger = settings.setup_logging("session_demo_agent")

# --- 2. 配置重试策略 (Retry Configuration) ---
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# --- 3. 定义常量 (Constants) ---
APP_NAME = "SessionDemoApp"
USER_ID = "demo_user"

async def run_session(
    runner_instance: Runner, 
    session_service: InMemorySessionService,
    user_queries: list[str] | str, 
    session_id: str = "default"
):
    """
    Helper function to run queries in a session and display responses.
    Ref: Tutorial Section 1.4
    """
    logger.info(f"--- Starting Session: {session_id} ---")

    # Create or retrieve session
    try:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        logger.debug(f"Created new session: {session_id}")
    except Exception:
        # If session exists, get it
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        logger.debug(f"Retrieved existing session: {session_id}")

    if isinstance(user_queries, str):
        user_queries = [user_queries]

    for query in user_queries:
        print(f"\nUser > {query}")
        query_content = types.Content(role="user", parts=[types.Part(text=query)])

        # Stream agent response
        async for event in runner_instance.run_async(
            user_id=USER_ID, session_id=session.id, new_message=query_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text and text != "None":
                    print(f"Model > {text}")
                    logger.info(f"Model Response: {text[:50]}...")

async def run_phase_1():
    """
    Phase 1: Basic Session Management
    """
    print("🚀 Starting Phase 1: Basic Session Management")

    # --- Step 1: Initialize Services ---
    # InMemorySessionService: Stores conversations in RAM (temporary)
    session_service = InMemorySessionService()
    logger.info("✅ Service initialized: InMemorySessionService")

    # --- Step 2: Create Agent ---
    # 使用基础 Agent，无需特殊工具
    simple_agent = Agent(
        model=Gemini(
            model=settings.DEFAULT_MODEL_NAME,
            api_key=settings.get_api_key(),
            retry_options=retry_config
        ),
        name="SessionBot",
        description="A simple chatbot to demonstrate sessions.",
    )

    # --- Step 3: Configure Runner ---
    # Runner 负责维护对话历史
    runner = Runner(
        agent=simple_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logger.info("✅ Runner configured")

    # --- Step 4: Test Stateful Conversation ---
    # 在同一个 Session 中连续提问，验证上下文保持
    session_id = "session-01"
    print(f"\n📝 [Conversation 1] Testing Context Retention (Session ID: {session_id})")
    
    queries = [
        "Hi, I am Sam! What is the capital of United States?",
        "Hello! What is my name?"  # Agent 应该能记住上一句提到的名字
    ]
    
    await run_session(runner, session_service, queries, session_id)

    # --- Step 5: Verify Forgetfulness (Optional Simulation) ---
    # 模拟重启：创建一个新的 Runner 和 SessionService (相当于重启 App)
    print("\n🔄 [Simulation] Restarting Application (Simulated)...")
    new_session_service = InMemorySessionService()
    new_runner = Runner(
        agent=simple_agent,
        app_name=APP_NAME,
        session_service=new_session_service
    )
    
    # 尝试使用相同的 Session ID 提问
    print(f"\n📝 [Conversation 2] Testing Data Loss after Restart (Session ID: {session_id})")
    await run_session(
        new_runner, 
        new_session_service, 
        "What is my name?", # Agent 应该已经忘记了
        session_id
    )

async def run_phase_2():
    """
    Phase 2: Persistence & Isolation
    """
    print("\n🚀 Starting Phase 2: Persistence & Isolation")
    
    # --- Step 1: Initialize Database Service ---
    # 使用 SQLite 进行持久化存储
    # 注意：SQLAlchemy 的 asyncio 扩展需要使用 aiosqlite 驱动
    db_url = "sqlite+aiosqlite:///my_agent_data.db"
    session_service = DatabaseSessionService(db_url=db_url)
    logger.info(f"✅ Service initialized: DatabaseSessionService ({db_url})")
    
    # --- Step 2: Create Agent & Runner ---
    persistent_agent = LlmAgent(
        model=Gemini(
            model=settings.DEFAULT_MODEL_NAME,
            api_key=settings.get_api_key(),
            retry_options=retry_config
        ),
        name="PersistentBot",
        description="A chatbot with persistent memory.",
    )
    
    runner = Runner(
        agent=persistent_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # --- Step 3: Test Persistence (Run 1) ---
    session_id = "db-session-01"
    print(f"\n📝 [Conversation 1] Teaching Agent a fact (Session ID: {session_id})")
    await run_session(
        runner, 
        session_service, 
        ["Hi, I am Sam! What is the capital of United States?", "Hello! What is my name?"], 
        session_id
    )
    
    # --- Step 4: Simulate Restart & Resume ---
    print("\n🔄 [Simulation] Restarting Application (Re-initializing Service)...")
    # 重新初始化 Service，模拟 App 重启
    # 因为连接的是同一个 SQLite 文件，数据应该还在
    restarted_session_service = DatabaseSessionService(db_url=db_url)
    restarted_runner = Runner(
        agent=persistent_agent,
        app_name=APP_NAME,
        session_service=restarted_session_service
    )
    
    print(f"\n📝 [Conversation 2] Testing Persistence after Restart (Session ID: {session_id})")
    await run_session(
        restarted_runner, 
        restarted_session_service, 
        "What is my name?", # Agent 应该还能记住 "Sam"
        session_id
    )
    
    # --- Step 5: Verify Isolation ---
    # 使用一个新的 Session ID，验证数据隔离
    new_session_id = "db-session-02"
    print(f"\n📝 [Conversation 3] Testing Session Isolation (Session ID: {new_session_id})")
    await run_session(
        restarted_runner, 
        restarted_session_service, 
        "What is my name?", # Agent 应该不知道名字
        new_session_id
    )

async def main():
    # await run_phase_1()
    await run_phase_2()

if __name__ == "__main__":
    asyncio.run(main())
