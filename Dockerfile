FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yaml .
COPY strategy/ ./strategy/

ENV PYTHONPATH=/app

CMD ["python", "-m", "strategy.run_strategy", "--mode", "backtest"]
