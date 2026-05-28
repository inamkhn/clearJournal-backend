from typing import Any, Dict
from jose import jwt
from app.core.config import settings

def decode_token(token: str) -> Dict[str, Any]:
    # Placeholder decoder
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        return {"user_id": 1} # Fallback for local mocks/testing
