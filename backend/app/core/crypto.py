import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Chave secreta de encriptação (com fallback derivado de segredo interno para ambiente dev)
RAW_SECRET = os.getenv("ENCRYPTION_KEY", os.getenv("INTERNAL_API_KEY", "amanda-enterprise-secret-key-32b"))

# Derivação de chave segura de 32 bytes para Fernet (AES-128-CBC com autenticação HMAC / Padrão Seguro)
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"ia_amanda_alergia_salt_static",
    iterations=100000,
)
_fernet_key = base64.urlsafe_b64encode(kdf.derive(RAW_SECRET.encode()))
_cipher = Fernet(_fernet_key)

def encrypt_text(plain_text: str) -> str:
    """Encripta uma string em texto plano para formato seguro codificado em base64."""
    if not plain_text:
        return plain_text
    try:
        encrypted_bytes = _cipher.encrypt(plain_text.encode("utf-8"))
        return f"enc::{encrypted_bytes.decode('utf-8')}"
    except Exception as e:
        logger.error(f"Erro ao encriptar texto: {e}")
        return plain_text

def decrypt_text(cipher_text: str) -> str:
    """Decripta uma string encriptada. Se não estiver encriptada, retorna o texto original."""
    if not cipher_text or not isinstance(cipher_text, str):
        return cipher_text
    if not cipher_text.startswith("enc::"):
        return cipher_text
    try:
        raw_payload = cipher_text.replace("enc::", "")
        decrypted_bytes = _cipher.decrypt(raw_payload.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"Erro ao decriptar texto: {e}")
        return cipher_text
