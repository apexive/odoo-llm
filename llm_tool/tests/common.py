from odoo.tests import common


class LLMToolCase(common.TransactionCase):
    """Base test case for llm.tool core functionality tests

    These tests focus on core tool functionality without relying on
    actual decorated methods. Integration tests with real @llm_tool
    decorated methods are in llm_tool_demo/tests/.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.LLMTool = cls.env["llm.tool"]

    def _create_test_tool(self, **kwargs):
        """Helper to create a test tool with default values"""
        values = {
            "name": kwargs.get("name", "test_tool"),
            "description": kwargs.get("description", "Test tool description"),
            "implementation": kwargs.get("implementation", "function"),
        }
        values.update(kwargs)
        return self.LLMTool.create(values)
