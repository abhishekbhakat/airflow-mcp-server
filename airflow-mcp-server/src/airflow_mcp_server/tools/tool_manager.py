"""Tools manager for maintaining singleton instances of tools."""

from airflow_mcp_server.tools.airflow_dag_tools import AirflowDagTools

_dag_tools: AirflowDagTools | None = None


def get_airflow_dag_tools() -> AirflowDagTools:
    global _dag_tools
    if not _dag_tools:
        _dag_tools = AirflowDagTools()
    return _dag_tools
