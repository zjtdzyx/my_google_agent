import asyncio
import logging
import shutil
import os
import base64

# ADK Imports
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Project Config
# 确保你的 PYTHONPATH 包含项目根目录，或者在根目录下运行此脚本
try:
    from config.settings import get_api_key, setup_logging, DEFAULT_MODEL_NAME
except ImportError:
    # Fallback for direct execution if path not set
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import get_api_key, setup_logging, DEFAULT_MODEL_NAME

# --- 1. Setup Logging ---
# 强制开启 DEBUG 级别日志，以便查看 MCP 协议的原始 JSON-RPC 通信
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("mcp_agent")
logger.setLevel(logging.DEBUG)

# 同时调整 google.adk 的日志级别
logging.getLogger("google.adk").setLevel(logging.DEBUG)
logging.getLogger("google.adk.tools.mcp_tool").setLevel(logging.DEBUG)

async def main():
    """
    运行 MCP Demo Agent。
    演示如何连接到外部 MCP Server (@modelcontextprotocol/server-everything) 并调用工具。
    """
    logger.info("🚀 Starting MCP Demo Agent...")

    # --- 2. Pre-flight Checks ---
    # 检查 node 是否安装
    node_path = shutil.which("node")
    if not node_path:
        logger.error("❌ 'node' not found in PATH. Please install Node.js.")
        return
    logger.info(f"✅ Found node at: {node_path}")

    # 查找全局安装的 server-everything 路径
    # 注意：这里假设用户使用 pnpm/npm 全局安装了包
    # Windows 下通常在 %APPDATA%\npm\node_modules 或类似路径
    # 为了稳健，我们尝试通过 npm list -g 获取路径，或者让用户手动指定
    # 这里我们使用一个更通用的方法：通过 npx --no-install 直接执行，但加上 shell=True (仅限 Windows)
    
    # --- Environment Fixes for Windows ---
    os.environ["PYTHONUTF8"] = "1"
    os.environ["NODE_OPTIONS"] = "--no-warnings"

    try:
        api_key = get_api_key()
        os.environ["GOOGLE_API_KEY"] = api_key
    except ValueError as e:
        logger.error(f"❌ Configuration Error: {e}")
        return

    # --- 3. Configure MCP Toolset ---
    logger.info("🔌 Connecting to MCP Server: @modelcontextprotocol/server-everything...")
    
    try:
        # 方案 C (核选项): 直接使用 node 运行目标 JS 文件
        # 绕过所有 npx/cmd 的中间层，直接建立 Python <-> Node 管道
        
        # 根据 pnpm list -g 输出构建绝对路径
        # 注意：这里硬编码了路径用于调试，生产环境应动态获取
        server_path = r"C:\Users\13007\AppData\Local\pnpm\global\5\.pnpm\@modelcontextprotocol+server-everything@2025.11.25\node_modules\@modelcontextprotocol\server-everything\dist\index.js"
        
        # 检查文件是否存在
        if not os.path.exists(server_path):
             logger.error(f"❌ Server file not found at: {server_path}")
             return

        mcp_image_server = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="node", 
                    args=[server_path], # 直接运行 JS 入口文件
                ),
                timeout=60,
            )
        )
        logger.info(f"✅ MCP Toolset initialized (Target: {server_path})")

    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP Toolset: {e}")
        return

    # --- 4. Create Agent ---
    logger.info("🤖 Initializing Agent...")
    image_agent = LlmAgent(
        model=Gemini(model=DEFAULT_MODEL_NAME),
        name="image_agent",
        # 增强指令：明确告诉 Agent 工具的名字和用途，强制它使用
        instruction="""You are a creative assistant. 
        You have access to a tool named 'getTinyImage' which can generate tiny pixel art images.
        When the user asks for an image, you MUST use the 'getTinyImage' tool.
        Do not say you cannot generate images. Just call the tool.""",
        tools=[mcp_image_server],
    )

    # --- 5. Run Agent ---
    runner = InMemoryRunner(agent=image_agent)
    
    user_query = "Generate a tiny pixel art image of a smiling face"
    logger.info(f"👤 User Query: {user_query}")

    try:
        # run_debug 方便我们在控制台看到交互过程
        response = await runner.run_debug(user_query, verbose=True)
        
        # --- 6. Process Output (Optional) ---
        # 解析并保存图片
        logger.info("🖼️ Processing response for images...")
        
        # 遍历所有事件，寻找 FunctionResponse 中的图片数据
        # 注意：run_debug 返回的是一个生成器或列表，取决于实现。
        # 在 ADK 中，run_debug 通常打印日志并返回最后的响应或事件列表。
        # 这里我们需要更细致地检查 response 对象。
        
        # 假设 response 是一个包含所有 turn 的列表
        for event in response:
            # 检查是否包含 function_response
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_response and part.function_response.response:
                        content_list = part.function_response.response.get("content", [])
                        for item in content_list:
                            if item.get("type") == "image":
                                image_data = item.get("data")
                                if image_data:
                                    # 保存图片到本地
                                    file_name = "tiny_image.png"
                                    with open(file_name, "wb") as f:
                                        f.write(base64.b64decode(image_data))
                                    logger.info(f"✅ Image saved to: {os.path.abspath(file_name)}")
                                    
    except Exception as e:
        logger.error(f"❌ Runtime Error: {e}")
    finally:
        # 良好的习惯：虽然 InMemoryRunner 会自动清理，但在复杂应用中要注意资源释放
        pass

if __name__ == "__main__":
    asyncio.run(main())
