import os
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

POLICY_PATH = "core/policies.yaml"
SIG_PATH = "core/policies.sig"
PUBLIC_KEY_PATH = "core/public.pem"

class SecurityTamperingException(Exception):
    pass

def verify_policy_integrity() -> str:
    """Проверяет RSA-подпись политик. Возвращает SHA256 хэш для аудита."""
    if not all(os.path.exists(p) for p in [POLICY_PATH, SIG_PATH, PUBLIC_KEY_PATH]):
        raise SecurityTamperingException("CRITICAL: Отсутствуют файлы политик, ключа или подписи.")

    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())

    with open(POLICY_PATH, "rb") as f:
        payload = f.read()
        
    with open(SIG_PATH, "rb") as f:
        signature = f.read()

    try:
        public_key.verify(
            signature,
            payload,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        # Подпись верна. Отдаем хэш.
        return hashlib.sha256(payload).hexdigest()
    except InvalidSignature:
        raise SecurityTamperingException("POLICY TAMPERING DETECTED! Подпись YAML файла недействительна.")
