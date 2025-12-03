import asyncio
import os
import sys
import logging
from typing import Dict, Any

# 将项目根目录添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目配置
from config import settings

# 导入 ADK 组件
from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

# --- 1. 工程化配置 ---
logger = settings.setup_logging("LoopDemo")

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

# --- 2. 定义循环控制工具 (Loop Control Tool) ---

def exit_loop():
    """
    这是一个特殊的控制函数。
    当 RefinerAgent 认为文章已经完美时，调用此函数来终止循环。
    """
    logger.info("🎯 收到 APPROVED 信号，正在退出循环...")
    return {"status": "approved", "message": "Story approved. Exiting refinement loop."}

# --- 3. 定义循环内的 Agent (Agents inside the Loop) ---

def create_initial_writer() -> Agent:
    """
    循环外的 Agent：负责写第一稿。
    只运行一次。
    """
    logger.info("正在创建 InitialWriterAgent...")
    return Agent(
        name="InitialWriterAgent",
        model=create_model(),
        instruction="""
        根据用户的提示，写一个短篇故事的初稿（约 100-150 字）。
        只输出故事内容，不要有任何开场白。
        """,
        output_key="current_story" # 初始状态
    )

def create_critic_agent() -> Agent:
    """
    循环内的 Agent 1：批评家。
    负责提出修改意见或批准通过。
    """
    logger.info("正在创建 CriticAgent...")
    return Agent(
        name="CriticAgent",
        model=create_model(),
        instruction="""
        你是一位严厉但建设性的故事评论家。请审阅以下故事：
        
        Story: {current_story}
        
        请评估情节、人物和节奏。
        - 如果故事写得很好且完整，你必须回复确切的短语："APPROVED"
        - 否则，请提供 2-3 条具体的修改建议。
        """,
        output_key="critique" # 将意见存入状态
    )

def create_refiner_agent() -> Agent:
    """
    循环内的 Agent 2：精炼者。
    负责根据意见修改故事，或者触发退出机制。
    """
    logger.info("正在创建 RefinerAgent...")
    
    # 将退出函数封装为工具
    exit_tool = FunctionTool(exit_loop)
    
    return Agent(
        name="RefinerAgent",
        model=create_model(),
        instruction="""
        你是一位故事精炼者。你拥有当前的故事草稿和评论家的意见。
        
        Story Draft: {current_story}
        Critique: {critique}
        
        你的任务是分析评论：
        1. 如果评论完全是 "APPROVED"，你必须调用 `exit_loop` 工具，不做其他事情。
        2. 否则，根据评论意见重写故事，使其更完美。
        """,
        output_key="current_story", # 覆盖旧的故事版本，实现状态更新
        tools=[exit_tool] # 赋予退出循环的能力
    )

# --- 4. 组装循环系统 (Loop System Architecture) ---

def create_refinement_system() -> SequentialAgent:
    """
    架构设计:
    [Initial Writer] -> [Loop: Critic -> Refiner]
    
    1. Initial Writer 先跑一次，生成初稿。
    2. LoopAgent 开始运行：
       - Critic 提意见
       - Refiner 修改 (或决定退出)
       - 如此往复，直到 Refiner 调用 exit_loop 或达到最大迭代次数。
    """
    logger.info("正在组装 Refinement System...")
    
    # 1. 定义循环体
    refinement_loop = LoopAgent(
        name="StoryRefinementLoop",
        sub_agents=[create_critic_agent(), create_refiner_agent()],
        max_iterations=3 # 安全机制：防止死循环，最多修 3 次
    )
    
    # 2. 串联：初稿 -> 循环修稿
    return SequentialAgent(
        name="StoryPipeline",
        sub_agents=[create_initial_writer(), refinement_loop]
    )

# --- 5. 运行逻辑 ---

async def main():
    system = create_refinement_system()
    runner = InMemoryRunner(agent=system)
    
    prompt = "写一个关于灯塔守护者发现一张发光地图的短篇故事"
    logger.info(f"开始执行循环优化任务: {prompt}")
    
    try:
        # run_debug 可以看到每一轮循环的迭代过程
        response = await runner.run_debug(prompt)
        
        print("\n" + "="*50)
        print("📖 最终打磨的故事 (Final Polished Story)")
        print("="*50)
        
        # 提取最终结果逻辑需要适配 Loop 的输出结构
        # 通常最后一步是 Refiner 的输出（如果是修改版）或 exit_loop 的结果
        # 我们这里简单打印最后一步的文本
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
