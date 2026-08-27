import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentConfigTest(unittest.TestCase):
    def test_agent_source_is_valid_python(self):
        ast.parse((ROOT / "agent.py").read_text())

    def test_required_runtime_files_exist(self):
        for relative in (
            "agent.py",
            "requirements.txt",
            ".agentkit/Dockerfile",
            ".agentkit/agentkit.yaml",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_mcp_and_confirmation_are_configured(self):
        source = (ROOT / "agent.py").read_text()
        self.assertIn("McpToolset", source)
        self.assertIn("MCP_TOOLSET_URL", source)
        self.assertIn("update_camera_maintenance_status", source)
        self.assertIn("require_confirmation", source)


if __name__ == "__main__":
    unittest.main()
