import sys
import os
from typing import List

# Ensure the root directory is in sys.path to allow importing config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search
from google.genai import types

from config import settings

# 1. 配置日志
logger = settings.setup_logging("research_agent")

# 2. 配置重试策略
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# 3. 定义工具 (Tools)

# 🐛 BUG ALERT: 故意植入的 Bug
# 教程演示：我们将类型提示错误地定义为 `str`，而不是 `List[str]`。
# 这会导致 Agent 将列表的字符串表示形式传递给函数，或者 LLM 感到困惑。
# `len(papers)` 将计算字符串的长度（字符数），而不是列表中的项目数。
def count_papers(papers: List[str]):
    """
    This function counts the number of papers in a list of strings.
    
    Args:
      papers: A list of strings, where each string is a research paper.
    
    Returns:
      The number of papers in the list.
    """
    logger.debug(f"Tool 'count_papers' called. Input type: {type(papers)}")
    logger.debug(f"Input value snippet: {str(papers)[:100]}...")
    
    count = len(papers)
    logger.info(f"Tool 'count_papers' returning count: {count}")
    return count


# 4. 定义子 Agent (Sub-Agent)
# 负责执行具体的搜索任务
google_search_agent = LlmAgent(
    name="google_search_agent",
    model=Gemini(
        model=settings.DEFAULT_MODEL_NAME, 
        api_key=settings.get_api_key(), 
        retry_options=retry_config
    ),
    description="Searches for information using Google search",
    instruction="""Use the google_search tool to find information on the given topic. Return the raw search results.
    If the user asks for a list of papers, then give them the list of research papers you found and not the summary.""",
    tools=[google_search]
)


# 5. 定义 Root Agent
# 负责协调搜索和计数
root_agent = LlmAgent(
    name="research_paper_finder_agent",
    model=Gemini(
        model=settings.DEFAULT_MODEL_NAME, 
        api_key=settings.get_api_key(), 
        retry_options=retry_config
    ),
    instruction="""Your task is to find research papers and count them. 

    You MUST ALWAYS follow these steps:
    1) Find research papers on the user provided topic using the 'google_search_agent'. 
    2) Then, pass the papers to 'count_papers' tool to count the number of papers returned.
    3) Return both the list of research papers and the total number of papers.
    """,
    tools=[AgentTool(agent=google_search_agent), count_papers]
)

if __name__ == "__main__":
    print(f"✅ Agent '{root_agent.name}' initialized with bug included for debugging practice.")
