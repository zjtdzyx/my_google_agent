import logging
from typing import Dict, Any, Optional
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool

logger = logging.getLogger("telemetry_plugin")

class TelemetryPlugin(BasePlugin):
    """
    A production-ready telemetry plugin that tracks agent execution metrics.
    
    Metrics tracked:
    - Agent invocation count
    - Tool execution count
    - LLM request count
    - (Optional) Token usage estimation
    """

    def __init__(self) -> None:
        """Initialize the plugin with zeroed counters."""
        super().__init__(name="telemetry_plugin")
        self.metrics: Dict[str, int] = {
            "agent_runs": 0,
            "tool_calls": 0,
            "llm_requests": 0,
            "errors": 0
        }
        logger.info("📊 TelemetryPlugin initialized")

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext, **kwargs: Any
    ) -> None:
        """Called before an agent starts execution."""
        self.metrics["agent_runs"] += 1
        logger.info(f"▶️  [Telemetry] Agent '{agent.name}' starting. (Total runs: {self.metrics['agent_runs']})")

    async def after_tool_callback(
        self, 
        *, 
        tool: BaseTool, 
        **kwargs: Any
    ) -> None:
        """Called after a tool finishes execution."""
        self.metrics["tool_calls"] += 1
        
        # 调试信息：如果想知道框架到底传了什么参数，可以取消下面这行的注释
        # logger.debug(f"🔍 [Telemetry] after_tool_callback received args: {list(kwargs.keys())}")
        
        # Log tool usage with a distinct icon for visibility
        logger.info(f"🛠️  [Telemetry] Tool '{tool.name}' executed. (Total calls: {self.metrics['tool_calls']})")

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest, **kwargs: Any
    ) -> None:
        """Called before sending a request to the LLM."""
        self.metrics["llm_requests"] += 1
        logger.debug(f"🧠 [Telemetry] LLM Request initiated. (Total requests: {self.metrics['llm_requests']})")

    async def on_model_error_callback(
        self, *, callback_context: CallbackContext, error: Exception, **kwargs: Any
    ) -> None:
        """Called when the model encounters an error."""
        self.metrics["errors"] += 1
        logger.error(f"❌ [Telemetry] Model Error detected: {str(error)}")

    def get_summary(self) -> str:
        """Returns a formatted summary of the session metrics."""
        return (
            "\n📊 --- Session Telemetry Summary ---\n"
            f"   🔹 Agent Runs:   {self.metrics['agent_runs']}\n"
            f"   🔹 Tool Calls:   {self.metrics['tool_calls']}\n"
            f"   🔹 LLM Requests: {self.metrics['llm_requests']}\n"
            f"   🔹 Errors:       {self.metrics['errors']}\n"
            "-------------------------------------"
        )
