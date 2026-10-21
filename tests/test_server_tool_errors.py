import asyncio
import unittest
from unittest.mock import MagicMock, patch

import requests

from servicenow_mcp.server import ServiceNowMCP


class TestToolErrors(unittest.TestCase):
    def test_success_false_raises(self):
        server = ServiceNowMCP({
            "instance_url": "https://example.service-now.com",
            "auth": {"type": "basic", "basic": {"username": "u", "password": "p"}},
        })
        server.enabled_tool_names = ["add_comment"]
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("403 Client Error: Forbidden")
        with patch("servicenow_mcp.tools.incident_tools.requests.put", return_value=resp):
            with self.assertRaisesRegex(RuntimeError, "403"):
                asyncio.run(server._call_tool_impl("add_comment", {"incident_id": "a" * 32, "comment": "x"}))


if __name__ == "__main__":
    unittest.main()
