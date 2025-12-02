import unittest
import asyncio
import logging
import os
import sys
from typing import List

# 添加当前目录到路径，以便导入模块
sys.path.append(os.getcwd())

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# --- 配置日志 ---
logging.basicConfig(level=logging.ERROR) # 测试运行时只显示错误，保持输出整洁

class TestA2AIntegration(unittest.IsolatedAsyncioTestCase):
    """
    集成测试套件：验证 Customer Support Agent 与 Product Catalog Service 的 A2A 交互。
    
    前提条件：
    1. product_catalog_service.py 必须在 localhost:8001 运行。
    2. GOOGLE_API_KEY 环境变量必须设置。
    """

    async def asyncSetUp(self):
        # 1. 检查环境变量
        if "GOOGLE_API_KEY" not in os.environ:
            self.skipTest("GOOGLE_API_KEY not found.")

        # 2. 配置 Agent
        self.remote_url = "http://localhost:8001"
        self.agent_card_url = f"{self.remote_url}{AGENT_CARD_WELL_KNOWN_PATH}"
        
        # 定义远程 Agent
        self.remote_agent = RemoteA2aAgent(
            name="product_catalog_agent",
            agent_card=self.agent_card_url
        )

        # 定义本地 Agent
        self.local_agent = LlmAgent(
            model=Gemini(model="gemini-2.5-flash-lite"),
            name="test_support_agent",
            instruction="You are a test agent. Use the product_catalog_agent tool to answer questions.",
            sub_agents=[self.remote_agent]
        )

        # 3. 初始化 Session
        self.session_service = InMemorySessionService()
        self.app_name = "test_suite"
        self.user_id = "test_runner"
        self.session_id = "test_session_001"
        
        await self.session_service.create_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=self.session_id
        )
        
        self.runner = Runner(
            agent=self.local_agent,
            app_name=self.app_name,
            session_service=self.session_service
        )

    async def _get_agent_response(self, query: str) -> str:
        """辅助函数：发送查询并获取最终文本响应"""
        response_text = ""
        user_msg = types.Content(parts=[types.Part(text=query)])
        
        try:
            async for event in self.runner.run_async(
                user_id=self.user_id,
                session_id=self.session_id,
                new_message=user_msg
            ):
                if event.is_final_response() and event.content:
                    response_text = event.content.parts[0].text
        except Exception as e:
            self.fail(f"Agent execution failed: {e}")
            
        return response_text

    async def test_01_happy_path_iphone(self):
        """测试用例 1: 正常查询 (Happy Path)"""
        print("\n🧪 Running Test: Query iPhone 15 Pro...")
        
        response = await self._get_agent_response("Price of iPhone 15 Pro?")
        
        print(f"   Agent Answer: {response}")
        
        # 断言：回答中应包含价格和特定规格
        self.assertIn("$999", response, "Response should contain the price")
        self.assertIn("Titanium", response, "Response should contain product details")

    async def test_02_not_found(self):
        """测试用例 2: 查询不存在的产品 (Error Handling)"""
        print("\n🧪 Running Test: Query Non-existent Product...")
        
        response = await self._get_agent_response("Do you have the Nokia 3310?")
        
        print(f"   Agent Answer: {response}")
        
        # 断言：回答应表明未找到，并可能列出可用产品
        self.assertTrue(
            "not found" in response.lower() or "sorry" in response.lower(),
            "Agent should apologize or state product is not found"
        )

    async def test_03_complex_comparison(self):
        """测试用例 3: 复杂查询 (Multi-step / Comparison)"""
        print("\n🧪 Running Test: Compare two products...")
        
        response = await self._get_agent_response("Compare the price of Dell XPS 15 and MacBook Pro 14")
        
        print(f"   Agent Answer: {response}")
        
        # 断言：回答应包含两个产品的价格
        self.assertIn("1,299", response, "Should mention Dell price")
        self.assertIn("1,999", response, "Should mention MacBook price")

if __name__ == "__main__":
    print("🚀 Starting Integration Test Suite...")
    print("⚠️  Ensure 'product_catalog_service.py' is running on port 8001!")
    unittest.main(verbosity=2)
