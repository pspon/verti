# Verti Garden Planner — FastAPI + HTMX web UI
FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; wheels cover pandas/numpy/plotly on slim.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

# DB lives on a mounted volume so writes survive restarts/redeploys.
ENV VERTI_DB_PATH=/data/verti.db
EXPOSE 8080

ENTRYPOINT ["./docker-entrypoint.sh"]
