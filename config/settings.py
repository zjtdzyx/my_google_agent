import os
import logging
import certifi
from dotenv import load_dotenv

# --- 1. 全局初始化 (Global Initialization) ---
# 加载 .env 文件
load_dotenv()

# 强制设置 SSL 证书路径 (解决 Windows 下的 SSL 报错)
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# --- 2. 配置常量 (Constants) ---
# 服务端配置
SERVICE_HOST = "0.0.0.0"
SERVICE_PORT = 8001
SERVICE_URL = f"http://localhost:{SERVICE_PORT}"
AGENT_CARD_PATH = "/.well-known/agent-card.json"
AGENT_CARD_FULL_URL = f"{SERVICE_URL}{AGENT_CARD_PATH}"

# 模型配置
# 建议统一管理模型名称，方便切换
DEFAULT_MODEL_NAME = "gemini-2.0-flash-lite-preview-02-05"

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

def setup_logging(logger_name: str) -> logging.Logger:
    """统一的日志配置函数"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger(logger_name)

def get_api_key() -> str:
    """获取并验证 API Key"""
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("❌ GOOGLE_API_KEY is missing. Please check your .env file.")
    return key
