"""API key encryption and decryption using Fernet (symmetric encryption)"""
from cryptography.fernet import Fernet
import base64

from app.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet cipher instance from encryption key"""
    # Ensure the key is properly formatted (32 bytes base64-encoded)
    key = settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for secure storage.

    Args:
        api_key: The plain API key (e.g., "sk-proj-...")

    Returns:
        Encrypted string safe for database storage
    """
    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(api_key.encode())
    return encrypted_bytes.decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key from database.

    Args:
        encrypted_key: The encrypted key from database

    Returns:
        The original plain API key

    Raises:
        cryptography.fernet.InvalidToken: If decryption fails
    """
    fernet = _get_fernet()
    decrypted_bytes = fernet.decrypt(encrypted_key.encode())
    return decrypted_bytes.decode()


def generate_encryption_key() -> str:
    """
    Generate a new encryption key for ENCRYPTION_KEY in .env

    Usage:
        Run this once to generate a key:
        >>> python -c "from app.services.encryption import generate_encryption_key; print(generate_encryption_key())"

    Returns:
        A new Fernet key (base64-encoded 32 bytes)
    """
    return Fernet.generate_key().decode()
