import logging
import os
import uvicorn
from typing import Dict

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

# --- 1. 配置日志 (Logging Setup) ---
# 生产环境标准：使用结构化日志而非 print
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ProductCatalogService")

# --- 2. 核心业务逻辑 (Business Logic) ---
def get_product_info(product_name: str) -> str:
    """
    Retrieves product details (price, stock, specs) from the catalog.
    
    Args:
        product_name: The name of the product to query.
        
    Returns:
        A formatted string with product details or availability status.
    """
    logger.info(f"Querying catalog for: {product_name}")
    
    # 模拟数据库 (Mock Database)
    # 在实际工程中，这里会连接 SQL/NoSQL 数据库
    catalog: Dict[str, str] = {
        "iphone 15 pro": "iPhone 15 Pro, $999, Low Stock (8 units), 128GB, Titanium finish",
        "samsung galaxy s24": "Samsung Galaxy S24, $799, In Stock (31 units), 256GB, Phantom Black",
        "dell xps 15": "Dell XPS 15, $1,299, In Stock (45 units), 15.6\" display, 16GB RAM",
        "macbook pro 14": "MacBook Pro 14\", $1,999, In Stock (22 units), M3 Pro chip",
        "sony wh-1000xm5": "Sony WH-1000XM5 Headphones, $399, In Stock (67 units), Noise-canceling",
    }
    
    key = product_name.lower().strip()
    
    try:
        if key in catalog:
            result = f"✅ Product Found: {catalog[key]}"
            logger.info(f"Hit: {key}")
            return result
        else:
            # 增强体验：提供可用列表
            available = ", ".join([k.title() for k in catalog.keys()])
            logger.warning(f"Miss: {key}")
            return f"❌ Product '{product_name}' not found. Available items: {available}"
    except Exception as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return "⚠️ System Error: Unable to access product catalog."

# --- 3. Agent 配置 (Agent Configuration) ---
# 检查 API Key
if "GOOGLE_API_KEY" not in os.environ:
    logger.warning("GOOGLE_API_KEY not found in environment variables. Agent may fail to start.")

# 配置重试策略 (Resilience Pattern)
retry_config = types.HttpRetryOptions(
    attempts=3,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503]
)

# 初始化 Agent
catalog_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
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

# --- 4. A2A 服务暴露 (Service Exposure) ---
# 将 Agent 包装为符合 A2A 协议的 Web 服务
# 这会自动生成 /.well-known/agent-card.json
PORT = 8001
app = to_a2a(catalog_agent, port=PORT)

if __name__ == "__main__":
    logger.info(f"🚀 Starting Product Catalog Service on port {PORT}...")
    logger.info(f"📄 Agent Card will be available at: http://localhost:{PORT}/.well-known/agent-card.json")
    
    # 启动服务 (生产环境通常使用 gunicorn + uvicorn worker，但在 Windows/开发环境直接用 uvicorn)
    uvicorn.run(app, host="127.0.0.1", port=PORT)
