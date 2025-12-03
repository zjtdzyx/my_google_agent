import asyncio
import os
import sys
import logging
from typing import List

# 将项目根目录添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目配置
from config import settings

# 导入 ADK 组件
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search
from google.genai import types

# --- 1. 工程化配置 ---
logger = settings.setup_logging("ParallelDemo")

try:
    settings.get_api_key()
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

RETRY_CONFIG = types.HttpRetryOptions(
    attempts=3,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503]
)

MODEL_NAME = settings.DEFAULT_MODEL_NAME

def create_model() -> Gemini:
    return Gemini(model=MODEL_NAME, retry_options=RETRY_CONFIG)

# --- 2. 定义并行工作者 (Parallel Workers) ---

def create_tech_researcher() -> Agent:
    """
    工作者 1: 科技研究员
    """
    logger.info("正在创建 TechResearcher...")
    return Agent(
        name="TechResearcher",
        model=create_model(),
        instruction="""
        请研究最新的 AI (人工智能) 和 ML (机器学习) 趋势。
        列出 3 个关键发展，涉及的主要公司以及潜在影响。
        保持报告简洁（约 100 字）。
        """,
        tools=[google_search],
        output_key="tech_research" # 独立的状态 Key
    )

def create_health_researcher() -> Agent:
    """
    工作者 2: 健康医疗研究员
    """
    logger.info("正在创建 HealthResearcher...")
    return Agent(
        name="HealthResearcher",
        model=create_model(),
        instruction="""
        请研究最近的医疗突破。
        列出 3 个重大进展，其实际应用以及预计时间表。
        保持报告简洁（约 100 字）。
        """,
        tools=[google_search],
        output_key="health_research" # 独立的状态 Key
    )

def create_finance_researcher() -> Agent:
    """
    工作者 3: 金融科技研究员
    """
    logger.info("正在创建 FinanceResearcher...")
    return Agent(
        name="FinanceResearcher",
        model=create_model(),
        instruction="""
        请研究当前的金融科技 (Fintech) 趋势。
        列出 3 个关键趋势，市场影响以及未来展望。
        保持报告简洁（约 100 字）。
        """,
        tools=[google_search],
        output_key="finance_research" # 独立的状态 Key
    )

# --- 3. 定义聚合器 (Aggregator) ---

def create_aggregator_agent() -> Agent:
    """
    聚合器: 汇总所有并行任务的结果
    """
    logger.info("正在创建 AggregatorAgent...")
    return Agent(
        name="AggregatorAgent",
        model=create_model(),
        # 关键点: 同时引用所有并行 Agent 的 output_key
        instruction="""
        请将以下三个领域的研究发现汇总成一份高管简报 (Executive Summary)：

        **科技趋势 (Technology):**
        {tech_research}
        
        **医疗突破 (Health):**
        {health_research}
        
        **金融创新 (Finance):**
        {finance_research}
        
        任务要求：
        1. 寻找这三个领域之间的共同主题或潜在联系（例如 AI 在医疗或金融中的应用）。
        2. 提炼出最重要的核心要点。
        3. 最终简报应在 200 字左右，适合快速阅读。
        """,
        output_key="executive_summary"
    )

# --- 4. 组装并行系统 (Parallel System Architecture) ---

def create_parallel_system() -> SequentialAgent:
    """
    架构设计:
    [Parallel Team] -> [Aggregator]
    
    Parallel Team 内部包含三个并发运行的研究员。
    整个系统被包裹在一个 SequentialAgent 中，确保先完成所有研究，再进行汇总。
    """
    logger.info("正在组装 Parallel System...")
    
    # 1. 创建并行组
    parallel_team = ParallelAgent(
        name="ParallelResearchTeam",
        sub_agents=[
            create_tech_researcher(),
            create_health_researcher(),
            create_finance_researcher()
        ]
    )
    
    # 2. 创建聚合器
    aggregator = create_aggregator_agent()
    
    # 3. 串联: 并行组 -> 聚合器
    return SequentialAgent(
        name="ResearchSystem",
        sub_agents=[parallel_team, aggregator]
    )

# --- 5. 运行逻辑 ---

async def main():
    system = create_parallel_system()
    runner = InMemoryRunner(agent=system)
    
    task = "生成一份关于科技、医疗和金融领域的每日高管简报"
    logger.info(f"开始执行并行任务: {task}")
    
    try:
        # run_debug 会显示并行执行的日志
        response = await runner.run_debug(task)
        
        print("\n" + "="*50)
        print("📊 每日高管简报 (Executive Briefing)")
        print("="*50)
        
        if isinstance(response, list) and response:
            last_step = response[-1]
            if hasattr(last_step, 'text'):
                print(last_step.text)
            else:
                print(f"Step Result: {last_step}")
        else:
            print(getattr(response, 'text', str(response)))
            
        print("="*50)
        
    except Exception as e:
        logger.error(f"系统执行失败: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
