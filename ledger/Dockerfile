FROM python:3.11-slim

WORKDIR /app

COPY ledger/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY proto /app/proto
COPY ledger /app/ledger

ENV PYTHONPATH="/app"

# generate stubs
RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app --grpc_python_out=/app /app/proto/payment.proto

CMD ["python", "-m", "ledger.server"]
