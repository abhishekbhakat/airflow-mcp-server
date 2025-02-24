from importlib.metadata import version

from airflow_wingman.plugin import WingmanPlugin

__version__ = version("airflow-wingman")
__all__ = ["WingmanPlugin"]
