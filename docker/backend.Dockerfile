# Backend: FastAPI + LangGraph. Repo root is build context.
# pyproject.toml uses PEP 621 + hatchling (not Poetry).
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY run.py .
COPY data ./data

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
