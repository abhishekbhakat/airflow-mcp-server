# airflow-mcp-server: An MCP Server for controlling Airflow


## Overview
A [Model Context Protocol](https://modelcontextprotocol.io/) server for controlling Airflow via Airflow APIs.


### Considerations

The MCP Server expects environment variables to be set:
- `AIRFLOW_BASE_URL`: The base URL of the Airflow API
- `AUTH_TOKEN`: The token to use for authorization (_This should be base64 encoded username:password_)

*Currently, only Basic Auth is supported.*

**Page Limit**

The default is 100 items, but you can change it using `maximum_page_limit` option in [api] section in the `airflow.cfg` file.

## Tasks

- [x] First API
- [x] Parse OpenAPI Spec
- [ ] Parse proper description with listing tools.
- [ ] Airflow config fetch (_specifically for page limit_)
- [ ] Env variables optional (_env variables might not be ideal for airflow plugins_)
