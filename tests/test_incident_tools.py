
import unittest
from unittest.mock import MagicMock, patch

import requests
from servicenow_mcp.tools.incident_tools import get_incident_by_number, GetIncidentByNumberParams
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
        journal_response = MagicMock()
        journal_response.json.return_value = {
            "result": [
                {"element": "work_notes", "value": "Internal note", "sys_created_on": "2025-06-25 10:06:00", "sys_created_by": "jdoe"},
                {"element": "comments", "value": "Looking into it", "sys_created_on": "2025-06-25 10:05:00", "sys_created_by": "jdoe"},
            ]
        }
        mock_get.side_effect = [mock_response, journal_response]

        # Call the function with test data
        params = GetIncidentByNumberParams(incident_number="INC0010001")
        result = get_incident_by_number(config, auth_manager, params)

        # Assert the results
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Incident INC0010001 found")
        self.assertIn("incident", result)
        self.assertEqual(result["incident"]["number"], "INC0010001")
        self.assertEqual(result["incident"]["comments"], [{"created_on": "2025-06-25 10:05:00", "created_by": "jdoe", "text": "Looking into it"}])
        self.assertEqual(result["incident"]["work_notes"], [{"created_on": "2025-06-25 10:06:00", "created_by": "jdoe", "text": "Internal note"}])
        self.assertIn("element_id=12345", mock_get.call_args.kwargs["params"]["sysparm_query"])

    @patch('requests.get')
    def test_get_incident_by_number_journal_fallback(self, mock_get):
        config = ServerConfig(instance_url="https://dev12345.service-now.com", auth=self.auth_config)
        auth_manager = MagicMock(spec=AuthManager)
        auth_manager.get_headers.return_value = {"Authorization": "Bearer FAKE_TOKEN"}

        incident_response = MagicMock()
        incident_response.json.return_value = {
            "result": [{"sys_id": "12345", "number": "INC0010001", "comments": "combined history", "work_notes": ""}]
        }
        journal_response = MagicMock()
        journal_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.side_effect = [incident_response, journal_response]

        result = get_incident_by_number(config, auth_manager, GetIncidentByNumberParams(incident_number="INC0010001"))

        self.assertTrue(result["success"])
        self.assertEqual(result["incident"]["comments"], [{"text": "combined history"}])
        self.assertEqual(result["incident"]["work_notes"], [])

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

if __name__ == '__main__':
    unittest.main()
