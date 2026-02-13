FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv \
  && uv pip compile pyproject.toml -o requirements.txt \
  && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8780

CMD ["python", "mcp_servers/epstein_files_processor/server.py", "--host", "0.0.0.0", "--port", "8780"]
