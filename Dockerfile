FROM python:3.11-slim

WORKDIR /app

COPY orchestrator/ ./orchestrator/
RUN pip install --no-cache-dir ./orchestrator

RUN mkdir -p /app/data
VOLUME /app/data

ENV METRICS_PATH=/app/data/runs.jsonl
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uvicorn", "remediation.main:app", "--host", "0.0.0.0", "--port", "8080"]
