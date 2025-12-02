import unittest
import sys
import os

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from config import settings
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

class TestA2AIntegration(unittest.IsolatedAsyncioTestCase):
    """
    集成测试套件：验证 Customer Support Agent 与 Product Catalog Service 的 A2A 交互。
    """

    async def asyncSetUp(self):
        # 1. 检查环境变量
        try:
            settings.get_api_key()
        except ValueError:
            self.skipTest("GOOGLE_API_KEY not found.")

        # 2. 配置 Agent
        self.remote_agent = RemoteA2aAgent(
            name="product_catalog_agent",
            agent_card=settings.AGENT_CARD_FULL_URL
        )

        self.local_agent = LlmAgent(
            model=Gemini(model=settings.DEFAULT_MODEL_NAME),
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
        self.assertIn("$999", response)
        self.assertIn("Titanium", response)

    async def test_02_not_found(self):
        """测试用例 2: 查询不存在的产品 (Error Handling)"""
        print("\n🧪 Running Test: Query Non-existent Product...")
        response = await self._get_agent_response("Do you have the Nokia 3310?")
        print(f"   Agent Answer: {response}")
        self.assertTrue(
            "not found" in response.lower() or "sorry" in response.lower()
        )

    async def test_03_complex_comparison(self):
        """测试用例 3: 复杂查询 (Multi-step / Comparison)"""
        print("\n🧪 Running Test: Compare two products...")
        response = await self._get_agent_response("Compare the price of Samsung Galaxy S24 and iPhone 15 Pro")
        print(f"   Agent Answer: {response}")
        self.assertIn("799", response)
        self.assertIn("999", response)

if __name__ == "__main__":
    print("🚀 Starting Integration Test Suite...")
    print(f"⚠️  Ensure Service is running at {settings.SERVICE_URL}!")
    unittest.main(verbosity=2)
