"""
## Python REPL DAG

This DAG allows execution of arbitrary Python code via parameters.
It's designed for development and testing purposes in a trusted environment.

**Parameters:**
- `python_code` (str): The Python code to execute
- `timeout` (int): Maximum execution time in seconds (default: 300)

**Features:**
- Manual trigger only (schedule=None)
- No retries
- Captures stdout/stderr to Airflow logs
- Execution errors will fail the task with full traceback
"""

import io
import signal
from contextlib import redirect_stderr, redirect_stdout

from airflow.models.param import Param
from airflow.sdk import dag, task
from pendulum import datetime


class TimeoutError(Exception):
    """Raised when code execution times out"""
    pass


def timeout_handler(signum, frame):
    """Handler for timeout signal"""
    raise TimeoutError("Code execution exceeded timeout limit")


@dag(
    dag_id="python_REPL_dag",
    start_date=datetime(2025, 1, 1),
    schedule=None,  # Manual trigger only
    catchup=False,
    default_args={
        "owner": "Airflow",
        "retries": 0,
    },
    params={
        "python_code": Param(
            default="print('Hello from Python REPL!')\nprint(f'2 + 2 = {2 + 2}')",
            type="string",
            description="Python code to execute. Use print() to output to logs.",
        ),
        "timeout": Param(
            default=300,
            type="integer",
            description="Maximum execution time in seconds",
            minimum=1,
            maximum=3600,
        ),
    },
    tags=["repl", "development", "python"],
    doc_md=__doc__,
)
def python_REPL_dag():
    """Python REPL DAG for executing arbitrary Python code"""

    @task(task_id="execute_python_code")
    def execute_code(**context):
        """
        Execute the provided Python code with stdout/stderr capture.

        The code runs in an isolated namespace with timeout protection.
        All output is logged to Airflow task logs.
        """
        # Get parameters
        python_code = context["params"]["python_code"]
        timeout_seconds = context["params"]["timeout"]

        print(f"{'=' * 60}")
        print(f"Executing Python code with {timeout_seconds}s timeout")
        print(f"{'=' * 60}\n")

        # Prepare output capture
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Set up timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            # Execute code with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Create isolated namespace for execution
                exec_namespace = {
                    "__builtins__": __builtins__,
                    "__name__": "__main__",
                }

                # Execute the code
                exec(python_code, exec_namespace)

            # Cancel timeout
            signal.alarm(0)

            # Get captured output
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            # Log results
            print(f"\n{'=' * 60}")
            print("EXECUTION COMPLETED SUCCESSFULLY")
            print(f"{'=' * 60}\n")

            if stdout_output:
                print("📤 STDOUT:")
                print(stdout_output)
            else:
                print("📤 STDOUT: (empty)")

            if stderr_output:
                print("\n⚠️  STDERR:")
                print(stderr_output)

            print(f"\n{'=' * 60}")
            print(f"✅ Execution finished in less than {timeout_seconds}s")
            print(f"{'=' * 60}")

        except TimeoutError as e:
            signal.alarm(0)  # Cancel alarm
            print(f"\n{'=' * 60}")
            print(f"❌ TIMEOUT ERROR: {str(e)}")
            print(f"{'=' * 60}")
            raise

        except Exception:
            signal.alarm(0)  # Cancel alarm

            # Get any output that was captured before the error
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            print(f"\n{'=' * 60}")
            print("❌ EXECUTION FAILED")
            print(f"{'=' * 60}\n")

            if stdout_output:
                print("📤 STDOUT (before error):")
                print(stdout_output)

            if stderr_output:
                print("\n⚠️  STDERR (before error):")
                print(stderr_output)

            print(f"\n{'=' * 60}")
            print("💥 EXCEPTION DETAILS:")
            print(f"{'=' * 60}")
            # Re-raise to show full traceback in Airflow logs
            raise

        finally:
            stdout_capture.close()
            stderr_capture.close()

    # Define the task execution
    execute_code()


# Instantiate the DAG
python_REPL_dag()
