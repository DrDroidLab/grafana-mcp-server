import logging
import requests
import json
import datetime
from typing import Optional, Dict, List, Any

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
    
    def __init__(self, grafana_host, grafana_api_key, ssl_verify='true'):
        """
        Initialize Grafana API processor.
        
        Args:
            grafana_host: Grafana instance URL (e.g., https://grafana.example.com)
            grafana_api_key: API key for authentication
            ssl_verify: Whether to verify SSL certificates ("true" or "false")
        """
        self.__host = grafana_host.rstrip('/')  # Remove trailing slash
        self.__api_key = grafana_api_key
        self.__ssl_verify = False if ssl_verify and ssl_verify.lower() == 'false' else True
        self.headers = {
            'Authorization': f'Bearer {self.__api_key}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"Initialized Grafana processor with host: {self.__host}")

    def get_connection(self):
        """Return connection details for debugging"""
        return {
            "host": self.__host,
            "ssl_verify": self.__ssl_verify,
            "auth_method": "api_key",
            "headers": {k: v for k, v in self.headers.items() if k != "Authorization"}
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
            url = '{}/api/datasources'.format(self.__host)
            logger.info(f"Testing Grafana connection to: {url}")
            
            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)
            if response and response.status_code == 200:
                logger.info("Successfully connected to Grafana API")
                return True
            else:
                status_code = response.status_code if response else None
                raise Exception(
                    f"Failed to connect with Grafana. Status Code: {status_code}. Response Text: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred while fetching grafana data sources with error: {e}")
            raise e

    def grafana_promql_query(self, datasource_uid: str, query: str) -> Dict[str, Any]:
        """
        Executes PromQL queries against Grafana's Prometheus datasource.
        
        Args:
            datasource_uid: Prometheus datasource UID
            query: PromQL query string
            
        Returns:
            Dict containing query results with optimized time series data
        """
        try:
            # Calculate time range (last 1 hour by default)
            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(hours=1)
            
            payload = {
                "queries": [{
                    "refId": "A",
                    "expr": query,
                    "datasource": {
                        "type": "prometheus",
                        "uid": datasource_uid
                    },
                    "intervalMs": 30000,
                    "maxDataPoints": 1000
                }],
                "from": start_time.isoformat(),
                "to": end_time.isoformat()
            }
            
            url = f"{self.__host}/api/ds/query"
            logger.info(f"Executing PromQL query: {query}")
            
            response = requests.post(url, headers=self.headers, json=payload, verify=self.__ssl_verify, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # Optimize time series data to reduce token size
                optimized_data = self._optimize_time_series_data(data)
                return {
                    "status": "success",
                    "query": query,
                    "results": optimized_data
                }
            else:
                raise Exception(f"PromQL query failed. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error executing PromQL query: {str(e)}")
            raise e

    def grafana_loki_query(self, query: str, duration: str, limit: int = 100) -> Dict[str, Any]:
        """
        Queries Grafana Loki for log data.
        
        Args:
            query: Loki query string
            duration: Time duration (e.g., '5m', '1h', '2d')
            limit: Maximum number of log entries to return
            
        Returns:
            Dict containing log data from Loki datasource
        """
        try:
            # Convert relative time to absolute timestamps
            end_time = datetime.datetime.now()
            start_time = self._parse_duration_to_start_time(duration, end_time)
            
            payload = {
                "queries": [{
                    "refId": "A",
                    "expr": query,
                    "datasource": {
                        "type": "loki"
                    },
                    "maxLines": limit
                }],
                "from": start_time.isoformat(),
                "to": end_time.isoformat()
            }
            
            url = f"{self.__host}/api/ds/query"
            logger.info(f"Executing Loki query: {query} for duration: {duration}")
            
            response = requests.post(url, headers=self.headers, json=payload, verify=self.__ssl_verify, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "query": query,
                    "duration": duration,
                    "limit": limit,
                    "results": data
                }
            else:
                raise Exception(f"Loki query failed. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error executing Loki query: {str(e)}")
            raise e

    def grafana_get_dashboard_config_details(self, dashboard_uid: str) -> Dict[str, Any]:
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
                    "meta": dashboard_data.get("meta", {})
                }
            else:
                raise Exception(f"Failed to fetch dashboard config. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching dashboard config: {str(e)}")
            raise e

    def grafana_query_dashboard_panels(self, dashboard_uid: str, 
                                     panel_ids: List[int], template_variables: Dict[str, str] = None) -> Dict[str, Any]:
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
            
            # First get dashboard configuration
            dashboard_url = f"{self.__host}/api/dashboards/uid/{dashboard_uid}"
            dashboard_response = requests.get(dashboard_url, headers=self.headers, verify=self.__ssl_verify, timeout=20)
            
            if dashboard_response.status_code != 200:
                raise Exception(f"Failed to fetch dashboard. Status: {dashboard_response.status_code}")
            
            dashboard_data = dashboard_response.json()
            dashboard = dashboard_data.get("dashboard", {})
            panels = dashboard.get("panels", [])
            
            # Filter panels by requested IDs
            target_panels = [panel for panel in panels if panel.get("id") in panel_ids]
            
            if not target_panels:
                raise Exception(f"No panels found with IDs: {panel_ids}")
            
            # Execute queries for each panel
            panel_results = []
            for panel in target_panels:
                panel_result = self._execute_panel_query(panel, template_variables or {})
                panel_results.append({
                    "panel_id": panel.get("id"),
                    "title": panel.get("title"),
                    "type": panel.get("type"),
                    "data": panel_result
                })
            
            return {
                "status": "success",
                "dashboard_uid": dashboard_uid,
                "panel_ids": panel_ids,
                "template_variables": template_variables,
                "results": panel_results
            }
                
        except Exception as e:
            logger.error(f"Error querying dashboard panels: {str(e)}")
            raise e

    def grafana_fetch_dashboard_variable_label_values(self, datasource_uid: str, label_name: str) -> Dict[str, Any]:
        """
        Fetches label values for dashboard variables from Prometheus datasource.
        
        Args:
            datasource_uid: Prometheus datasource UID
            label_name: Label name to fetch values for (e.g., "instance", "job")
            
        Returns:
            Dict containing list of available label values
        """
        try:
            # Use a simple query that returns series with the label we want
            # This approach is more reliable than trying to use label_values function
            query = f'up{{{label_name}=~".+"}}'
            
            payload = {
                "queries": [{
                    "refId": "A",
                    "expr": query,
                    "datasource": {
                        "type": "prometheus",
                        "uid": datasource_uid
                    },
                    "intervalMs": 30000,
                    "maxDataPoints": 1000
                }],
                "from": (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
                "to": datetime.datetime.now().isoformat()
            }
            
            url = f"{self.__host}/api/ds/query"
            logger.info(f"Fetching label values for: {label_name}")
            
            response = requests.post(url, headers=self.headers, json=payload, verify=self.__ssl_verify, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                label_values = self._extract_label_values_from_series(data, label_name)
                
                return {
                    "status": "success",
                    "datasource_uid": datasource_uid,
                    "label_name": label_name,
                    "values": label_values
                }
            else:
                raise Exception(f"Failed to fetch label values. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching label values: {str(e)}")
            raise e

    def grafana_fetch_dashboard_variables(self, dashboard_uid: str) -> Dict[str, Any]:
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
                    variable_details.append({
                        "name": var.get("name"),
                        "type": var.get("type"),
                        "current_value": var.get("current", {}).get("value"),
                        "options": var.get("options", []),
                        "query": var.get("query"),
                        "definition": var.get("definition")
                    })
                
                return {
                    "status": "success",
                    "dashboard_uid": dashboard_uid,
                    "variables": variable_details
                }
            else:
                raise Exception(f"Failed to fetch dashboard variables. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching dashboard variables: {str(e)}")
            raise e

    def grafana_fetch_all_dashboards(self, limit: int = 100) -> Dict[str, Any]:
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
            
            response = requests.get(url, headers=self.headers, params=params, verify=self.__ssl_verify, timeout=20)
            
            if response.status_code == 200:
                dashboards = response.json()
                # Extract relevant information
                dashboard_list = []
                for dashboard in dashboards:
                    dashboard_list.append({
                        "uid": dashboard.get("uid"),
                        "title": dashboard.get("title"),
                        "type": dashboard.get("type"),
                        "url": dashboard.get("url"),
                        "folder_title": dashboard.get("folderTitle"),
                        "folder_uid": dashboard.get("folderUid"),
                        "tags": dashboard.get("tags", []),
                        "is_starred": dashboard.get("isStarred", False)
                    })
                
                return {
                    "status": "success",
                    "total_count": len(dashboard_list),
                    "limit": limit,
                    "dashboards": dashboard_list
                }
            else:
                raise Exception(f"Failed to fetch dashboards. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching dashboards: {str(e)}")
            raise e

    def grafana_fetch_datasources(self) -> Dict[str, Any]:
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
                    datasource_list.append({
                        "id": ds.get("id"),
                        "uid": ds.get("uid"),
                        "name": ds.get("name"),
                        "type": ds.get("type"),
                        "url": ds.get("url"),
                        "access": ds.get("access"),
                        "database": ds.get("database"),
                        "is_default": ds.get("isDefault", False),
                        "json_data": ds.get("jsonData", {}),
                        "secure_json_data": {k: "***" for k in ds.get("secureJsonData", {}).keys()}
                    })
                
                return {
                    "status": "success",
                    "total_count": len(datasource_list),
                    "datasources": datasource_list
                }
            else:
                raise Exception(f"Failed to fetch datasources. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching datasources: {str(e)}")
            raise e

    def grafana_fetch_users(self, limit: int = 100) -> Dict[str, Any]:
        """
        Fetches all users from Grafana.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            Dict containing list of users
        """
        try:
            url = f"{self.__host}/api/users"
            params = {"limit": limit}
            logger.info(f"Fetching all users (limit: {limit})")
            
            response = requests.get(url, headers=self.headers, params=params, verify=self.__ssl_verify, timeout=20)
            
            if response.status_code == 200:
                users = response.json()
                # Extract relevant information
                user_list = []
                for user in users:
                    user_list.append({
                        "id": user.get("id"),
                        "login": user.get("login"),
                        "email": user.get("email"),
                        "name": user.get("name"),
                        "is_admin": user.get("isAdmin", False),
                        "is_disabled": user.get("isDisabled", False),
                        "last_seen_at": user.get("lastSeenAt"),
                        "auth_labels": user.get("authLabels", [])
                    })
                
                return {
                    "status": "success",
                    "total_count": len(user_list),
                    "limit": limit,
                    "users": user_list
                }
            else:
                raise Exception(f"Failed to fetch users. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching users: {str(e)}")
            raise e

    def grafana_fetch_teams(self, limit: int = 100) -> Dict[str, Any]:
        """
        Fetches all teams from Grafana.
        
        Args:
            limit: Maximum number of teams to return
            
        Returns:
            Dict containing list of teams
        """
        try:
            url = f"{self.__host}/api/teams/search"
            params = {"perpage": limit}
            logger.info(f"Fetching all teams (limit: {limit})")
            
            response = requests.get(url, headers=self.headers, params=params, verify=self.__ssl_verify, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                teams = data.get("teams", [])
                # Extract relevant information
                team_list = []
                for team in teams:
                    team_list.append({
                        "id": team.get("id"),
                        "name": team.get("name"),
                        "email": team.get("email"),
                        "org_id": team.get("orgId"),
                        "avatar_url": team.get("avatarUrl"),
                        "member_count": team.get("memberCount")
                    })
                
                return {
                    "status": "success",
                    "total_count": len(team_list),
                    "limit": limit,
                    "teams": team_list
                }
            else:
                raise Exception(f"Failed to fetch teams. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching teams: {str(e)}")
            raise e

    def grafana_fetch_folders(self) -> Dict[str, Any]:
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
                    folder_list.append({
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
                        "version": folder.get("version")
                    })
                
                return {
                    "status": "success",
                    "total_count": len(folder_list),
                    "folders": folder_list
                }
            else:
                raise Exception(f"Failed to fetch folders. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching folders: {str(e)}")
            raise e

    def grafana_fetch_annotations(self, dashboard_uid: str = None, limit: int = 100) -> Dict[str, Any]:
        """
        Fetches annotations from Grafana.
        
        Args:
            dashboard_uid: Optional dashboard UID to filter annotations
            limit: Maximum number of annotations to return
            
        Returns:
            Dict containing list of annotations
        """
        try:
            url = f"{self.__host}/api/annotations"
            params = {"limit": limit}
            if dashboard_uid:
                params["dashboardUID"] = dashboard_uid
            
            logger.info(f"Fetching annotations (limit: {limit})")
            
            response = requests.get(url, headers=self.headers, params=params, verify=self.__ssl_verify, timeout=20)
            
            if response.status_code == 200:
                annotations = response.json()
                # Extract relevant information
                annotation_list = []
                for annotation in annotations:
                    annotation_list.append({
                        "id": annotation.get("id"),
                        "dashboard_uid": annotation.get("dashboardUID"),
                        "panel_id": annotation.get("panelId"),
                        "user_id": annotation.get("userId"),
                        "user_name": annotation.get("userName"),
                        "text": annotation.get("text"),
                        "type": annotation.get("type"),
                        "tags": annotation.get("tags", []),
                        "time": annotation.get("time"),
                        "time_end": annotation.get("timeEnd"),
                        "is_region": annotation.get("isRegion", False)
                    })
                
                return {
                    "status": "success",
                    "total_count": len(annotation_list),
                    "limit": limit,
                    "dashboard_uid": dashboard_uid,
                    "annotations": annotation_list
                }
            else:
                raise Exception(f"Failed to fetch annotations. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching annotations: {str(e)}")
            raise e

    def _parse_duration_to_start_time(self, duration: str, end_time: datetime.datetime) -> datetime.datetime:
        """Convert duration string to start time"""
        duration = duration.lower()
        if duration.endswith('m'):
            minutes = int(duration[:-1])
            return end_time - datetime.timedelta(minutes=minutes)
        elif duration.endswith('h'):
            hours = int(duration[:-1])
            return end_time - datetime.timedelta(hours=hours)
        elif duration.endswith('d'):
            days = int(duration[:-1])
            return end_time - datetime.timedelta(days=days)
        else:
            # Default to 1 hour
            return end_time - datetime.timedelta(hours=1)

    def _optimize_time_series_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _execute_panel_query(self, panel: Dict[str, Any], template_variables: Dict[str, str]) -> Dict[str, Any]:
        """Execute query for a specific panel"""
        try:
            targets = panel.get("targets", [])
            if not targets:
                return {"error": "No targets found for panel"}
            
            # For now, execute the first target
            target = targets[0]
            query = target.get("expr", "")
            datasource = target.get("datasource", {})
            
            # Handle both string and object datasource formats
            if isinstance(datasource, str):
                datasource_uid = datasource
            else:
                datasource_uid = datasource.get("uid")
            
            if not query or not datasource_uid:
                return {"error": "Invalid target configuration"}
            
            # Apply template variables
            for var_name, var_value in template_variables.items():
                query = query.replace(f"${{{var_name}}}", var_value)
            
            # Execute the query
            return self.grafana_promql_query(datasource_uid, query)
            
        except Exception as e:
            logger.error(f"Error executing panel query: {e}")
            return {"error": str(e)}

    def _extract_label_values(self, data: Dict[str, Any], label_name: str) -> List[str]:
        """Extract label values from query response"""
        try:
            values = []
            for result in data.get("results", {}).values():
                if "frames" in result:
                    for frame in result["frames"]:
                        if "data" in frame and "values" in frame["data"]:
                            # Extract string values from the response
                            frame_values = frame["data"]["values"]
                            if frame_values and len(frame_values) > 0:
                                values.extend([str(v) for v in frame_values[0] if v])
            return list(set(values))  # Remove duplicates
        except Exception as e:
            logger.error(f"Error extracting label values: {e}")
            return []

    def _extract_label_values_from_series(self, data: Dict[str, Any], label_name: str) -> List[str]:
        """Extract label values from series data"""
        try:
            values = set()
            for result in data.get("results", {}).values():
                if "frames" in result:
                    for frame in result["frames"]:
                        if "schema" in frame and "fields" in frame["schema"]:
                            # Look for the label in the field names
                            for field in frame["schema"]["fields"]:
                                if "labels" in field and label_name in field["labels"]:
                                    values.add(field["labels"][label_name])
                        # Also check in the data if available
                        if "data" in frame and "values" in frame["data"]:
                            # This might contain label information in a different format
                            pass
            return list(values)
        except Exception as e:
            logger.error(f"Error extracting label values from series: {e}")
            return []