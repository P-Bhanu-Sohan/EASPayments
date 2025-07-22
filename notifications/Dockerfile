FROM python:3.11-slim
WORKDIR /app

COPY notifications/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY proto /app/proto
COPY notifications /app/notifications

ENV PYTHONPATH="/app"

RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app --grpc_python_out=/app /app/proto/payment.proto

CMD ["python", "-m", "notifications.server"]
