import os
import logging
import sys
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

# 远程服务地址配置
# 1. 优先读取环境变量 REMOTE_CATALOG_URL
# 2. 其次使用部署好的 Cloud Run 地址
# 3. 最后回退到本地调试地址
CLOUD_RUN_URL = "https://mygoogleagent-781259129090.us-central1.run.app"
LOCAL_URL = f"http://localhost:{SERVICE_PORT}"

SERVICE_URL = os.environ.get("REMOTE_CATALOG_URL", CLOUD_RUN_URL)

AGENT_CARD_PATH = "/.well-known/agent-card.json"
AGENT_CARD_FULL_URL = f"{SERVICE_URL}{AGENT_CARD_PATH}"

# 模型配置
# 建议统一管理模型名称，方便切换
DEFAULT_MODEL_NAME = "gemini-2.0-flash-lite-preview-02-05"

# 日志配置
# 允许通过环境变量覆盖，方便调试 (例如: set LOG_LEVEL=DEBUG)
LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
LOG_FILE = "logger.log"

def cleanup_logs(log_files: list[str] = None) -> None:
    """
    清理旧的日志文件 (对应教程 1.3 节)。
    在每次启动 Agent 前调用，确保日志干净。
    """
    if log_files is None:
        log_files = ["logger.log", "web.log", "tunnel.log"]
        
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
                print(f"🧹 Cleaned up {log_file}")
            except OSError as e:
                print(f"⚠️ Failed to clean up {log_file}: {e}")

def setup_logging(logger_name: str = "root", log_to_file: bool = True) -> logging.Logger:
    """
    统一的日志配置函数 (Production Ready)。
    
    Features:
    1. 配置 Root Logger，捕获所有库的日志 (包括 google.adk)。
    2. 同时输出到 Console (方便开发) 和 File (方便追溯)。
    3. 避免重复添加 Handler。
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # 如果已经配置过，直接返回 logger，避免重复添加 handler 导致日志重复
    if root_logger.hasHandlers():
        return logging.getLogger(logger_name)

    formatter = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. File Handler
    if log_to_file:
        try:
            file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"⚠️ Failed to setup file logging: {e}")

    return logging.getLogger(logger_name)

def get_api_key() -> str:
    """获取并验证 API Key"""
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("❌ GOOGLE_API_KEY is missing. Please check your .env file.")
    return key
