from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings


def get_cipher() -> Fernet:
    settings = get_settings()
    key = settings.app_secret_key.encode("utf-8")
    return Fernet(key)


def encrypt_secret(plain_text: str | None) -> str | None:
    if not plain_text:
        return None
    cipher = get_cipher()
    return cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher_text: str | None) -> str | None:
    if not cipher_text:
        return None
    cipher = get_cipher()
    try:
        return cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
