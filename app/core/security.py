from typing import Any, Dict
from jose import jwt
from app.core.config import settings


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception as e:
        raise ValueError("Invalid or expired token") from e
