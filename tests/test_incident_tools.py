
import unittest
from unittest.mock import MagicMock, patch

import requests
from servicenow_mcp.tools.incident_tools import (
    get_incident_by_number, GetIncidentByNumberParams, get_incident_comments, GetIncidentCommentsParams,
)
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig
from servicenow_mcp.auth.auth_manager import AuthManager

class TestIncidentTools(unittest.TestCase):

    def setUp(self):
        self.auth_config = AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username='test', password='test'))

    @patch('requests.get')
    def test_get_incident_by_number_success(self, mock_get):
        # Mock the server configuration
        config = ServerConfig(instance_url="https://dev12345.service-now.com", auth=self.auth_config)

        # Mock the authentication manager
        auth_manager = MagicMock(spec=AuthManager)
        auth_manager.get_headers.return_value = {"Authorization": "Bearer FAKE_TOKEN"}

        # Mock the requests.get call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "12345",
                    "number": "INC0010001",
                    "short_description": "Test incident",
                    "description": "This is a test incident",
                    "state": "New",
                    "priority": "1 - Critical",
                    "assigned_to": "John Doe",
                    "category": "Software",
                    "subcategory": "Email",
                    "sys_created_on": "2025-06-25 10:00:00",
                    "sys_updated_on": "2025-06-25 10:00:00",
                    "comments": "2025-06-25 10:05:00 - John Doe (Additional comments)\nLooking into it",
                    "work_notes": "2025-06-25 10:06:00 - John Doe (Work notes)\nInternal note"
                }
            ]
        }
        mock_get.return_value = mock_response

        # Call the function with test data
        params = GetIncidentByNumberParams(incident_number="INC0010001")
        result = get_incident_by_number(config, auth_manager, params)

        # Assert the results
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Incident INC0010001 found")
        self.assertIn("incident", result)
        self.assertEqual(result["incident"]["number"], "INC0010001")
        self.assertNotIn("comments", result["incident"])
        self.assertEqual(mock_get.call_count, 1)

    @patch('requests.get')
    def test_get_incident_by_number_not_found(self, mock_get):
        # Mock the server configuration
        config = ServerConfig(instance_url="https://dev12345.service-now.com", auth=self.auth_config)

        # Mock the authentication manager
        auth_manager = MagicMock(spec=AuthManager)
        auth_manager.get_headers.return_value = {"Authorization": "Bearer FAKE_TOKEN"}

        # Mock the requests.get call for a not found scenario
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        # Call the function with a non-existent incident number
        params = GetIncidentByNumberParams(incident_number="INC9999999")
        result = get_incident_by_number(config, auth_manager, params)

        # Assert the results
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Incident not found: INC9999999")

    @patch('requests.get')
    def test_get_incident_comments_pages(self, mock_get):
        config = ServerConfig(instance_url="https://dev12345.service-now.com", auth=self.auth_config)
        auth_manager = MagicMock(spec=AuthManager)
        auth_manager.get_headers.return_value = {}

        lookup = MagicMock()
        lookup.json.return_value = {"result": [{"sys_id": "abc"}]}
        journal = MagicMock()
        journal.json.return_value = {"result": [
            {"element": "work_notes", "value": f"n{i}", "sys_created_on": "t", "sys_created_by": "u"} for i in range(3)
        ]}
        mock_get.side_effect = [lookup, journal]

        params = GetIncidentCommentsParams(incident_number="INC0010001", type="work_notes", limit=2, offset=4)
        result = get_incident_comments(config, auth_manager, params)

        self.assertEqual([e["text"] for e in result["entries"]], ["n0", "n1"])
        self.assertTrue(result["has_more"])
        self.assertEqual(result["next_offset"], 6)
        sent = mock_get.call_args.kwargs["params"]
        self.assertEqual(sent["sysparm_limit"], 3)
        self.assertEqual(sent["sysparm_offset"], 4)
        self.assertIn("element_id=abc^elementINwork_notes^", sent["sysparm_query"])

    @patch('requests.get')
    def test_get_incident_comments_last_page(self, mock_get):
        config = ServerConfig(instance_url="https://dev12345.service-now.com", auth=self.auth_config)
        auth_manager = MagicMock(spec=AuthManager)
        auth_manager.get_headers.return_value = {}

        lookup = MagicMock()
        lookup.json.return_value = {"result": [{"sys_id": "abc"}]}
        journal = MagicMock()
        journal.json.return_value = {"result": [{"element": "comments", "value": "hi"}]}
        mock_get.side_effect = [lookup, journal]

        result = get_incident_comments(config, auth_manager, GetIncidentCommentsParams(incident_number="INC0010001"))

        self.assertFalse(result["has_more"])
        self.assertIsNone(result["next_offset"])
        self.assertEqual(result["entries"][0]["type"], "comments")

    @patch('requests.get')
    def test_get_incident_comments_not_found(self, mock_get):
        config = ServerConfig(instance_url="https://dev12345.service-now.com", auth=self.auth_config)
        auth_manager = MagicMock(spec=AuthManager)
        auth_manager.get_headers.return_value = {}

        lookup = MagicMock()
        lookup.json.return_value = {"result": []}
        mock_get.return_value = lookup

        result = get_incident_comments(config, auth_manager, GetIncidentCommentsParams(incident_number="INC9999999"))

        self.assertFalse(result["success"])
        self.assertEqual(mock_get.call_count, 1)

if __name__ == '__main__':
    unittest.main()
