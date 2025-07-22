FROM python:3.11-slim

WORKDIR /app

COPY gateway/requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r /app/requirements.txt && pip install --upgrade SQLAlchemy

# copy source
COPY proto /app/proto
COPY gateway /app/gateway

ENV PYTHONPATH="/app"

# generate gRPC stubs at build time
RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app/gateway --grpc_python_out=/app/gateway /app/proto/payment.proto

# fix imports in generated gRPC code
RUN sed -i 's/^import payment_pb2 as payment__pb2/from . import payment_pb2 as payment__pb2/' /app/gateway/payment_pb2_grpc.py

CMD ["python", "-m", "gateway.app"]
