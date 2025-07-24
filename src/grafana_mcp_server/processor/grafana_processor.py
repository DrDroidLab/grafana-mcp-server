import datetime
import json
import logging
import re
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class Processor:
    """Base processor interface"""

    def get_connection(self):
        pass

    def test_connection(self):
        pass


class GrafanaApiProcessor(Processor):
    """
    Grafana API processor for handling Grafana API interactions.
    Uses API key authentication.
    """

    def __init__(self, grafana_host, grafana_api_key, ssl_verify="true"):
        """
        Initialize Grafana API processor.

        Args:
            grafana_host: Grafana instance URL (e.g., https://grafana.example.com)
            grafana_api_key: API key for authentication
            ssl_verify: Whether to verify SSL certificates ("true" or "false")
        """
        self.__host = grafana_host.rstrip("/")  # Remove trailing slash
        self.__api_key = grafana_api_key
        self.__ssl_verify = not (ssl_verify and ssl_verify.lower() == "false")
        self.headers = {
            "Authorization": f"Bearer {self.__api_key}",
            "Content-Type": "application/json",
        }

        logger.info(f"Initialized Grafana processor with host: {self.__host}")

    def get_connection(self):
        """Return connection details for debugging"""
        return {
            "host": self.__host,
            "ssl_verify": self.__ssl_verify,
            "auth_method": "api_key",
            "headers": {k: v for k, v in self.headers.items() if k != "Authorization"},
        }

    def test_connection(self):
        """
        Test connection to Grafana API to verify configuration and connectivity.
        Uses the /api/datasources endpoint to verify API access.

        Returns:
            bool: True if connection successful

        Raises:
            Exception: If connection fails with details about the failure
        """
        try:
            url = f"{self.__host}/api/datasources"
            logger.info(f"Testing Grafana connection to: {url}")

            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)
            if response and response.status_code == 200:
                logger.info("Successfully connected to Grafana API")
                return True
            else:
                status_code = response.status_code if response else None
                raise Exception(f"Failed to connect with Grafana. Status Code: {status_code}. Response Text: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred while fetching grafana data sources with error: {e}")
            raise e

    def _get_time_range(self, start_time=None, end_time=None, duration=None, default_hours=3):
        """
        Returns (start_dt, end_dt) as UTC datetimes.
        - If start_time and end_time are provided, use those.
        - Else if duration is provided, use (now - duration, now).
        - Else, use (now - default_hours, now).
        """
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        if start_time and end_time:
            start_dt = self._parse_time(start_time)
            end_dt = self._parse_time(end_time)
            if not start_dt or not end_dt:
                start_dt = now_dt - datetime.timedelta(hours=default_hours)
                end_dt = now_dt
        elif duration:
            dur_ms = self._parse_duration(duration)
            if dur_ms is None:
                dur_ms = default_hours * 60 * 60 * 1000
            start_dt = now_dt - datetime.timedelta(milliseconds=dur_ms)
            end_dt = now_dt
        else:
            start_dt = now_dt - datetime.timedelta(hours=default_hours)
            end_dt = now_dt
        return start_dt, end_dt

    def _parse_duration(self, duration_str):
        """Parse duration string like '2h', '90m' into milliseconds."""
        if not duration_str or not isinstance(duration_str, str):
            return None
        match = re.match(r"^(\d+)([smhd])$", duration_str.strip().lower())
        if match:
            value, unit = match.groups()
            value = int(value)
            if unit == "s":
                return value * 1000
            elif unit == "m":
                return value * 60 * 1000
            elif unit == "h":
                return value * 60 * 60 * 1000
            elif unit == "d":
                return value * 24 * 60 * 60 * 1000
        try:
            # fallback: try to parse as integer minutes
            value = int(duration_str)
            return value * 60 * 1000
        except Exception as e:
            logger.error(f"_parse_duration: Exception parsing '{duration_str}': {e}")
        return None

    def _parse_time(self, time_str):
        """
        Parse a time string in RFC3339, 'now', or 'now-2h', 'now-30m', etc. Returns a UTC datetime.
        """
        if not time_str or not isinstance(time_str, str):
            logger.error(f"_parse_time: Invalid input (not a string): {time_str}")
            return None
        time_str_orig = time_str
        time_str = time_str.strip().lower()
        if time_str.startswith("now"):
            if "-" in time_str:
                match = re.match(r"now-(\d+)([smhd])", time_str)
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    if unit == "s":
                        delta = datetime.timedelta(seconds=value)
                    elif unit == "m":
                        delta = datetime.timedelta(minutes=value)
                    elif unit == "h":
                        delta = datetime.timedelta(hours=value)
                    elif unit == "d":
                        delta = datetime.timedelta(days=value)
                    else:
                        delta = datetime.timedelta()
                    logger.debug(f"_parse_time: Parsed relative time '{time_str_orig}' as now - {value}{unit}")
                    return datetime.datetime.now(datetime.timezone.utc) - delta
            logger.debug(f"_parse_time: Parsed 'now' as current UTC time for input '{time_str_orig}'")
            return datetime.datetime.now(datetime.timezone.utc)
        else:
            try:
                # Try parsing as RFC3339 or other datetime formats
                dt = datetime.datetime.fromisoformat(time_str_orig.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                logger.debug(f"_parse_time: Successfully parsed '{time_str_orig}' as {dt.isoformat()}")
                return dt.astimezone(datetime.timezone.utc)
            except Exception as e:
                logger.error(f"_parse_time: Exception parsing '{time_str_orig}': {e}")
                return None

    def grafana_promql_query(
        self,
        datasource_uid: str,
        query: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Executes PromQL queries against Grafana's Prometheus datasource.

        Args:
            datasource_uid: Prometheus datasource UID
            query: PromQL query string
            start_time: Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')
            end_time: End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')
            duration: Duration string for the time window (e.g., '2h', '90m')

        Returns:
            Dict containing query results with optimized time series data
        """
        try:
            # Use standardized time range logic
            start_dt, end_dt = self._get_time_range(start_time, end_time, duration, default_hours=3)

            # Convert to milliseconds since epoch (Grafana format)
            start_ms = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)

            payload = {
                "queries": [
                    {
                        "refId": "A",
                        "expr": query,
                        "editorMode": "code",
                        "legendFormat": "__auto",
                        "range": True,
                        "exemplar": False,
                        "requestId": "A",
                        "utcOffsetSec": 0,
                        "scopes": [],
                        "adhocFilters": [],
                        "interval": "",
                        "datasource": {"type": "prometheus", "uid": datasource_uid},
                        "intervalMs": 30000,
                        "maxDataPoints": 1000,
                    }
                ],
                "from": str(start_ms),
                "to": str(end_ms),
            }

            url = f"{self.__host}/api/ds/query"
            logger.info(f"Executing PromQL query: {query} from {start_dt.isoformat()} to {end_dt.isoformat()}")

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=self.__ssl_verify,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                # Optimize time series data to reduce token size
                optimized_data = self._optimize_time_series_data(data)
                return {
                    "status": "success",
                    "query": query,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "duration": duration,
                    "results": optimized_data,
                }
            else:
                raise Exception(f"PromQL query failed. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error executing PromQL query: {e!s}")
            raise e

    def grafana_loki_query(
        self,
        datasource_uid: str,
        query: str,
        duration: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Queries Grafana Loki for log data.

        Args:
            query: Loki query string
            duration: Time duration (e.g., '5m', '1h', '2d') - overrides start_time/end_time if provided
            start_time: Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')
            end_time: End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')
            limit: Maximum number of log entries to return

        Returns:
            Dict containing log data from Loki datasource
        """
        try:
            # Use standardized time range logic
            start_dt, end_dt = self._get_time_range(start_time, end_time, duration, default_hours=1)

            # Convert to milliseconds since epoch (Grafana format)
            start_ms = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)

            payload = {
                "queries": [
                    {
                        "refId": "A",
                        "expr": query,
                        "datasource": {"type": "loki", "uid": datasource_uid},
                        "maxLines": limit,
                    }
                ],
                "from": str(start_ms),
                "to": str(end_ms),
            }

            url = f"{self.__host}/api/ds/query"
            logger.info(f"Executing Loki query: {query} from {start_dt.isoformat()} to {end_dt.isoformat()}")

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=self.__ssl_verify,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "query": query,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "duration": duration,
                    "limit": limit,
                    "results": data,
                }
            else:
                raise Exception(f"Loki query failed. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error executing Loki query: {e!s}")
            raise e

    def grafana_get_dashboard_config_details(self, dashboard_uid: str) -> dict[str, Any]:
        """
        Retrieves dashboard configuration details from the database.

        Args:
            dashboard_uid: Dashboard UID

        Returns:
            Dict containing dashboard configuration metadata
        """
        try:
            # This would typically query a database, but for now we'll use Grafana API
            url = f"{self.__host}/api/dashboards/uid/{dashboard_uid}"
            logger.info(f"Fetching dashboard config for UID: {dashboard_uid}")

            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)

            if response.status_code == 200:
                dashboard_data = response.json()
                return {
                    "status": "success",
                    "dashboard_uid": dashboard_uid,
                    "dashboard": dashboard_data.get("dashboard", {}),
                    "meta": dashboard_data.get("meta", {}),
                }
            else:
                raise Exception(f"Failed to fetch dashboard config. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error fetching dashboard config: {e!s}")
            raise e

    def grafana_query_dashboard_panels(
        self,
        dashboard_uid: str,
        panel_ids: list[int],
        template_variables: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Executes queries for specific dashboard panels.

        Args:
            dashboard_uid: Dashboard UID
            panel_ids: List of panel IDs to query (max 4)
            template_variables: Template variables for the dashboard

        Returns:
            Dict containing panel data with optimized metrics
        """
        try:
            if len(panel_ids) > 4:
                raise ValueError("Maximum 4 panels can be queried at once")

            logger.info(f"Querying dashboard panels: {dashboard_uid}, panel_ids: {panel_ids}")

            # First get dashboard configuration
            dashboard_url = f"{self.__host}/api/dashboards/uid/{dashboard_uid}"
            dashboard_response = requests.get(
                dashboard_url,
                headers=self.headers,
                verify=self.__ssl_verify,
                timeout=20,
            )

            if dashboard_response.status_code != 200:
                raise Exception(f"Failed to fetch dashboard. Status: {dashboard_response.status_code}")

            dashboard_data = dashboard_response.json()
            dashboard = dashboard_data.get("dashboard", {})

            # Handle both old and new dashboard structures
            panels = dashboard.get("panels", [])
            if not panels:
                # Try to get panels from rows (newer dashboard structure)
                rows = dashboard.get("rows", [])
                for row in rows:
                    row_panels = row.get("panels", [])
                    panels.extend(row_panels)

            logger.info(f"Found {len(panels)} panels in dashboard")

            # Filter panels by requested IDs
            target_panels = [panel for panel in panels if panel.get("id") in panel_ids]

            if not target_panels:
                logger.warning(f"No panels found with IDs: {panel_ids}")
                logger.info(f"Available panel IDs: {[panel.get('id') for panel in panels]}")
                raise Exception(f"No panels found with IDs: {panel_ids}")

            logger.info(f"Found {len(target_panels)} target panels")

            # Execute queries for each panel
            panel_results = []
            for panel in target_panels:
                logger.info(f"Processing panel {panel.get('id')}: {panel.get('title', 'Unknown')}")
                panel_result = self._execute_panel_query(panel, template_variables or {})
                panel_results.append(
                    {
                        "panel_id": panel.get("id"),
                        "title": panel.get("title"),
                        "type": panel.get("type"),
                        "data": panel_result,
                    }
                )

            return {
                "status": "success",
                "dashboard_uid": dashboard_uid,
                "panel_ids": panel_ids,
                "template_variables": template_variables,
                "results": panel_results,
            }

        except Exception as e:
            logger.error(f"Error querying dashboard panels: {e!s}")
            raise e

    def grafana_fetch_dashboard_variable_label_values(self, datasource_uid: str, label_name: str, metric_match_filter: Optional[str] = None) -> dict[str, Any]:
        """
        Fetches label values for dashboard variables from Prometheus datasource.

        Args:
            datasource_uid: Prometheus datasource UID
            label_name: Label name to fetch values for (e.g., "instance", "job")
            metric_match_filter: Optional metric name filter (e.g., "up", "node_cpu_seconds_total")

        Returns:
            Dict containing list of available label values
        """
        try:
            url = f'{self.__host}/api/datasources/proxy/uid/{datasource_uid}/api/v1/label/{label_name}/values'
            params = {}

            if metric_match_filter:
                params['match[]'] = metric_match_filter

            logger.info(f"Fetching label values for: {label_name} from Prometheus API")

            response = requests.get(
                url, 
                headers=self.headers, 
                params=params, 
                verify=self.__ssl_verify,
                timeout=20
            )
            
            if response and response.status_code == 200:
                label_values = response.json().get('data', [])
                
                return {
                    "status": "success",
                    "datasource_uid": datasource_uid,
                    "label_name": label_name,
                    "metric_match_filter": metric_match_filter,
                    "values": label_values,
                }
            else:
                status_code = response.status_code if response else None
                error_msg = f"Failed to fetch label values for {label_name}. Status: {status_code}, Response: {response.text if response else 'No response'}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Exception occurred while fetching promql metric labels for {label_name} with error: {e}")
            raise e

    def grafana_fetch_dashboard_variables(self, dashboard_uid: str) -> dict[str, Any]:
        """
        Fetches all variables and their values from a Grafana dashboard.

        Args:
            dashboard_uid: Dashboard UID

        Returns:
            Dict containing dashboard variables and their values
        """
        try:
            url = f"{self.__host}/api/dashboards/uid/{dashboard_uid}"
            logger.info(f"Fetching dashboard variables for UID: {dashboard_uid}")

            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)

            if response.status_code == 200:
                dashboard_data = response.json()
                dashboard = dashboard_data.get("dashboard", {})
                templating = dashboard.get("templating", {})
                variables = templating.get("list", [])

                # Extract variable information
                variable_details = []
                for var in variables:
                    variable_details.append(
                        {
                            "name": var.get("name"),
                            "type": var.get("type"),
                            "current_value": var.get("current", {}).get("value"),
                            "options": var.get("options", []),
                            "query": var.get("query"),
                            "definition": var.get("definition"),
                        }
                    )

                return {
                    "status": "success",
                    "dashboard_uid": dashboard_uid,
                    "variables": variable_details,
                }
            else:
                raise Exception(f"Failed to fetch dashboard variables. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error fetching dashboard variables: {e!s}")
            raise e

    def grafana_fetch_all_dashboards(self, limit: int = 100) -> dict[str, Any]:
        """
        Fetches all dashboards from Grafana.

        Args:
            limit: Maximum number of dashboards to return

        Returns:
            Dict containing list of dashboards with basic information
        """
        try:
            url = f"{self.__host}/api/search"
            params = {"limit": limit}
            logger.info(f"Fetching all dashboards (limit: {limit})")

            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                verify=self.__ssl_verify,
                timeout=20,
            )

            if response.status_code == 200:
                dashboards = response.json()
                # Extract relevant information
                dashboard_list = []
                for dashboard in dashboards:
                    dashboard_list.append(
                        {
                            "uid": dashboard.get("uid"),
                            "title": dashboard.get("title"),
                            "type": dashboard.get("type"),
                            "url": dashboard.get("url"),
                            "folder_title": dashboard.get("folderTitle"),
                            "folder_uid": dashboard.get("folderUid"),
                            "tags": dashboard.get("tags", []),
                            "is_starred": dashboard.get("isStarred", False),
                        }
                    )

                return {
                    "status": "success",
                    "total_count": len(dashboard_list),
                    "limit": limit,
                    "dashboards": dashboard_list,
                }
            else:
                raise Exception(f"Failed to fetch dashboards. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error fetching dashboards: {e!s}")
            raise e

    def grafana_fetch_datasources(self) -> dict[str, Any]:
        """
        Fetches all datasources from Grafana.

        Returns:
            Dict containing list of datasources
        """
        try:
            url = f"{self.__host}/api/datasources"
            logger.info("Fetching all datasources")

            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)

            if response.status_code == 200:
                datasources = response.json()
                # Extract relevant information
                datasource_list = []
                for ds in datasources:
                    datasource_list.append(
                        {
                            "id": ds.get("id"),
                            "uid": ds.get("uid"),
                            "name": ds.get("name"),
                            "type": ds.get("type"),
                            "url": ds.get("url"),
                            "access": ds.get("access"),
                            "database": ds.get("database"),
                            "is_default": ds.get("isDefault", False),
                            "json_data": ds.get("jsonData", {}),
                            "secure_json_data": dict.fromkeys(ds.get("secureJsonData", {}).keys(), "***"),
                        }
                    )

                return {
                    "status": "success",
                    "total_count": len(datasource_list),
                    "datasources": datasource_list,
                }
            else:
                raise Exception(f"Failed to fetch datasources. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error fetching datasources: {e!s}")
            raise e

    def grafana_fetch_folders(self) -> dict[str, Any]:
        """
        Fetches all folders from Grafana.

        Returns:
            Dict containing list of folders
        """
        try:
            url = f"{self.__host}/api/folders"
            logger.info("Fetching all folders")

            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)

            if response.status_code == 200:
                folders = response.json()
                # Extract relevant information
                folder_list = []
                for folder in folders:
                    folder_list.append(
                        {
                            "id": folder.get("id"),
                            "uid": folder.get("uid"),
                            "title": folder.get("title"),
                            "url": folder.get("url"),
                            "has_acl": folder.get("hasAcl", False),
                            "can_save": folder.get("canSave", False),
                            "can_edit": folder.get("canEdit", False),
                            "can_admin": folder.get("canAdmin", False),
                            "created": folder.get("created"),
                            "updated": folder.get("updated"),
                            "created_by": folder.get("createdBy"),
                            "updated_by": folder.get("updatedBy"),
                            "version": folder.get("version"),
                        }
                    )

                return {
                    "status": "success",
                    "total_count": len(folder_list),
                    "folders": folder_list,
                }
            else:
                raise Exception(f"Failed to fetch folders. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error fetching folders: {e!s}")
            raise e

    def _optimize_time_series_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Optimize time series data to reduce token size"""
        try:
            # Sample data points if there are too many
            for result in data.get("results", {}).values():
                if "frames" in result:
                    for frame in result["frames"]:
                        if "data" in frame and "values" in frame["data"]:
                            values = frame["data"]["values"]
                            if len(values) > 0 and len(values[0]) > 1000:
                                # Sample every 10th point
                                for i in range(len(values)):
                                    values[i] = values[i][::10]
            return data
        except Exception as e:
            logger.warning(f"Error optimizing time series data: {e}")
            return data

    def _execute_panel_query(self, panel: dict[str, Any], template_variables: dict[str, str]) -> dict[str, Any]:
        """Execute query for a specific panel"""
        try:
            logger.info(f"Executing panel query for panel: {panel.get('title', 'Unknown')}")
            logger.debug(f"Panel structure: {json.dumps(panel, indent=2)}")

            targets = panel.get("targets", [])
            if not targets:
                logger.warning(f"No targets found for panel: {panel.get('title', 'Unknown')}")
                return {"error": "No targets found for panel"}

            # For now, execute the first target
            target = targets[0]
            logger.debug(f"Target structure: {json.dumps(target, indent=2)}")

            # Extract query expression
            query = target.get("expr", "")
            if not query:
                logger.warning(f"No query expression found in target for panel: {panel.get('title', 'Unknown')}")
                return {"error": "No query expression found in target"}

            # Extract datasource information
            datasource = target.get("datasource", {})
            logger.debug(f"Datasource info: {datasource}")

            # Handle different datasource formats
            datasource_uid = None
            if isinstance(datasource, str):
                datasource_uid = datasource
            elif isinstance(datasource, dict):
                datasource_uid = datasource.get("uid")
                if not datasource_uid:
                    datasource_uid = datasource.get("id")  # Fallback to id
            else:
                logger.warning(f"Unexpected datasource format: {type(datasource)}")
                return {"error": f"Unexpected datasource format: {type(datasource)}"}

            if not datasource_uid:
                logger.warning(f"No datasource UID found for panel: {panel.get('title', 'Unknown')}")
                # Try to get datasource from panel level
                panel_datasource = panel.get("datasource", {})
                if isinstance(panel_datasource, dict):
                    datasource_uid = panel_datasource.get("uid") or panel_datasource.get("id")
                elif isinstance(panel_datasource, str):
                    datasource_uid = panel_datasource

                if not datasource_uid:
                    return {"error": "No datasource UID found"}

            logger.info(f"Executing query: {query} with datasource: {datasource_uid}")

            # Apply template variables - fix the replacement pattern
            original_query = query
            for var_name, var_value in template_variables.items():
                # Replace both $var and ${var} patterns
                query = query.replace(f"${var_name}", var_value)
                query = query.replace(f"${{{var_name}}}", var_value)

            if original_query != query:
                logger.info(f"Applied template variables. Original: {original_query}, Modified: {query}")

            # Execute the query with a reasonable time range
            result = self.grafana_promql_query(datasource_uid, query, duration="1h")

            return result

        except Exception as e:
            logger.error(f"Error executing panel query: {e}")
            return {"error": str(e)}


