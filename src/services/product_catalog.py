import sys
import os
import uvicorn
from typing import Dict

# 添加项目根目录到 sys.path，确保能导入 config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from config import settings
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# 初始化日志
logger = settings.setup_logging("ProductCatalogService")

# --- 核心业务逻辑 ---
def get_product_info(product_name: str) -> str:
    """
    Retrieves product details (price, stock, specs) from the catalog.
    
    Args:
        product_name: The name of the product to query.
        
    Returns:
        A formatted string with product details or availability status.
    """
    logger.info(f"🔍 Querying catalog for: {product_name}")
    
    # 模拟数据库
    catalog = {
        "iphone 15 pro": {
            "price": "$999",
            "stock": "In Stock",
            "specs": "A17 Pro chip, Titanium design"
        },
        "pixel 8 pro": {
            "price": "$999",
            "stock": "Low Stock",
            "specs": "Google Tensor G3, AI camera"
        },
        "samsung galaxy s24": {
            "price": "$799",
            "stock": "In Stock",
            "specs": "Snapdragon 8 Gen 3"
        }
    }
    
    key = product_name.lower().strip()
    try:
        # 模糊匹配逻辑
        for db_key, data in catalog.items():
            if key in db_key or db_key in key:
                return (f"✅ Found: {db_key.title()}\n"
                        f"Price: {data['price']}\n"
                        f"Stock: {data['stock']}\n"
                        f"Specs: {data['specs']}")
        
        # 生成可用列表建议
        available = ", ".join([k.title() for k in catalog.keys()])
        return f"❌ Product '{product_name}' not found. Available items: {available}"
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        return "⚠️ System Error: Unable to access product catalog."

# --- 服务启动逻辑 ---
def main():
    try:
        settings.get_api_key() # 验证 API Key
    except ValueError as e:
        logger.error(e)
        return

    logger.info("🚀 Initializing Product Catalog Agent...")

    # 创建 Agent
    agent = LlmAgent(
        model=Gemini(model=settings.DEFAULT_MODEL_NAME),
        name="product_catalog_agent",
        description="External vendor's product catalog service. Provides price, stock, and specs.",
        instruction="""
        You are the Product Catalog Agent (Vendor Side).
        Your ONLY role is to fetch product data using the 'get_product_info' tool.
        - If the tool returns data, present it clearly.
        - If the tool says 'not found', inform the user politely.
        - Do not invent product details.
        """,
        tools=[get_product_info]
    )

    # 转换为 A2A 服务
    app = to_a2a(agent, port=settings.SERVICE_PORT)
    return app

# 全局 app 对象，供 Gunicorn/Uvicorn 导入使用
# 注意：这里我们不再直接调用 uvicorn.run，而是暴露 app 对象
app = None
if __name__ == "__main__":
    # 本地调试模式
    app = main()
    logger.info(f"📡 Starting A2A Server on port {settings.SERVICE_PORT}...")
    uvicorn.run(app, host=settings.SERVICE_HOST, port=settings.SERVICE_PORT)
else:
    # 生产模式 (被 Gunicorn 导入时)
    # 我们需要在这里初始化 app，但不要调用 uvicorn.run
    try:
        settings.get_api_key()
        # 初始化 Agent
        agent = LlmAgent(
            model=Gemini(model=settings.DEFAULT_MODEL_NAME),
            name="product_catalog_agent",
            description="External vendor's product catalog service.",
            instruction="You are the Product Catalog Agent.",
            tools=[get_product_info]
        )
        # 创建 app 对象
        # 注意：Cloud Run 会通过环境变量 PORT 覆盖这里的端口设置，但 to_a2a 需要一个默认值
        app = to_a2a(agent, port=int(os.environ.get("PORT", settings.SERVICE_PORT)))
    except Exception as e:
        logger.error(f"Failed to initialize app: {e}")

