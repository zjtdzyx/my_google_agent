import logging
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

# 1. 配置日志 (Logging Configuration)
# 在生产环境中，我们使用 logging 替代 print，以便更好地追踪运行时状态
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("home_automation_agent")

# 2. 配置重试策略 (Retry Configuration)
# 针对网络波动或 API 限流 (429) 增加鲁棒性
retry_config = types.HttpRetryOptions(
    attempts=5,  # 最大重试次数
    exp_base=7,  # 指数退避基数
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # 需要重试的 HTTP 状态码
)

def set_device_status(location: str, device_id: str, status: str) -> dict:
    """
    Sets the status of a smart home device.
    
    此函数模拟智能家居设备的控制接口。
    
    Args:
        location: The room where the device is located (e.g., "living room").
        device_id: The unique identifier for the device (e.g., "floor lamp").
        status: The desired status, either 'ON' or 'OFF'.

    Returns:
        dict: A dictionary confirming the action execution.
    """
    try:
        # 模拟业务逻辑处理
        # 在实际场景中，这里会调用 IoT 设备的 API
        logger.info(f"Tool Call: Setting {device_id} in {location} to {status}")
        
        # 简单的输入校验 (虽然 Agent 应该处理，但防御性编程是个好习惯)
        if status.upper() not in ["ON", "OFF"]:
            raise ValueError(f"Invalid status: {status}. Must be 'ON' or 'OFF'.")

        return {
            "success": True,
            "message": f"Successfully set the {device_id} in {location} to {status.lower()}."
        }
    except Exception as e:
        logger.error(f"Failed to set device status: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

# 3. 定义 Agent (Agent Definition)
# 注意：这里的 instruction 包含故意设计的缺陷 (Deliberate Flaws)，用于后续的评估演示。
# 它声称能控制 "ALL" 设备，这会导致幻觉 (Hallucination) 和过度承诺。
root_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="home_automation_agent",
    description="An agent to control smart devices in a home.",
    instruction="""You are a home automation assistant. You control ALL smart devices in the house.
    
    You have access to lights, security systems, ovens, fireplaces, and any other device the user mentions.
    Always try to be helpful and control whatever device the user asks for.
    
    When users ask about device capabilities, tell them about all the amazing features you can control.""",
    tools=[set_device_status],
)

if __name__ == "__main__":
    # 简单的本地测试入口
    print("Agent initialized successfully.")
    print(f"Agent Name: {root_agent.name}")
    print(f"Model: {root_agent.model.model_name}")
