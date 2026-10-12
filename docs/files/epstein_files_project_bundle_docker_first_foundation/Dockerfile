FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ocrmypdf tesseract-ocr ghostscript qpdf poppler-utils \
    ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
WORKDIR /app
COPY pyproject.toml uv.lock* /app/
RUN if [ -f uv.lock ]; then uv sync --frozen; else uv sync; fi
COPY . /app
ENTRYPOINT ["uv","run","python"]
CMD ["epstein_files_pipeline.py","--help"]
