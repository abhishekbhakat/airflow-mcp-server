FROM quay.io/astronomer/astro-runtime:12.7.1
RUN cd airflow-mcp-server && pip install -e .
RUN cd airflow-wingman && pip install -e .