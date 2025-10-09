## NOTE

FastMCP’s OpenAPI tooling requires an `httpx.AsyncClient` implementation. Even if the underlying transport is swapped to `aiohttp`, the adapter must still return `httpx` request/response objects so FastMCP continues to function. Consequently, `httpx` remains a required dependency.

- Airflow 3.0’s OpenAPI spec references `DagTagResponse` from `DAGCollectionResponse.$defs` without including the definition there. FastMCP treats that as an error (`PointerToNowhere`).

