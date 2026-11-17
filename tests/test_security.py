from app.core.security import decrypt_secret, encrypt_secret


def test_encryption_roundtrip():
    secret = "sample_oauth_refresh_token_12345"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert encrypted is not None

    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret


def test_encryption_none():
    assert encrypt_secret(None) is None
    assert decrypt_secret(None) is None
