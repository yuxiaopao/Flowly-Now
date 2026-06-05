"""
Encryption utilities for secure credential storage.
Uses Fernet symmetric encryption from the cryptography library.
"""

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from django.conf import settings


def get_encryption_key() -> bytes:
    """
    Get or generate the encryption key for credential encryption.
    Uses Django's SECRET_KEY as the base for key derivation.
    """
    secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key-change-me')
    salt = b'flowly-credential-salt-v1'

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return key


def get_fernet() -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    key = get_encryption_key()
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext string.
    
    Args:
        plaintext: The string to encrypt
        
    Returns:
        Base64-encoded encrypted string
    """
    if not plaintext:
        return ''
    
    fernet = get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt an encrypted string.
    
    Args:
        ciphertext: Base64-encoded encrypted string
        
    Returns:
        Decrypted plaintext string
    """
    if not ciphertext:
        return ''
    
    try:
        fernet = get_fernet()
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except Exception:
        return ''


def hash_value(value: str) -> str:
    """
    Create a SHA-256 hash of a value for integrity checking.
    
    Args:
        value: The string to hash
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    if not value:
        return ''
    
    return hashlib.sha256(value.encode()).hexdigest()


def generate_masked_value(value: str, visible_chars: int = 4) -> str:
    """
    Generate a masked version of a sensitive value for display.
    
    Args:
        value: The sensitive value
        visible_chars: Number of characters to show at start and end
        
    Returns:
        Masked string like "sk-ab...xy"
    """
    if not value:
        return '***'
    
    if len(value) <= visible_chars * 2:
        return '*' * len(value)
    
    return f"{value[:visible_chars]}...{value[-visible_chars:]}"
