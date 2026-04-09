FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
COPY src/ src/
RUN uv pip install --system .

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/mcp-server-zefix /usr/local/bin/
COPY src/ src/
RUN useradd -r -s /bin/false appuser
USER appuser
EXPOSE 8000
CMD ["python", "-m", "mcp_server_zefix", "--transport", "streamable-http"]
