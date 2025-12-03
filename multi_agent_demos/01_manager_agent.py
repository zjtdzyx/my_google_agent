import asyncio
import os
import sys
import logging
from typing import Dict, Any

# 将项目根目录添加到 sys.path，以便导入 config 模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目配置
from config import settings

# 导入 ADK 组件
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool, google_search
from google.genai import types

# --- 1. 工程化配置 (Logging & Config) ---
# 使用统一的日志配置
logger = settings.setup_logging("ManagerDemo")

# 确保 API Key 存在
try:
    settings.get_api_key()
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

# 配置重试策略 (Production Best Practice: Handle Transient Errors)
RETRY_CONFIG = types.HttpRetryOptions(
    attempts=3,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503]
)

# 通用模型配置
MODEL_NAME = settings.DEFAULT_MODEL_NAME

def create_model() -> Gemini:
    return Gemini(model=MODEL_NAME, retry_options=RETRY_CONFIG)

# --- 2. 定义专家智能体 (Specialized Agents) ---

def create_research_agent() -> Agent:
    """
    创建一个专注于搜索信息的智能体。
    """
    logger.info("正在创建 ResearchAgent...")
    return Agent(
        name="ResearchAgent",
        model=create_model(),
        # 明确的指令：只做搜索，不发散
        instruction="""
        你是一个专业的搜索助手。
        你的任务是使用 Google Search 工具收集关于给定主题的 2-3 个相关且可信的信息源。
        找到信息后，请列出关键发现并附上来源引用。
        不要尝试自己编造信息，必须依赖搜索结果。
        """,
        tools=[google_search], # 赋予搜索能力
        output_key="research_findings" # 将结果存储到共享状态的这个 key 中
    )

def create_summarizer_agent() -> Agent:
    """
    创建一个专注于总结文本的智能体。
    """
    logger.info("正在创建 SummarizerAgent...")
    return Agent(
        name="SummarizerAgent",
        model=create_model(),
        # 指令中引用 {research_findings}，这是上游 Agent 的输出
        instruction="""
        请阅读提供的研究发现：{research_findings}。
        
        任务要求：
        1. 将关键点总结为一个简洁的要点列表 (Bulleted List)。
        2. 突出 3-5 个最重要的见解。
        3. 保持客观，不要添加原文没有的观点。
        """,
        output_key="final_summary"
    )

# --- 3. 定义编排器 (Orchestrator / Manager) ---

def create_manager_agent(researcher: Agent, summarizer: Agent) -> Agent:
    """
    创建一个管理者智能体，它将其他 Agent 作为工具来调用。
    """
    logger.info("正在创建 ManagerAgent (Root)...")
    
    # 将子 Agent 包装为 Tool
    research_tool = AgentTool(researcher)
    summarizer_tool = AgentTool(summarizer)
    
    return Agent(
        name="ResearchCoordinator",
        model=create_model(),
        # 编排指令：告诉 Manager 如何使用它的工具
        instruction="""
        你是一个研究协调员，负责通过结构化的工作流回答用户的问题。
        
        你的工作流程如下：
        1. **启动研究**：首先调用 `ResearchAgent` 工具，针对用户的主题收集信息。
        2. **总结发现**：收到研究结果后，调用 `SummarizerAgent` 工具生成简洁的总结。
        3. **最终回复**：将总结结果直接展示给用户。
        
        请严格按照此顺序执行，不要跳过步骤。
        """,
        tools=[research_tool, summarizer_tool] # 赋予调用子 Agent 的能力
    )

# --- 4. 运行逻辑 (Execution) ---

async def main():
    # 1. 实例化组件
    researcher = create_research_agent()
    summarizer = create_summarizer_agent()
    manager = create_manager_agent(researcher, summarizer)
    
    # 2. 创建运行器
    runner = InMemoryRunner(agent=manager)
    
    # 3. 定义用户查询
    user_query = "量子计算在药物研发中的最新应用是什么？"
    logger.info(f"开始执行任务: {user_query}")
    
    try:
        # 4. 运行并获取结果
        # run_debug 会打印详细的执行步骤，适合开发阶段
        response = await runner.run(user_query)
        
        print("\n" + "="*50)
        print("🤖 最终执行结果")
        print("="*50)
        print(response.text)
        print("="*50)
        
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}", exc_info=True)

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
