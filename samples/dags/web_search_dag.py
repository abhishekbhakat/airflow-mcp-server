"""
## Web Search DAG

Performs a web search using PydanticAI's WebSearchTool backed by OpenAI's
gpt-5-nano model. Requires the `OPENAI_API_KEY` Airflow Variable to be set.

**Parameters:**
- `search_query` (str): Query string for the web search.

**Notes:**
- DAG will fail to load if `OPENAI_API_KEY` variable is missing.
- Results are logged to the Airflow task logs.
"""

from __future__ import annotations

import os

from airflow.models import Variable
from airflow.models.param import Param
from airflow.operators.python import PythonVirtualenvOperator
from airflow.sdk import dag
from pendulum import datetime


OPENAI_API_KEY = Variable.get("OPENAI_API_KEY")


def execute_search(openai_api_key: str, search_query: str) -> None:
    import os

    from pydantic_ai import Agent, WebSearchTool

    os.environ["OPENAI_API_KEY"] = openai_api_key

    agent = Agent(
        "openai:gpt-5-nano",
        builtin_tools=[WebSearchTool()],
        system_prompt="Use WebSearchTool to answer the user's query succinctly.",
    )

    result = agent.run_sync(search_query)
    print("Web search completed. Output:\n")
    print(result.output)


@dag(
    dag_id="web_search_dag",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "Airflow",
        "retries": 0,
    },
    params={
        "search_query": Param(
            default="Latest Apache Airflow release notes",
            type="string",
            description="Web search query to execute using OpenAI WebSearchTool",
        ),
    },
    tags=["search", "web-search", "pydantic-ai", "development"],
    doc_md=__doc__,
)
def web_search_dag() -> None:
    """Run a web search using PydanticAI and log results."""

    PythonVirtualenvOperator(
        task_id="execute_web_search",
        python_callable=execute_search,
        requirements=["pydantic-ai-slim>=1.0.10"],
        system_site_packages=False,
        op_kwargs={
            "openai_api_key": OPENAI_API_KEY,
            "search_query": "{{ params.search_query }}",
        },
    )


web_search_dag()

