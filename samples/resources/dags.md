# Available DAGs

## bash_REPL_dag
**Purpose**: Execute arbitrary shell commands in a controlled environment.

**Parameters**:
- `bash_command` (string): Shell command to execute
- `timeout` (integer): Maximum execution time in seconds (1-3600)
- `working_directory` (string): Directory to execute in (default: /tmp)

**Usage**:
```json
{
  "method": "dag/trigger",
  "params": {
    "dag_id": "bash_REPL_dag",
    "conf": {
      "bash_command": "ls -la",
      "timeout": 60
    }
  }
}
```

## python_REPL_dag
**Purpose**: Execute arbitrary Python code in an isolated namespace.

**Parameters**:
- `python_code` (string): Python code to execute
- `timeout` (integer): Maximum execution time in seconds (1-3600)

**Usage**:
```json
{
  "method": "dag/trigger",
  "params": {
    "dag_id": "python_REPL_dag",
    "conf": {
      "python_code": "print('Hello World')",
      "timeout": 120
    }
  }
}
```

## web_search_dag
**Purpose**: Perform web searches using PydanticAI's WebSearchTool.

**Parameters**:
- `search_query` (string): Web search query

**Usage**:
```json
{
  "method": "dag/trigger",
  "params": {
    "dag_id": "web_search_dag",
    "conf": {
      "search_query": "Latest Apache Airflow release"
    }
  }
}
```