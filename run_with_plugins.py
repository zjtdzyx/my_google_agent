import asyncio
import sys
import os

# Ensure root directory is in sys.path
sys.path.append(os.path.dirname(__file__))

from google.adk.runners import InMemoryRunner
from google.adk.plugins.logging_plugin import LoggingPlugin
from src.plugins.telemetry_plugin import TelemetryPlugin  # <--- Import custom plugin
from research_agent.agent import root_agent
from config import settings

# 配置日志
logger = settings.setup_logging("runner")

async def main():
    logger.info("🚀 Starting Agent with LoggingPlugin & TelemetryPlugin...")
    
    # 初始化 TelemetryPlugin 实例，以便后续获取统计数据
    telemetry = TelemetryPlugin()

    # 初始化 Runner
    # 关键点：我们将 LoggingPlugin 注入到 Runner 中
    # 这会自动捕获所有的 Agent 交互、工具调用和 LLM 请求
    runner = InMemoryRunner(
        agent=root_agent,
        plugins=[
            LoggingPlugin(),
            telemetry  # <--- Add custom plugin
        ]
    )

    query = "Find recent papers on quantum computing"
    logger.info(f"👤 User Query: {query}")

    # 使用 run_debug 可以看到更详细的流式输出，但在生产中通常使用 run
    # 这里我们演示 run_debug 以便在控制台看到效果
    response = await runner.run_debug(query)
    
    logger.info("✅ Agent Execution Completed")
    
    # 打印统计摘要
    print(telemetry.get_summary())
    # 注意：InMemoryRunner.run_debug 返回的是最后的响应对象或文本
    # 具体返回类型取决于 ADK 版本，通常直接打印即可
    # print(f"🤖 Agent Response: {response}")

if __name__ == "__main__":
    # Windows 下 asyncio 的常见兼容性设置
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())
