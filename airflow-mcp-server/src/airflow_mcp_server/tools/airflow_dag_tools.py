import os

import aiohttp


class AirflowDagTools:
    def __init__(self):
        self.airflow_base_url = os.getenv("AIRFLOW_BASE_URL")
        self.auth_token = os.getenv("AUTH_TOKEN")
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.auth_token}"}

    async def list_dags(
        self,
        limit: int | None = 100,
        offset: int | None = None,
        order_by: str | None = None,
        tags: list[str] | None = None,
        only_active: bool = True,
        paused: bool | None = None,
        fields: list[str] | None = None,
        dag_id_pattern: str | None = None,
    ) -> list[str]:
        """
        List all DAGs in Airflow.

        Sample response:
        {
        "dags": [
            {
            "dag_id": "string",
            "dag_display_name": "string",
            "root_dag_id": "string",
            "is_paused": true,
            "is_active": true,
            "is_subdag": true,
            "last_parsed_time": "2019-08-24T14:15:22Z",
            "last_pickled": "2019-08-24T14:15:22Z",
            "last_expired": "2019-08-24T14:15:22Z",
            "scheduler_lock": true,
            "pickle_id": "string",
            "default_view": "string",
            "fileloc": "string",
            "file_token": "string",
            "owners": [
                "string"
            ],
            "description": "string",
            "schedule_interval": {
                "__type": "string",
                "days": 0,
                "seconds": 0,
                "microseconds": 0
            },
            "timetable_description": "string",
            "tags": [
                {
                "name": "string"
                }
            ],
            "max_active_tasks": 0,
            "max_active_runs": 0,
            "has_task_concurrency_limits": true,
            "has_import_errors": true,
            "next_dagrun": "2019-08-24T14:15:22Z",
            "next_dagrun_data_interval_start": "2019-08-24T14:15:22Z",
            "next_dagrun_data_interval_end": "2019-08-24T14:15:22Z",
            "next_dagrun_create_after": "2019-08-24T14:15:22Z",
            "max_consecutive_failed_dag_runs": 0
            }
        ],
        "total_entries": 0
        }

        Args:
            limit (int, optional): The numbers of items to return.
            offset (int, optional): The number of items to skip before starting to collect the result set.
            order_by (str, optional): The name of the field to order the results by. Prefix a field name with - to reverse the sort order. New in version 2.1.0
            tags (list[str], optional): List of tags to filter results. New in version 2.2.0
            only_active (bool, optional): Only filter active DAGs. New in version 2.1.1
            paused (bool, optional): Only filter paused/unpaused DAGs. If absent or null, it returns paused and unpaused DAGs. New in version 2.6.0
            fields (list[str], optional): List of field for return.
            dag_id_pattern (str, optional): If set, only return DAGs with dag_ids matching this pattern.

        Returns:
            list[str]: A list of DAG names.
        """
        dags = []
        async with aiohttp.ClientSession() as session:
            params = {
                "limit": limit,
                "offset": offset,
                "order_by": order_by,
                "tags": tags,
                "only_active": only_active,
                "paused": paused,
                "fields": fields,
                "dag_id_pattern": dag_id_pattern,
            }
            async with session.get(f"{self.airflow_base_url}/api/v1/dags", headers=self.headers, params=params) as response:
                if response.status == 200:
                    dags = await response.json()

        return dags
