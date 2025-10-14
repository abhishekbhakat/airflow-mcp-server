"""
## Bash REPL DAG

This DAG allows execution of arbitrary shell commands via parameters.
It's designed for development and testing purposes in a trusted environment.

**Parameters:**
- `bash_command` (str): The shell command to execute
- `timeout` (int): Maximum execution time in seconds (default: 300)
- `working_directory` (str): Directory to execute command in (default: /tmp)

**Features:**
- Manual trigger only (schedule=None)
- No retries
- Captures stdout/stderr to Airflow logs
- Execution errors will fail the task with full output
"""

from airflow.sdk import dag
from airflow.operators.bash import BashOperator
from airflow.models.param import Param
from pendulum import datetime
from datetime import timedelta


@dag(
    dag_id="bash_REPL_dag",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "Airflow",
        "retries": 0,
    },
    params={
        "bash_command": Param(
            default="echo 'Hello from Bash REPL!' && date && pwd",
            type="string",
            description="Shell command to execute. Multiple commands can be chained with && or ;",
        ),
        "timeout": Param(
            default=300,
            type="integer",
            description="Maximum execution time in seconds",
            minimum=1,
            maximum=3600,
        ),
        "working_directory": Param(
            default="/tmp",
            type="string",
            description="Working directory for command execution",
        ),
    },
    tags=["repl", "development", "bash", "shell"],
    doc_md=__doc__,
)
def bash_REPL_dag():
    """Bash REPL DAG for executing arbitrary shell commands"""

    BashOperator(
        task_id="execute_bash_command",
        bash_command="{{ params.bash_command }}",
        cwd="{{ params.working_directory }}",
        execution_timeout=timedelta(seconds=3600),
        append_env=True,
    )


bash_REPL_dag()
