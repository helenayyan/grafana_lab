FROM python:3.10-slim

WORKDIR /app
COPY order.py ./

RUN pip install --no-cache-dir prometheus_client

EXPOSE 9101
CMD ["python", "order.py"]
