import os
from dotenv import load_dotenv

load_dotenv()

def get_backend_socketio_endpoint() -> str:
    return os.getenv("BACKEND_SOCKETIO_ENDPOINT")

def get_jwt_signing_key() -> str:
    return os.getenv("JWT_SIGNING_KEY")