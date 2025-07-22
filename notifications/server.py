import asyncio
import os
import grpc
from loguru import logger

import payment_pb2
import payment_pb2_grpc

NOTIFY_GRPC_PORT = int(os.getenv("NOTIFY_GRPC_PORT", "50052"))

class NotificationService(payment_pb2_grpc.NotificationServiceServicer):
    async def Notify(self, request, context):  # type: ignore[override]
        try:
            log_message = (
                f"NOTIFY acct={request.account_id} dir={request.direction} amt={request.amount} "
                f"cur={request.currency} tx={request.tx_id} msg={request.message}"
            )
            logger.info(log_message)
            with open("/app/notifications.log", "a") as f:
                f.write(log_message + "\n")
            # extend: send email/SMS/webhook
            return payment_pb2.NotificationResponse(ok=True)
        except Exception as e:
            logger.error(f"Error in Notify method: {e}")
            raise

async def serve():
    server = grpc.aio.server()
    payment_pb2_grpc.add_NotificationServiceServicer_to_server(NotificationService(), server)
    listen_addr = f"[::]:{NOTIFY_GRPC_PORT}"
    server.add_insecure_port(listen_addr)
    logger.info(f"Notification gRPC listening on {listen_addr}")
    try:
        await server.start()
        await server.wait_for_termination()
    except Exception as e:
        logger.error(f"Error starting or running gRPC server: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(serve())
