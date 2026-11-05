FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# The DuckDB file lives on a dedicated volume so it survives container
# re-creation (see docker-compose.yml); everything else stays read-only code.
RUN pip install --no-cache-dir -e . \
    && useradd --system --uid 10001 --home-dir /app app \
    && mkdir -p /app/db \
    && chown -R app:app /app

ENV RETAIL_OPS_DATABASE=/app/db/retail_ops.duckdb
VOLUME ["/app/db"]

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4).status == 200 else 1)"

CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
