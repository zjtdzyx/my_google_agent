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
from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

# --- 1. 工程化配置 ---
logger = settings.setup_logging("SequentialDemo")

# 确保 API Key 存在
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

# --- 2. 定义流水线节点 (Pipeline Nodes) ---

def create_outline_agent() -> Agent:
    """
    节点 1: 大纲生成器
    输入: 用户的主题 (User Prompt)
    输出: blog_outline
    """
    logger.info("正在创建 OutlineAgent...")
    return Agent(
        name="OutlineAgent",
        model=create_model(),
        instruction="""
        你是一个专业的博客策划。
        请为给定的主题创建一个详细的博客大纲。
        
        大纲应包含：
        1. 一个吸引人的标题
        2. 引人入胜的开头 (Hook)
        3. 3-5 个主要章节，每章包含 2-3 个要点
        4. 总结与行动号召 (Call to Action)
        """,
        output_key="blog_outline" # 下游 Agent 将通过这个 key 读取内容
    )

def create_writer_agent() -> Agent:
    """
    节点 2: 内容撰写者
    输入: blog_outline (来自上一节点)
    输出: blog_draft
    """
    logger.info("正在创建 WriterAgent...")
    return Agent(
        name="WriterAgent",
        model=create_model(),
        # 关键点: 使用 {blog_outline} 占位符自动注入上下文
        instruction="""
        请严格按照以下大纲撰写一篇 400 字左右的博客文章：
        
        {blog_outline}
        
        风格要求：
        - 语气专业但亲切
        - 使用 Markdown 格式
        - 确保逻辑通顺
        """,
        output_key="blog_draft"
    )

def create_editor_agent() -> Agent:
    """
    节点 3: 编辑与润色
    输入: blog_draft (来自上一节点)
    输出: final_blog
    """
    logger.info("正在创建 EditorAgent...")
    return Agent(
        name="EditorAgent",
        model=create_model(),
        # 关键点: 使用 {blog_draft} 获取草稿
        instruction="""
        你是一位资深主编。请审阅并润色以下博客草稿：
        
        {blog_draft}
        
        任务：
        1. 修正语法和拼写错误。
        2. 优化句子结构，使其更流畅。
        3. 确保文章结构清晰，标题层级正确。
        4. 输出最终定稿版本。
        """,
        output_key="final_blog"
    )

# --- 3. 定义顺序流水线 (Sequential Pipeline) ---

def create_blog_pipeline() -> SequentialAgent:
    """
    将三个 Agent 串联成一条固定的流水线。
    """
    logger.info("正在组装 Sequential Pipeline...")
    
    outline_agent = create_outline_agent()
    writer_agent = create_writer_agent()
    editor_agent = create_editor_agent()
    
    return SequentialAgent(
        name="BlogPipeline",
        # 顺序非常重要：Outline -> Writer -> Editor
        sub_agents=[outline_agent, writer_agent, editor_agent]
    )

# --- 4. 运行逻辑 ---

async def main():
    pipeline = create_blog_pipeline()
    runner = InMemoryRunner(agent=pipeline)
    
    topic = "多智能体系统(Multi-Agent Systems)如何改变软件开发"
    logger.info(f"开始执行流水线任务: {topic}")
    
    try:
        # 使用 run_debug 查看每一步的执行情况
        response = await runner.run_debug(topic)
        
        print("\n" + "="*50)
        print("📝 最终博客文章 (Final Blog Post)")
        print("="*50)
        
        # 尝试提取最终结果
        if isinstance(response, list) and response:
            # 在 SequentialAgent 中，最后一步通常是最后一个子 Agent 的输出
            last_step = response[-1]
            # 打印最后一步的文本内容
            if hasattr(last_step, 'text'):
                print(last_step.text)
            else:
                print(f"Step Result: {last_step}")
        else:
            print(getattr(response, 'text', str(response)))
            
        print("="*50)
        
    except Exception as e:
        logger.error(f"流水线执行失败: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
