import asyncio
import logging
import sys
import os

# Ensure the root directory is in sys.path to allow importing config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import load_memory
from google.genai import types

from config import settings

# --- 1. 配置日志 (Logging Configuration) ---
logger = settings.setup_logging("memory_demo_agent")

# --- 2. 配置重试策略 (Retry Configuration) ---
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# --- 3. 定义常量 (Constants) ---
APP_NAME = "MemoryDemoApp"
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

async def main():
    """
    Phase 1: Infrastructure Setup & Manual Memory Workflow
    """
    print("🚀 Starting Phase 1: Memory Infrastructure Setup")

    # --- Step 1: Initialize Services ---
    # MemoryService: 长期知识存储 (Long-term knowledge)
    # SessionService: 短期会话状态 (Short-term conversation state)
    memory_service = InMemoryMemoryService()
    session_service = InMemorySessionService()
    logger.info("✅ Services initialized: InMemoryMemoryService, InMemorySessionService")

    # --- Step 2: Create Agent ---
    # 初始 Agent 不带 Memory 工具，用于演示手动摄入
    simple_agent = LlmAgent(
        model=Gemini(
            model=settings.DEFAULT_MODEL_NAME,
            api_key=settings.get_api_key(),
            retry_options=retry_config
        ),
        name="SimpleMemoryAgent",
        instruction="Answer user questions in simple words.",
        # 注意：这里暂时没有添加 load_memory 工具，我们先演示数据摄入
    )

    # --- Step 3: Configure Runner ---
    # Runner 将 Agent, Session, Memory 连接在一起
    runner = Runner(
        agent=simple_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service, 
    )
    logger.info("✅ Runner configured with Session and Memory services")

    # --- Step 4: Ingest Data (Manual) ---
    # 场景：告诉 Agent 一个事实，然后手动存入 Memory
    session_id_1 = "conversation-01"
    print(f"\n📝 [Conversation 1] Teaching Agent a fact (Session ID: {session_id_1})")
    await run_session(
        runner, 
        session_service,
        "My favorite color is Blue-Green. Can you write a short sentence about it?", 
        session_id_1
    )

    # 关键步骤：手动将 Session 数据转存到 Memory
    # 在生产环境中，这一步通常由 Callback 自动完成 (Phase 3)
    session_obj = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id_1
    )
    await memory_service.add_session_to_memory(session_obj)
    print("💾 [System] Session manually added to Memory!")

    # --- Step 5: Verify Retrieval (Manual Search) ---
    # 不通过 Agent，直接查询 Memory 服务，验证数据是否已持久化
    query = "What is the user's favorite color?"
    print(f"\n🔍 [System] Verifying Memory with query: '{query}'")
    
    search_response = await memory_service.search_memory(
        app_name=APP_NAME, user_id=USER_ID, query=query
    )

    if search_response.memories:
        print(f"✅ Found {len(search_response.memories)} relevant memories:")
        for mem in search_response.memories:
            # 提取记忆内容
            content = mem.content.parts[0].text if mem.content.parts else "No text"
            print(f"   - [{mem.author}]: {content.strip()[:100]}...")
    else:
        print("❌ No memories found. Something went wrong.")

    # --- Step 6: Agent Retrieval (Reactive) ---
    # 为了让 Agent 能用到记忆，我们需要给它 load_memory 工具
    # 重新创建一个带工具的 Agent
    print(f"\n🤖 [Conversation 2] Testing Agent Retrieval (New Session)")
    
    agent_with_memory = LlmAgent(
        model=Gemini(
            model=settings.DEFAULT_MODEL_NAME,
            api_key=settings.get_api_key(),
            retry_options=retry_config
        ),
        name="AgentWithMemory",
        instruction="Answer user questions. Use load_memory tool if you need to recall past conversations.",
        tools=[load_memory] # <--- 赋予 Agent 查阅记忆的能力
    )

    # 更新 Runner 使用新 Agent
    runner_with_memory = Runner(
        agent=agent_with_memory,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service
    )

    # 在一个全新的 Session 中提问，测试跨会话记忆
    session_id_2 = "conversation-02"
    await run_session(
        runner_with_memory,
        session_service,
        "What is my favorite color?", # Agent 应该调用 load_memory 找到答案
        session_id_2
    )

if __name__ == "__main__":
    asyncio.run(main())
