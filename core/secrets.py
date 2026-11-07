"""Encrypt small per-app secrets (GitHub access tokens, .env contents) at rest.

The projects table stores these as Fernet ciphertext in *_enc columns, so a
database dump never exposes a client's DB password or a repo access token in
the clear. The key is derived from the platform's own FLASK_SECRET_KEY (or an
explicit APP_SECRETS_KEY when one is set) - no new secret to manage, and the
same key every worker already trusts. decrypt_secret() never raises, so a row
encrypted under an old key (or a hand-edited value) degrades to "no secret"
rather than crashing a deploy.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

try:
    from flask import current_app
except Exception:  # pragma: no cover - Flask is always present in practice
    current_app = None


def _key():
    explicit = os.environ.get("APP_SECRETS_KEY")
    if explicit:
        return explicit.encode() if isinstance(explicit, str) else explicit

    secret = ""
    if current_app:
        try:
            secret = current_app.config.get("SECRET_KEY") or ""
        except Exception:
            secret = ""
    secret = secret or os.environ.get("FLASK_SECRET_KEY", "")

    digest = hashlib.sha256(("origin-solutions-secrets:" + secret).encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext):
    """Ciphertext (str) for a non-empty secret, else None."""
    if not plaintext:
        return None
    return Fernet(_key()).encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext):
    """Plaintext for valid ciphertext, else None. Never raises."""
    if not ciphertext:
        return None
    try:
        return Fernet(_key()).decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return None
