import asyncio
import uuid
import logging
from google.genai import types

# Import from local modules
from .agent import shipping_runner, session_service

logger = logging.getLogger("shipping_agent.workflow")

# --- Helper Functions ---

def check_for_approval(events):
    """
    检查事件流中是否包含 'adk_request_confirmation' 事件。
    如果存在，说明 Agent 请求暂停并等待审批。
    """
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_confirmation"
                ):
                    return {
                        "approval_id": part.function_call.id,
                        "invocation_id": event.invocation_id, # 关键：用于恢复执行的 ID
                        "args": part.function_call.args
                    }
    return None

def create_approval_response(approval_info, approved: bool):
    """
    构造审批结果消息。
    """
    confirmation_response = types.FunctionResponse(
        id=approval_info["approval_id"],
        name="adk_request_confirmation",
        response={"confirmed": approved},
    )
    return types.Content(
        role="user", parts=[types.Part(function_response=confirmation_response)]
    )

def print_agent_response(events):
    """打印 Agent 的文本回复"""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"🤖 Agent > {part.text}")

# --- Main Workflow Logic ---

async def run_shipping_workflow(query: str, auto_approve: bool = True):
    """
    运行完整的航运审批工作流。
    """
    print(f"\n{'='*60}")
    print(f"👤 User > {query}")
    
    # 1. 创建新会话
    session_id = f"order_{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name="shipping_coordinator", user_id="test_user", session_id=session_id
    )
    
    query_content = types.Content(role="user", parts=[types.Part(text=query)])
    events = []

    # 2. 第一阶段执行：发送用户请求
    logger.info("▶️ Starting execution...")
    async for event in shipping_runner.run_async(
        user_id="test_user", session_id=session_id, new_message=query_content
    ):
        events.append(event)
        # 实时打印回复
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"🤖 Agent > {part.text}")

    # 3. 检查是否暂停
    approval_info = check_for_approval(events)

    if approval_info:
        # --- 暂停状态 ---
        print(f"\n⏸️  Workflow PAUSED for approval.")
        print(f"   Details: {approval_info.get('args')}")
        
        # 模拟人工决策
        decision = "APPROVE ✅" if auto_approve else "REJECT ❌"
        print(f"🤔 Human Decision: {decision}\n")

        # 4. 第二阶段执行：恢复 (Resume)
        # 使用相同的 session_id 和之前保存的 invocation_id
        logger.info(f"▶️ Resuming execution with invocation_id={approval_info['invocation_id']}...")
        
        resume_message = create_approval_response(approval_info, auto_approve)
        
        async for event in shipping_runner.run_async(
            user_id="test_user",
            session_id=session_id,
            new_message=resume_message, # 传入审批结果
            invocation_id=approval_info["invocation_id"], # 告诉 ADK 这是一个恢复操作
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"🤖 Agent > {part.text}")
    else:
        logger.info("✅ Workflow completed without interruption.")

    print(f"{'='*60}\n")

async def main():
    # Demo 1: 小订单 (自动通过)
    await run_shipping_workflow("Ship 3 containers to Singapore")

    # Demo 2: 大订单 (模拟人工批准)
    await run_shipping_workflow("Ship 10 containers to Rotterdam", auto_approve=True)

    # Demo 3: 大订单 (模拟人工拒绝)
    await run_shipping_workflow("Ship 8 containers to Los Angeles", auto_approve=False)

if __name__ == "__main__":
    asyncio.run(main())
