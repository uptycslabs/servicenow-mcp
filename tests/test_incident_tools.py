
import unittest
from unittest.mock import MagicMock, patch
from servicenow_mcp.tools.incident_tools import (
    get_incident_by_number,
    update_incident,
    GetIncidentByNumberParams,
    UpdateIncidentParams,
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
                    "sys_updated_on": "2025-06-25 10:00:00"
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


class TestUpdateIncidentVerification(unittest.TestCase):
    """Tests for the update-applied check on update_incident.

    ServiceNow returns 200 even when it silently discards invalid field values,
    so update_incident tallies the returned record against the sent payload.
    """

    SYS_ID = "ad57a404830b871010bcb9f6feaad371"

    def setUp(self):
        auth_config = AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username='test', password='test'))
        self.config = ServerConfig(instance_url="https://dev12345.service-now.com", auth=auth_config)
        self.auth_manager = MagicMock(spec=AuthManager)
        self.auth_manager.get_headers.return_value = {"Authorization": "Bearer FAKE_TOKEN"}

    @staticmethod
    def _mock_put(fields):
        """Build a mocked PUT response in sysparm_display_value=all shape."""
        result = {
            "sys_id": {"display_value": TestUpdateIncidentVerification.SYS_ID,
                       "value": TestUpdateIncidentVerification.SYS_ID},
            "number": {"display_value": "INC0010081", "value": "INC0010081"},
        }
        result.update(fields)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": result}
        return mock_response

    @patch('requests.put')
    def test_update_all_fields_applied(self, mock_put):
        mock_put.return_value = self._mock_put({
            "category": {"display_value": "Software", "value": "software"},
            "priority": {"display_value": "2 - High", "value": "2"},
        })

        params = UpdateIncidentParams(incident_id=self.SYS_ID, category="software", priority="2")
        result = update_incident(self.config, self.auth_manager, params)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Incident updated successfully")
        self.assertEqual(result.incident_id, self.SYS_ID)
        self.assertEqual(result.incident_number, "INC0010081")

    @patch('requests.put')
    def test_update_partial_failure(self, mock_put):
        # category "Internal" is invalid and silently kept at "software"
        mock_put.return_value = self._mock_put({
            "category": {"display_value": "Software", "value": "software"},
            "priority": {"display_value": "2 - High", "value": "2"},
        })

        params = UpdateIncidentParams(incident_id=self.SYS_ID, category="Internal", priority="2")
        result = update_incident(self.config, self.auth_manager, params)

        self.assertFalse(result.success)
        self.assertIn("partially updated", result.message)
        self.assertIn("category", result.message)
        self.assertNotIn("priority", result.message)
        self.assertEqual(result.incident_number, "INC0010081")

    @patch('requests.put')
    def test_update_no_fields_applied(self, mock_put):
        mock_put.return_value = self._mock_put({
            "category": {"display_value": "Software", "value": "software"},
        })

        params = UpdateIncidentParams(incident_id=self.SYS_ID, category="Internal")
        result = update_incident(self.config, self.auth_manager, params)

        self.assertFalse(result.success)
        self.assertIn("update failed", result.message)
        self.assertIn("category", result.message)

    @patch('requests.put')
    def test_update_journal_fields_not_flagged(self, mock_put):
        # work_notes is write-only: the record always echoes "" for it
        mock_put.return_value = self._mock_put({
            "work_notes": {"display_value": "", "value": ""},
        })

        params = UpdateIncidentParams(incident_id=self.SYS_ID, work_notes="Investigating")
        result = update_incident(self.config, self.auth_manager, params)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Incident updated successfully")

    @patch('requests.put')
    def test_update_matches_display_or_raw_value(self, mock_put):
        assignee_sys_id = "3b59ecc98352431010bcb9f6feaad3a1"
        mock_put.return_value = self._mock_put({
            "state": {"display_value": "Resolved", "value": "6"},
            "assigned_to": {"display_value": "John Doe", "value": assignee_sys_id},
        })

        # state sent as display value, assigned_to sent as raw sys_id
        params = UpdateIncidentParams(incident_id=self.SYS_ID, state="Resolved", assigned_to=assignee_sys_id)
        result = update_incident(self.config, self.auth_manager, params)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Incident updated successfully")


if __name__ == '__main__':
    unittest.main()
