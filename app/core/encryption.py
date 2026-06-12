from cryptography.fernet import Fernet
from app.core.config import settings

# Ensure the encryption key is valid for Fernet (must be 32 URL-safe base64-encoded bytes)
# You can generate one by running: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
try:
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError(f"CRITICAL: ENCRYPTION_KEY in .env is invalid. It must be a valid Fernet key. {str(e)}")


def encrypt_api_secret(secret: str) -> str:
    if not secret:
        return secret
    return fernet.encrypt(secret.encode()).decode()


def decrypt_api_secret(encrypted_secret: str) -> str:
    if not encrypted_secret:
        return encrypted_secret
    return fernet.decrypt(encrypted_secret.encode()).decode()
